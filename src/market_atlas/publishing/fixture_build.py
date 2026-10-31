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

PUBLICATION_NAME = "synthetic_fixture"


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
        diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD"],
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
    if not dirty.stdout.strip():
        return value
    worktree_hash = sha256({"status": dirty.stdout, "diff": diff.stdout})[:12]
    return f"{value}-worktree-{worktree_hash}"


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
        "snapshot_contract": "reporting-provenance-fixture-v1",
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


def _materialize_reporting_snapshot(
    cursor: Any,
    snapshot_id: Any,
    build_run_id: Any,
    input_manifest_id: Any,
    effective_as_of: str,
    knowledge_cutoff: str | None,
) -> None:
    """Copy every report surface before the snapshot becomes publishable."""
    cursor.execute(
        """
        INSERT INTO atlas_report.node_snapshot (
            serving_snapshot_id, node_id, node_type, canonical_key,
            display_label, entity_status, provenance
        )
        SELECT %s, node_id, node_type, canonical_key,
               display_label, entity_status, provenance
        FROM atlas.node
        WHERE provenance->>'source' = 'synthetic-fixture'
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id,),
    )
    cursor.execute(
        """
        INSERT INTO atlas_report.relationship_snapshot (
            serving_snapshot_id, assertion_id, assertion_key, edge_type,
            source_node_id, source_node_type, target_node_id, target_node_type,
            relationship_kind, assertion_status, rationale, source_record,
            provenance, history_support
        )
        SELECT %s, relationship.assertion_id, relationship.assertion_key,
               relationship.edge_type, relationship.source_node_id,
               relationship.source_node_type, relationship.target_node_id,
               relationship.target_node_type, relationship.relationship_kind,
               relationship.assertion_status, stored.rationale,
               relationship.source_record, relationship.provenance,
               relationship.history_support
        FROM atlas.relationships_as_of(%s, %s, NULL) AS relationship
        JOIN atlas.reference_assertion AS stored
          ON stored.assertion_id = relationship.assertion_id
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id, effective_as_of, knowledge_cutoff),
    )
    cursor.execute(
        """
        INSERT INTO atlas_report.macro_context_snapshot (
            serving_snapshot_id, curated_macro_context_version_id,
            macro_series_node_id, target_node_id, target_node_type,
            mapping_kind, evidence_basis, semantic_label, rationale, mapping_owner,
            source_reference, taxonomy_provider, taxonomy_version,
            supporting_assertion_id, input_manifest_id, source_record, history_support
        )
        SELECT %s, curated_macro_context_version_id,
               macro_series_node_id, target_node_id, target_node_type,
               mapping_kind, evidence_basis, semantic_label, rationale, mapping_owner,
               source_reference, taxonomy_provider, taxonomy_version,
               supporting_assertion_id, input_manifest_id, source_record, history_support
        FROM atlas.curated_macro_context_as_of(%s, %s, NULL)
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id, effective_as_of, knowledge_cutoff),
    )

    cursor.execute(
        """
        SELECT assertion_id, source_node_id, target_node_id, edge_type, assertion_status
        FROM atlas_report.relationship_snapshot
        WHERE serving_snapshot_id = %s
          AND assertion_status IN ('accepted', 'disputed')
          AND history_support IN ('supported', 'current_context')
        """,
        (snapshot_id,),
    )
    adjacency: dict[Any, list[tuple[Any, Any, str, str]]] = {}
    for (
        assertion_id,
        source_id,
        target_id,
        edge_type,
        assertion_status,
    ) in cursor.fetchall():
        adjacency.setdefault(source_id, []).append(
            (target_id, assertion_id, edge_type, assertion_status)
        )
    cursor.execute(
        """
        SELECT node_id FROM atlas_report.node_snapshot
        WHERE serving_snapshot_id = %s
        """,
        (snapshot_id,),
    )
    paths: list[
        tuple[Any, Any, Any, int, list[Any], list[Any], list[str], list[str]]
    ] = []

    def walk(
        start_id: Any,
        endpoint_id: Any,
        node_path: list[Any],
        assertion_path: list[Any],
        edge_path: list[str],
        status_path: list[str],
    ) -> None:
        if len(assertion_path) == 4:
            return
        for target_id, assertion_id, edge_type, assertion_status in adjacency.get(
            endpoint_id, []
        ):
            if target_id in node_path:
                continue
            next_nodes = [*node_path, target_id]
            next_assertions = [*assertion_path, assertion_id]
            next_edges = [*edge_path, edge_type]
            next_statuses = [*status_path, assertion_status]
            path_key = stable_id(
                "snapshot-path",
                f"{snapshot_id}:{start_id}:" + ":".join(map(str, next_assertions)),
            )
            paths.append(
                (
                    snapshot_id,
                    path_key,
                    start_id,
                    target_id,
                    len(next_assertions),
                    next_nodes,
                    next_assertions,
                    next_edges,
                    next_statuses,
                )
            )
            walk(
                start_id,
                target_id,
                next_nodes,
                next_assertions,
                next_edges,
                next_statuses,
            )

    for (node_id,) in cursor.fetchall():
        walk(node_id, node_id, [node_id], [], [], [])
    if paths:
        cursor.executemany(
            """
            INSERT INTO atlas_report.bounded_path_snapshot (
                serving_snapshot_id, path_key, start_node_id, endpoint_node_id,
                depth, node_path, assertion_path, edge_type_path, assertion_status_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            paths,
        )

    cursor.execute(
        """
        INSERT INTO atlas_report.provenance_snapshot (
            serving_snapshot_id, provenance_kind, subject_id, build_run_id,
            input_manifest_id, source_record, supporting_assertion_id,
            knowledge_cutoff, details
        )
        SELECT %s, 'relationship', assertion_id, %s, %s, source_record, NULL, %s,
               jsonb_build_object(
                   'edge_type', edge_type,
                   'relationship_kind', relationship_kind,
                   'history_support', history_support
               )
        FROM atlas_report.relationship_snapshot
        WHERE serving_snapshot_id = %s
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id, build_run_id, input_manifest_id, knowledge_cutoff, snapshot_id),
    )
    cursor.execute(
        """
        INSERT INTO atlas_report.provenance_snapshot (
            serving_snapshot_id, provenance_kind, subject_id, build_run_id,
            input_manifest_id, source_record, supporting_assertion_id,
            knowledge_cutoff, details
        )
        SELECT %s, 'macro_context', curated_macro_context_version_id, %s,
               input_manifest_id, source_record, supporting_assertion_id, %s,
               jsonb_build_object(
                   'evidence_basis', evidence_basis,
                   'mapping_owner', mapping_owner,
                   'source_reference', source_reference,
                   'semantic_label', semantic_label
               )
        FROM atlas_report.macro_context_snapshot
        WHERE serving_snapshot_id = %s
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id, build_run_id, knowledge_cutoff, snapshot_id),
    )
    cursor.execute(
        """
        INSERT INTO atlas_report.provenance_snapshot (
            serving_snapshot_id, provenance_kind, subject_id, build_run_id,
            input_manifest_id, method_version, configuration_sha256,
            input_selection_sha256, knowledge_cutoff, details
        )
        SELECT %s, 'rolling_correlation', rolling_correlation_estimate_version_id, %s,
               input_manifest_id, method_version, configuration_sha256,
               input_selection_sha256, knowledge_cutoff,
               jsonb_build_object(
                   'estimate_status', estimate_status,
                   'paired_return_count', paired_return_count
               )
        FROM atlas_report.rolling_correlation_estimate_snapshot
        WHERE serving_snapshot_id = %s
        ON CONFLICT DO NOTHING
        """,
        (snapshot_id, build_run_id, snapshot_id),
    )


def _reporting_counts(cursor: Any, snapshot_id: Any) -> dict[str, int]:
    cursor.execute(
        """
        SELECT
            (SELECT count(*) FROM atlas_report.node_snapshot
             WHERE serving_snapshot_id = %s),
            (SELECT count(*) FROM atlas_report.relationship_snapshot
             WHERE serving_snapshot_id = %s),
            (SELECT count(*) FROM atlas_report.macro_context_snapshot
             WHERE serving_snapshot_id = %s),
            (SELECT count(*) FROM atlas_report.bounded_path_snapshot
             WHERE serving_snapshot_id = %s),
            (SELECT count(*) FROM atlas_report.provenance_snapshot
             WHERE serving_snapshot_id = %s)
        """,
        (snapshot_id, snapshot_id, snapshot_id, snapshot_id, snapshot_id),
    )
    nodes, relationships, contexts, paths, provenance = cursor.fetchone()
    return {
        "node_count": nodes,
        "relationship_count": relationships,
        "context_count": contexts,
        "path_count": paths,
        "provenance_count": provenance,
    }


def _snapshot_payload(cursor: Any, snapshot_id: Any) -> list[list[str]]:
    cursor.execute(
        """
        SELECT 'correlation', rolling_correlation_estimate_version_id::text
        FROM atlas_report.rolling_correlation_estimate_snapshot
        WHERE serving_snapshot_id = %s
        UNION ALL
        SELECT 'node', node_id::text
        FROM atlas_report.node_snapshot
        WHERE serving_snapshot_id = %s
        UNION ALL
        SELECT 'relationship', assertion_id::text
        FROM atlas_report.relationship_snapshot
        WHERE serving_snapshot_id = %s
        UNION ALL
        SELECT 'macro_context', curated_macro_context_version_id::text
        FROM atlas_report.macro_context_snapshot
        WHERE serving_snapshot_id = %s
        UNION ALL
        SELECT 'path', path_key::text
        FROM atlas_report.bounded_path_snapshot
        WHERE serving_snapshot_id = %s
        UNION ALL
        SELECT provenance_kind, subject_id::text
        FROM atlas_report.provenance_snapshot
        WHERE serving_snapshot_id = %s
        ORDER BY 1, 2
        """,
        (snapshot_id, snapshot_id, snapshot_id, snapshot_id, snapshot_id, snapshot_id),
    )
    return [list(row) for row in cursor.fetchall()]


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
            _materialize_reporting_snapshot(
                cursor,
                snapshot_id,
                build_run_id,
                input_manifest_id,
                fixture["sessions"][-1],
                knowledge_cutoff,
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
            reporting_counts = _reporting_counts(cursor, snapshot_id)
            output_sha256 = sha256(_snapshot_payload(cursor, snapshot_id))
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
                            **reporting_counts,
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


def validate_fixture_reporting(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Verify pinned report grains and provenance for one published snapshot."""
    try:
        build = build_fixture_snapshot(config, fixture)
        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT serving_snapshot_id::text
                FROM atlas_report.current_snapshot_metadata
                WHERE publication_name = %s
                """,
                (PUBLICATION_NAME,),
            )
            snapshot_id = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT
                    (SELECT count(*) FROM atlas_report.current_node_dimension),
                    (SELECT count(*) FROM atlas_report.current_relationship_fact),
                    (SELECT count(*) FROM atlas_report.current_macro_context_fact),
                    (SELECT count(*) FROM atlas_report.current_bounded_path_bridge),
                    (SELECT count(*) FROM atlas_report.current_provenance
                     WHERE serving_snapshot_id = %s::uuid)
                """,
                (snapshot_id,),
            )
            (
                node_count,
                relationship_count,
                context_count,
                path_count,
                provenance_count,
            ) = cursor.fetchone()
            cursor.execute(
                """
                SELECT
                    count(*),
                    count(DISTINCT correlation.rolling_correlation_estimate_version_id),
                    count(*) FILTER (WHERE low.node_id IS NOT NULL AND high.node_id IS NOT NULL)
                FROM atlas_report.current_rolling_correlation_estimate AS correlation
                JOIN atlas_report.current_node_dimension AS low
                  ON low.node_id = correlation.instrument_low_node_id
                JOIN atlas_report.current_node_dimension AS high
                  ON high.node_id = correlation.instrument_high_node_id
                WHERE correlation.publication_name = %s
                """,
                (PUBLICATION_NAME,),
            )
            (
                joined_correlation_count,
                distinct_correlation_count,
                resolved_endpoint_count,
            ) = cursor.fetchone()
            cursor.execute(
                """
                SELECT
                    EXISTS (
                        SELECT 1
                        FROM atlas_report.current_provenance AS provenance
                        JOIN atlas_report.current_relationship_fact AS relationship
                          ON relationship.assertion_id = provenance.subject_id
                        WHERE provenance.provenance_kind = 'relationship'
                          AND relationship.source_record = 'synthetic-fixture:A11'
                          AND provenance.source_record = relationship.source_record
                          AND provenance.serving_snapshot_id = %s::uuid
                    ),
                    EXISTS (
                        SELECT 1
                        FROM atlas_report.current_provenance AS provenance
                        JOIN atlas_report.current_macro_context_fact AS context
                          ON context.curated_macro_context_version_id = provenance.subject_id
                        WHERE provenance.provenance_kind = 'macro_context'
                          AND context.source_record = 'synthetic-fixture:CTX3'
                          AND provenance.supporting_assertion_id
                              = context.supporting_assertion_id
                          AND provenance.serving_snapshot_id = %s::uuid
                    ),
                    EXISTS (
                        SELECT 1
                        FROM atlas_report.current_provenance AS provenance
                        WHERE provenance.provenance_kind = 'rolling_correlation'
                          AND provenance.method_version IS NOT NULL
                          AND provenance.configuration_sha256 IS NOT NULL
                          AND provenance.input_selection_sha256 IS NOT NULL
                          AND provenance.serving_snapshot_id = %s::uuid
                    ),
                    (SELECT max(depth) <= 4
                     FROM atlas_report.current_bounded_path_bridge)
                """,
                (snapshot_id, snapshot_id, snapshot_id),
            )
            relationship_trace, context_trace, estimate_trace, paths_bounded = (
                cursor.fetchone()
            )
            cursor.execute(
                """
                SELECT count(DISTINCT serving_snapshot_id)
                FROM (
                    SELECT serving_snapshot_id FROM atlas_report.current_node_dimension
                    UNION ALL
                    SELECT serving_snapshot_id FROM atlas_report.current_relationship_fact
                    UNION ALL
                    SELECT serving_snapshot_id FROM atlas_report.current_macro_context_fact
                    UNION ALL
                    SELECT serving_snapshot_id FROM atlas_report.current_rolling_correlation_estimate
                    UNION ALL
                    SELECT serving_snapshot_id FROM atlas_report.current_provenance
                    WHERE serving_snapshot_id = %s::uuid
                ) AS report_rows
                """,
                (snapshot_id,),
            )
            snapshot_count = cursor.fetchone()[0]

        reconciled = (
            joined_correlation_count == build["row_count"]
            and distinct_correlation_count == build["row_count"]
            and resolved_endpoint_count == build["row_count"]
        )
        provenance_complete = all((relationship_trace, context_trace, estimate_trace))
        snapshot_pinned = snapshot_count == 1 and snapshot_id == build["snapshot_id"]
        report_grains_present = all(
            (
                node_count > 0,
                relationship_count > 0,
                context_count > 0,
                path_count > 0,
                provenance_count > 0,
                paths_bounded,
            )
        )
        passed = all(
            (reconciled, provenance_complete, snapshot_pinned, report_grains_present)
        )
        return {
            "status": "valid" if passed else "invalid",
            "snapshot_pinned": snapshot_pinned,
            "correlation_reconciled_without_multiplication": reconciled,
            "provenance_complete": provenance_complete,
            "report_grains_present": report_grains_present,
            "snapshot_id": snapshot_id,
            "node_count": node_count,
            "relationship_count": relationship_count,
            "context_count": context_count,
            "path_count": path_count,
            "provenance_count": provenance_count,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"fixture reporting validation failed: {message}"
        ) from error
