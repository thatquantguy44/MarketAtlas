"""Repeatable release validation and prepared-query performance checks."""

from __future__ import annotations

import math
import os
import platform
from statistics import median
from time import perf_counter
from typing import Any

from market_atlas.analytics.fixture_correlations import validate_rolling_correlation_fixture
from market_atlas.config import SourceDatabaseConfig, TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable, inspect_source
from market_atlas.fixtures import build_fixture
from market_atlas.graph.fixture_loader import (
    validate_curated_context_fixture,
    validate_fixture_graph,
    validate_observation_fixture,
    validate_temporal_fixture,
)
from market_atlas.migrations import validate_role_boundaries
from market_atlas.publishing.fixture_build import (
    build_fixture_snapshot,
    validate_fixture_build,
    validate_fixture_reporting,
)
from market_atlas.report_api import REPORT_READER_ROLE, load_macro_economic_graph
from market_atlas.source_catalog import build_source_catalog
from market_atlas.source_contracts import verify_source_contracts

MINIMUM_QUERY_SAMPLES = 20
BUILD_TARGET_SECONDS = 300.0
QUERY_P95_TARGET_SECONDS = 2.0


def summarize_timing(samples: list[float], target_seconds: float) -> dict[str, Any]:
    """Return a conservative nearest-rank percentile for a declared sample set."""
    if len(samples) < MINIMUM_QUERY_SAMPLES:
        raise ValueError(
            f"performance validation requires at least {MINIMUM_QUERY_SAMPLES} samples"
        )
    if target_seconds <= 0:
        raise ValueError("performance target must be positive")
    if any(sample < 0 for sample in samples):
        raise ValueError("performance samples cannot be negative")
    ordered = sorted(samples)
    p95_index = math.ceil(0.95 * len(ordered)) - 1
    p95 = ordered[p95_index]
    return {
        "sample_count": len(samples),
        "min_seconds": round(ordered[0], 6),
        "median_seconds": round(float(median(ordered)), 6),
        "p95_seconds": round(p95, 6),
        "max_seconds": round(ordered[-1], 6),
        "target_seconds": target_seconds,
        "target_met": p95 <= target_seconds,
    }


def _environment_summary() -> dict[str, Any]:
    """Declare portable runtime characteristics without recording a hostname."""
    return {
        "operating_system": platform.system(),
        "operating_system_release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "cache_policy": (
            "warm local PostgreSQL connection; one unmeasured prepared-statement warm-up "
            "per query case; operating-system and database caches are not cleared"
        ),
    }


def benchmark_prepared_report_queries(
    config: TargetDatabaseConfig, samples: int = MINIMUM_QUERY_SAMPLES
) -> dict[str, Any]:
    """Measure the two bounded report query shapes under the report-reader role."""
    if samples < MINIMUM_QUERY_SAMPLES:
        raise ValueError(f"samples must be at least {MINIMUM_QUERY_SAMPLES}")
    try:
        import psycopg
    except ImportError as error:
        raise DatabaseUnavailable("PostgreSQL support is not installed") from error

    kwargs = config.connection_kwargs() | {
        "application_name": "marketatlas-release-validation",
        "options": "-c default_transaction_read_only=on -c statement_timeout=5000",
    }
    catalog_query = """
        SELECT
            count(*) FILTER (WHERE node_type = 'macro_series')::int AS series_count,
            count(*) FILTER (WHERE node_type = 'economic_concept')::int AS concept_count
        FROM atlas_report.current_macro_economic_graph_node
    """
    category_query = """
        SELECT edge.target_node_id::text
        FROM atlas_report.current_macro_economic_graph_edge AS edge
        JOIN atlas_report.current_macro_economic_graph_node AS series
          ON series.node_id = edge.source_node_id
        WHERE series.node_type = 'macro_series'
        GROUP BY edge.target_node_id
        ORDER BY count(*) DESC, edge.target_node_id
        LIMIT 1
    """
    neighborhood_query = """
        SELECT series.node_id::text, series.display_label
        FROM atlas_report.current_macro_economic_graph_edge AS edge
        JOIN atlas_report.current_macro_economic_graph_node AS series
          ON series.node_id = edge.source_node_id
        WHERE edge.target_node_id::text = %s
          AND series.node_type = 'macro_series'
        ORDER BY series.display_label
        LIMIT %s
    """
    try:
        with psycopg.connect(**kwargs) as connection, connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {REPORT_READER_ROLE}")
            cursor.execute(category_query, prepare=True)
            row = cursor.fetchone()
            if row is None:
                raise ValueError(
                    "no published macro economic category is available for benchmarking"
                )
            category_id = row[0]
            cases = {
                "catalog_summary": (catalog_query, None),
                "largest_category_neighborhood": (neighborhood_query, (category_id, 50)),
            }
            results: dict[str, Any] = {}
            for name, (query, params) in cases.items():
                cursor.execute(query, params, prepare=True)
                cursor.fetchall()
                durations: list[float] = []
                for _ in range(samples):
                    started = perf_counter()
                    cursor.execute(query, params, prepare=True)
                    cursor.fetchall()
                    durations.append(perf_counter() - started)
                results[name] = summarize_timing(durations, QUERY_P95_TARGET_SECONDS)
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001 - driver diagnostics are normalized below
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"prepared report-query benchmark failed: {message}") from error
    return {
        "status": (
            "valid" if all(result["target_met"] for result in results.values()) else "invalid"
        ),
        "samples_per_case": samples,
        "environment": _environment_summary(),
        "cases": results,
    }


def run_release_validation(
    source_config: SourceDatabaseConfig,
    target_config: TargetDatabaseConfig,
    samples: int = MINIMUM_QUERY_SAMPLES,
) -> dict[str, Any]:
    """Execute the documented local release gate without writing upstream data."""
    fixture = build_fixture()
    checks: dict[str, Any] = {}
    checks["role_boundaries"] = validate_role_boundaries(target_config)
    checks["source_contracts"] = verify_source_contracts(
        build_source_catalog(inspect_source(source_config))
    )
    checks["fixture_graph_integrity"] = validate_fixture_graph(target_config, fixture)
    checks["fixture_temporal_integrity"] = validate_temporal_fixture(target_config, fixture)
    checks["fixture_observation_integrity"] = validate_observation_fixture(target_config, fixture)
    checks["fixture_context_integrity"] = validate_curated_context_fixture(target_config, fixture)
    checks["fixture_numerical_integrity"] = validate_rolling_correlation_fixture(
        target_config, fixture
    )

    build_started = perf_counter()
    build = build_fixture_snapshot(target_config, fixture)
    build_duration = perf_counter() - build_started
    checks["fixture_build"] = {
        "status": build["status"],
        "snapshot_id": build["snapshot_id"],
        "row_count": build["row_count"],
        "duration_seconds": round(build_duration, 6),
        "target_seconds": BUILD_TARGET_SECONDS,
        "target_met": build_duration <= BUILD_TARGET_SECONDS,
    }
    checks["publication_recovery"] = validate_fixture_build(target_config, fixture)
    checks["fixture_reporting"] = validate_fixture_reporting(target_config, fixture)
    macro_graph = load_macro_economic_graph(target_config)
    checks["live_catalog_surface"] = {
        "status": "valid"
        if macro_graph["facets"]["series_count"] > 0
        and macro_graph["facets"]["concept_count"] > 0
        else "invalid",
        "series_count": macro_graph["facets"]["series_count"],
        "concept_count": macro_graph["facets"]["concept_count"],
        "snapshot_id": macro_graph["snapshot_id"],
    }
    checks["prepared_query_performance"] = benchmark_prepared_report_queries(
        target_config, samples
    )

    valid_statuses = {"valid", "fixture_snapshot_published", "fixture_snapshot_reused"}
    passed = all(
        result.get("status") in valid_statuses
        for result in checks.values()
        if isinstance(result, dict) and "status" in result
    ) and checks["fixture_build"]["target_met"]
    return {
        "status": "valid" if passed else "invalid",
        "fixture_sha256": sha256(fixture),
        "performance_targets": {
            "fixture_build_seconds": BUILD_TARGET_SECONDS,
            "prepared_query_p95_seconds": QUERY_P95_TARGET_SECONDS,
        },
        "checks": checks,
    }
