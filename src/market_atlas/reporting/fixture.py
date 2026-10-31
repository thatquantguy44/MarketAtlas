"""Credential-free Power BI data, calculated from the canonical fixture."""

from dataclasses import asdict
from datetime import date, datetime

from market_atlas.analytics.rolling_correlation import (
    CONFIGURATION_SHA256,
    METHOD_VERSION,
    MarketPoint,
    compute_rolling_correlations,
)
from market_atlas.contracts import sha256, validate_fixture
from market_atlas.fixtures import build_fixture


def fixture_tables():
    fixture = build_fixture()
    errors = validate_fixture(fixture)
    if errors:
        raise ValueError("invalid synthetic input: " + "; ".join(errors))
    input_hash = sha256(fixture)
    # This identity describes a file export, not a PostgreSQL serving snapshot.
    snapshot = "synthetic-file:" + input_hash
    common = {"serving_snapshot_id": snapshot, "publication_name": "synthetic_file"}
    tables = {}
    tables["nodes"] = [
        dict(
            common,
            node_id=r["id"],
            node_type=r["type"],
            display_label=r["label"],
            canonical_key="fixture:" + r["id"],
        )
        for r in fixture["entities"]
    ]
    latest = {}
    for row in sorted(fixture["assertions"], key=lambda r: r["recorded_at"]):
        latest[row["assertion_key"]] = row
    tables["relationships"] = [
        dict(
            common,
            assertion_id=r["id"],
            assertion_key=r["assertion_key"],
            source_node_id=r["source_id"],
            target_node_id=r["target_id"],
            edge_type=r["predicate"],
            relationship_kind=r["kind"],
            assertion_status=r["status"],
            rationale=r["rationale"],
            source_record="synthetic-fixture:" + r["id"],
            history_support="current_context",
        )
        for r in latest.values()
    ]
    tables["contexts"] = [
        dict(
            common,
            curated_macro_context_version_id=r["id"],
            macro_series_node_id=r["macro_series_id"],
            target_node_id=r["target_id"],
            mapping_kind=r["mapping_kind"],
            evidence_basis=r["evidence_basis"],
            rationale=r["rationale"],
            mapping_owner=r["mapping_owner"],
            source_record="synthetic-fixture:" + r["id"],
            semantic_label="context_only_not_measured_sensitivity_or_causality",
            supporting_assertion_id=r["supporting_assertion_id"],
        )
        for r in fixture["curated_contexts"]
    ]
    points = [
        MarketPoint(
            instrument_id=r["instrument_id"],
            session_date=date.fromisoformat(r["session"]),
            value=r["value"],
            unit=r["unit"],
            calendar_name=fixture["metadata"]["calendar"],
            adjustment_basis=r["adjustment"],
            available_at=datetime.fromisoformat(r["available_at"]),
            source_record=r["source_record"],
            selection_status="current_context",
        )
        for r in fixture["market_observations"]
    ]
    estimates = compute_rolling_correlations(
        map(date.fromisoformat, fixture["sessions"]),
        points,
        fixture["configured_pairs"],
    )
    tables["correlations"] = []
    for estimate in estimates:
        r = asdict(estimate)
        tables["correlations"].append(
            dict(
                common,
                rolling_correlation_estimate_version_id=sha256(
                    {
                        "pair": [r["instrument_low_id"], r["instrument_high_id"]],
                        "endpoint": r["endpoint_session_date"].isoformat(),
                        "input": input_hash,
                    }
                ),
                instrument_low_node_id=r["instrument_low_id"],
                instrument_high_node_id=r["instrument_high_id"],
                endpoint_session_date=r["endpoint_session_date"],
                window_start_session_date=r["window_start_session_date"],
                paired_return_count=r["paired_return_count"],
                correlation=r["correlation"],
                estimate_status=r["estimate_status"],
                knowledge_cutoff=None,
                method_version=METHOD_VERSION,
                configuration_sha256=CONFIGURATION_SHA256,
                input_selection_sha256=r["input_selection_sha256"],
            )
        )
    tables["provenance"] = []
    for table, kind, key in [
        ("relationships", "relationship", "assertion_id"),
        ("contexts", "macro_context", "curated_macro_context_version_id"),
        (
            "correlations",
            "rolling_correlation",
            "rolling_correlation_estimate_version_id",
        ),
    ]:
        for r in tables[table]:
            tables["provenance"].append(
                dict(
                    common,
                    provenance_kind=kind,
                    subject_id=r[key],
                    source_record=r.get(
                        "source_record", "synthetic-price-configured-pair"
                    ),
                    input_manifest_id=input_hash,
                    build_run_id=None,
                    method_version=r.get("method_version"),
                    knowledge_cutoff=None,
                    input_selection_sha256=r.get("input_selection_sha256"),
                )
            )
    metadata = [
        dict(
            common,
            published_at=None,
            build_run_id=None,
            input_manifest_id=input_hash,
            knowledge_cutoff=None,
            temporal_status="synthetic_current_context",
            synthetic=True,
            redistribution_status="generated_synthetic",
        )
    ]
    return metadata, tables
