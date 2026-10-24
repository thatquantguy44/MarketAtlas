"""Immutable fixture builds and atomic publication of a serving snapshot."""

from __future__ import annotations

import platform
import subprocess
from typing import Any

from market_atlas.analytics.fixture_correlations import calculate_fixture_correlations
from market_atlas.analytics.rolling_correlation import (
    CONFIGURATION_SHA256 as CORRELATION_CONFIGURATION_SHA256,
)
from market_atlas.analytics.rolling_correlation import (
    METHOD_VERSION,
)
from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable
from market_atlas.graph.fixture_loader import _connect, load_fixture, stable_id

PUBLICATION_NAME = "default"


def _code_revision() -> str:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unresolved"
    value = revision.stdout.strip()
    if not value:
        return "unresolved"
    return f"{value}-dirty" if dirty.stdout.strip() else value


def _build_configuration(
    knowledge_cutoff: str | None, failure_marker: str | None
) -> dict[str, Any]:
    return {
        "calculation": {
            "method_version": METHOD_VERSION,
            "configuration_sha256": CORRELATION_CONFIGURATION_SHA256,
        },
        "knowledge_cutoff": knowledge_cutoff,
        "publication": PUBLICATION_NAME,
        "snapshot_contract": "rolling-correlation-fixture-v1",
        "failure_marker": failure_marker,
    }


def _snapshot_summary(cursor: Any, snapshot_id: Any) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT snapshot_status, row_count, output_sha256, failure_reason
        FROM atlas.serving_snapshot
        WHERE serving_snapshot_id = %s
        """,
        (snapshot_id,),
    )
    status, row_count, output_sha256, failure_reason = cursor.fetchone()
    return {
        "snapshot_id": str(snapshot_id),
        "snapshot_status": status,
        "row_count": row_count,
        "output_sha256": output_sha256,
        "failure_reason": failure_reason,
    }


def _mark_failed(
    config: TargetDatabaseConfig, build_run_id: Any, snapshot_id: Any, reason: str
) -> dict[str, Any]:
    with _connect(config) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE atlas.build_run
            SET run_status = 'failed', error_detail = %s, completed_at = clock_timestamp()
            WHERE build_run_id = %s
            """,
            (reason, build_run_id),
        )
        cursor.execute(
            """
            UPDATE atlas.serving_snapshot
            SET snapshot_status = 'failed', failure_reason = %s
            WHERE serving_snapshot_id = %s
            """,
            (reason, snapshot_id),
        )
        return _snapshot_summary(cursor, snapshot_id)


def build_fixture_snapshot(
    config: TargetDatabaseConfig,
    fixture: dict[str, Any],
    knowledge_cutoff: str | None = None,
    failure_marker: str | None = None,
) -> dict[str, Any]:
    """Build and publish a single immutable synthetic serving snapshot."""
    try:
        from psycopg.types.json import Jsonb

        load_fixture(config, fixture)
        calculate_fixture_correlations(config, fixture, knowledge_cutoff)
        fixture_hash = sha256(fixture)
        input_manifest_id = stable_id("input-manifest", fixture_hash)
        configuration = _build_configuration(knowledge_cutoff, failure_marker)
        configuration_sha256 = sha256(configuration)
        code_revision = _code_revision()
        build_key = stable_id(
            "build-key",
            f"{fixture_hash}:{configuration_sha256}:{code_revision}",
        )
        build_run_id = stable_id("build-run", str(build_key))
        snapshot_key = stable_id("serving-snapshot-key", str(build_key))
        snapshot_id = stable_id("serving-snapshot", str(snapshot_key))

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO atlas.build_run (
                    build_run_id, build_key, input_manifest_id, knowledge_cutoff,
                    configuration_sha256, configuration, code_revision, environment,
                    run_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'building')
                ON CONFLICT (build_key) DO NOTHING
                """,
                (
                    build_run_id,
                    build_key,
                    input_manifest_id,
                    knowledge_cutoff,
                    configuration_sha256,
                    Jsonb(configuration),
                    code_revision,
                    Jsonb({"python": platform.python_version()}),
                ),
            )
            cursor.execute(
                """
                INSERT INTO atlas.serving_snapshot (
                    serving_snapshot_id, snapshot_key, build_run_id, input_manifest_id,
                    knowledge_cutoff, snapshot_status
                ) VALUES (%s, %s, %s, %s, %s, 'building')
                ON CONFLICT (snapshot_key) DO NOTHING
                """,
                (
                    snapshot_id,
                    snapshot_key,
                    build_run_id,
                    input_manifest_id,
                    knowledge_cutoff,
                ),
            )
            existing = _snapshot_summary(cursor, snapshot_id)
            if existing["snapshot_status"] == "published":
                return {"status": "fixture_snapshot_reused", **existing}

        if failure_marker is not None:
            failed = _mark_failed(
                config,
                build_run_id,
                snapshot_id,
                f"injected fixture failure: {failure_marker}",
            )
            return {"status": "fixture_snapshot_failed", **failed}

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO atlas_report.rolling_correlation_estimate_snapshot (
                    serving_snapshot_id, rolling_correlation_estimate_version_id,
                    instrument_low_node_id, instrument_high_node_id,
                    endpoint_session_date, window_start_session_date,
                    paired_return_count, correlation, estimate_status,
                    knowledge_cutoff, method_version, configuration_sha256,
                    input_selection_sha256, input_manifest_id
                )
                SELECT
                    %s, rolling_correlation_estimate_version_id,
                    instrument_low_node_id, instrument_high_node_id,
                    endpoint_session_date, window_start_session_date,
                    paired_return_count, correlation, estimate_status,
                    knowledge_cutoff, method_version, configuration_sha256,
                    input_selection_sha256, input_manifest_id
                FROM atlas.rolling_correlation_estimate_version
                WHERE input_manifest_id = %s
                  AND knowledge_cutoff IS NOT DISTINCT FROM %s::timestamptz
                  AND recorded_to IS NULL
                ON CONFLICT DO NOTHING
                """,
                (snapshot_id, input_manifest_id, knowledge_cutoff),
            )
            cursor.execute(
                """
                SELECT
                    rolling_correlation_estimate_version_id::text,
                    endpoint_session_date::text, paired_return_count,
                    correlation::text, estimate_status, input_selection_sha256
                FROM atlas_report.rolling_correlation_estimate_snapshot
                WHERE serving_snapshot_id = %s
                ORDER BY rolling_correlation_estimate_version_id
                """,
                (snapshot_id,),
            )
            rows = [list(row) for row in cursor.fetchall()]
            if not rows:
                raise ValueError("fixture build has no eligible correlation estimates")
            output_sha256 = sha256(rows)
            cursor.execute(
                """
                UPDATE atlas.serving_snapshot
                SET snapshot_status = 'validated', output_sha256 = %s,
                    row_count = %s,
                    validation_summary = %s,
                    validated_at = clock_timestamp()
                WHERE serving_snapshot_id = %s
                """,
                (
                    output_sha256,
                    len(rows),
                    Jsonb(
                        {
                            "estimate_count": len(rows),
                            "input_manifest_id": str(input_manifest_id),
                            "output_sha256": output_sha256,
                        }
                    ),
                    snapshot_id,
                ),
            )
            cursor.execute(
                """
                UPDATE atlas.build_run
                SET run_status = 'validated', completed_at = clock_timestamp()
                WHERE build_run_id = %s
                """,
                (build_run_id,),
            )
            cursor.execute(
                "SELECT atlas.publish_serving_snapshot(%s, %s)",
                (PUBLICATION_NAME, snapshot_id),
            )
            result = _snapshot_summary(cursor, snapshot_id)
        return {"status": "fixture_snapshot_published", **result}
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001 - persist database build failures safely
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        try:
            failed = _mark_failed(config, build_run_id, snapshot_id, message)
        except (UnboundLocalError, DatabaseUnavailable):
            raise DatabaseUnavailable(f"fixture build failed: {message}") from error
        return {"status": "fixture_snapshot_failed", **failed}


def validate_fixture_build(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Prove idempotency and that an injected failure cannot move publication."""
    try:
        first = build_fixture_snapshot(config, fixture)
        second = build_fixture_snapshot(config, fixture)
        published_snapshot_id = first["snapshot_id"]
        failed = build_fixture_snapshot(config, fixture, failure_marker="validation")
        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT serving_snapshot_id::text
                FROM atlas.publication
                WHERE publication_name = %s
                """,
                (PUBLICATION_NAME,),
            )
            publication_snapshot_id = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT count(DISTINCT serving_snapshot_id), count(*)
                FROM atlas_report.current_rolling_correlation_estimate
                WHERE publication_name = %s
                """,
                (PUBLICATION_NAME,),
            )
            snapshot_count, published_row_count = cursor.fetchone()
            cursor.execute(
                """
                SELECT count(*)
                FROM atlas_report.rolling_correlation_estimate_snapshot
                WHERE serving_snapshot_id = %s::uuid
                """,
                (failed["snapshot_id"],),
            )
            failed_row_count = cursor.fetchone()[0]

        idempotent = (
            first["snapshot_id"] == second["snapshot_id"]
            and first["row_count"] == second["row_count"]
        )
        publication_atomic = (
            publication_snapshot_id == published_snapshot_id
            and snapshot_count == 1
            and published_row_count == first["row_count"]
        )
        failure_safe = (
            failed["snapshot_status"] == "failed"
            and failed_row_count == 0
            and publication_snapshot_id == published_snapshot_id
        )
        passed = all((idempotent, publication_atomic, failure_safe))
        return {
            "status": "valid" if passed else "invalid",
            "idempotent": idempotent,
            "publication_atomic": publication_atomic,
            "failure_safe": failure_safe,
            "published_row_count": published_row_count,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"fixture build validation failed: {message}"
        ) from error
