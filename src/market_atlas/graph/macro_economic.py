"""Current-only macro taxonomy graph projection and immutable publication."""

from __future__ import annotations

import platform
import re
from datetime import datetime
from typing import Any

from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable
from market_atlas.ingestion.macro_medallion import _connect, stable_id
from market_atlas.publishing.fixture_build import _code_revision
from market_atlas.publishing.macro_context import (
    _manifest_identity,
    _snapshot_summary,
    ingest_context_extract,
    validate_context_extract,
)

PUBLICATION_NAME = "macro_economic_graph"
_NON_IDENTIFIER = re.compile(r"[^a-z0-9]+")


def _concept_key(category: str) -> str:
    normalized = _NON_IDENTIFIER.sub("-", category.strip().casefold()).strip("-")
    if not normalized:
        raise ValueError("macro taxonomy econ_category must contain letters or numbers")
    return normalized


def _concept_label(category: str) -> str:
    return " ".join(part.capitalize() for part in _concept_key(category).split("-"))


def project_macro_economic_graph(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Project the approved current taxonomy into source-backed graph assertions."""
    validate_context_extract(extract)
    manifest = extract["manifest"]
    input_manifest_id = stable_id("macro-context-input-manifest", _manifest_identity(manifest))
    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT taxonomy.series_node_id, taxonomy.series_id, taxonomy.econ_category,
                       taxonomy.source_record, taxonomy.source_extracted_at
                FROM atlas.macro_series_taxonomy_current AS taxonomy
                WHERE taxonomy.input_manifest_id = %s
                ORDER BY taxonomy.series_id
                """,
                (input_manifest_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                raise ValueError("macro taxonomy must be ingested before graph projection")
            if manifest.get("selection_scope") == "all_approved_dim_series":
                cursor.execute(
                    """DELETE FROM atlas.macro_taxonomy_concept_current
                       WHERE input_manifest_id <> %s""",
                    (input_manifest_id,),
                )
            else:
                cursor.execute(
                    """DELETE FROM atlas.macro_taxonomy_concept_current
                       WHERE series_node_id = ANY(%s) AND input_manifest_id <> %s""",
                    ([row[0] for row in rows], input_manifest_id),
                )
            projected_edges = 0
            categories: set[str] = set()
            for series_node_id, series_id, category, taxonomy_record, extracted_at in rows:
                if not isinstance(category, str) or not category.strip():
                    continue
                concept_key = _concept_key(category)
                categories.add(concept_key)
                concept_canonical_key = f"economic-concept:macro-category:{concept_key}"
                concept_node_id = stable_id("economic-concept", concept_canonical_key)
                cursor.execute(
                    """
                    INSERT INTO atlas.node (
                        node_id, node_type, canonical_key, display_label, entity_status, provenance
                    ) VALUES (%s, 'economic_concept', %s, %s, 'active', %s)
                    ON CONFLICT (node_type, canonical_key) DO UPDATE
                    SET display_label = EXCLUDED.display_label, provenance = EXCLUDED.provenance
                    RETURNING node_id
                    """,
                    (
                        concept_node_id, concept_canonical_key, _concept_label(category),
                        Jsonb({"source": "macro_medallion_ecomedallion", "source_object": "gold.dim_series",
                               "taxonomy_field": "econ_category", "temporal_status": "current_only"}),
                    ),
                )
                concept_node_id = cursor.fetchone()[0]
                source_record = f"{taxonomy_record}:econ_category:{concept_key}"
                projection_id = stable_id("macro-taxonomy-concept", source_record)
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_taxonomy_concept_current (
                        macro_taxonomy_concept_id, series_node_id, economic_concept_node_id,
                        input_manifest_id, source_record, source_extracted_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (series_node_id, economic_concept_node_id) DO UPDATE SET
                        input_manifest_id = EXCLUDED.input_manifest_id,
                        source_record = EXCLUDED.source_record,
                        source_extracted_at = EXCLUDED.source_extracted_at,
                        recorded_at = clock_timestamp()
                    """,
                    (projection_id, series_node_id, concept_node_id, input_manifest_id, source_record, extracted_at),
                )
                assertion_id = stable_id("macro-taxonomy-measures", source_record)
                provenance = Jsonb({
                    "source": "macro_medallion_ecomedallion", "source_object": "gold.dim_series",
                    "source_record": taxonomy_record, "taxonomy_field": "econ_category",
                    "taxonomy_value": category, "temporal_status": "current_only",
                    "input_manifest_id": str(input_manifest_id),
                })
                cursor.execute(
                    """
                    INSERT INTO atlas.reference_assertion (
                        assertion_id, assertion_key, edge_type, source_node_id, source_node_type,
                        target_node_id, target_node_type, relationship_kind, assertion_status,
                        valid_from, available_at, availability_status, source_record, provenance
                    ) VALUES (%s, %s, 'measures', %s, 'macro_series', %s, 'economic_concept',
                              'reference', 'accepted', %s::date, %s, 'known', %s, %s)
                    ON CONFLICT (assertion_id) DO UPDATE SET
                        available_at = EXCLUDED.available_at, source_record = EXCLUDED.source_record,
                        provenance = EXCLUDED.provenance
                    """,
                    (assertion_id, assertion_id, series_node_id, concept_node_id,
                     extracted_at.date(), extracted_at, source_record, provenance),
                )
                projected_edges += 1
        return {
            "status": "macro_economic_graph_projected_current_only",
            "input_manifest_id": str(input_manifest_id),
            "series_count": len(rows),
            "edge_count": projected_edges,
            "concept_count": len(categories),
            "unclassified_series_count": len(rows) - projected_edges,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"macro economic graph projection failed: {message}") from error


def publish_macro_economic_graph(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Snapshot-publish current source taxonomy nodes and their measures edges."""
    validate_context_extract(extract)
    manifest = extract["manifest"]
    input_manifest_id = stable_id("macro-context-input-manifest", _manifest_identity(manifest))
    configuration = {
        "publication": PUBLICATION_NAME, "snapshot_contract": "macro-economic-graph-v1",
        "temporal_semantics": "current_only", "input_selection_sha256": manifest["input_selection_sha256"],
    }
    configuration_sha256 = sha256(configuration)
    code_revision = _code_revision()
    build_key = stable_id("macro-economic-graph-build", f"{input_manifest_id}:{configuration_sha256}:{code_revision}")
    build_run_id = stable_id("macro-economic-graph-run", str(build_key))
    snapshot_key = stable_id("macro-economic-graph-snapshot-key", str(build_key))
    snapshot_id = stable_id("macro-economic-graph-snapshot", str(snapshot_key))
    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO atlas.build_run (
                       build_run_id, build_key, input_manifest_id, configuration_sha256,
                       configuration, code_revision, environment, run_status
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'building')
                   ON CONFLICT (build_key) DO NOTHING""",
                (build_run_id, build_key, input_manifest_id, configuration_sha256, Jsonb(configuration),
                 code_revision, Jsonb({"python": platform.python_version()})),
            )
            cursor.execute(
                """INSERT INTO atlas.serving_snapshot (
                       serving_snapshot_id, snapshot_key, build_run_id, input_manifest_id, snapshot_status
                   ) VALUES (%s, %s, %s, %s, 'building') ON CONFLICT (snapshot_key) DO NOTHING""",
                (snapshot_id, snapshot_key, build_run_id, input_manifest_id),
            )
            existing = _snapshot_summary(cursor, snapshot_id)
            if existing["snapshot_status"] == "published":
                return {"status": "macro_economic_graph_reused", **existing}
            cursor.execute(
                """
                SELECT projection.series_node_id, projection.economic_concept_node_id,
                       assertion.assertion_id, assertion.source_record, assertion.provenance
                FROM atlas.macro_taxonomy_concept_current AS projection
                JOIN atlas.reference_assertion AS assertion
                  ON assertion.source_node_id = projection.series_node_id
                 AND assertion.target_node_id = projection.economic_concept_node_id
                 AND assertion.edge_type = 'measures'
                 AND assertion.recorded_to IS NULL
                WHERE projection.input_manifest_id = %s
                ORDER BY projection.series_node_id
                """,
                (input_manifest_id,),
            )
            edges = cursor.fetchall()
            if not edges:
                raise ValueError("macro economic graph has no source-backed measures edges")
            cursor.execute(
                """
                SELECT taxonomy.series_node_id, node.node_type, node.display_label,
                       node.canonical_key, taxonomy.source_record, taxonomy.source,
                       taxonomy.frequency, taxonomy.units, taxonomy.econ_category,
                       taxonomy.geo, taxonomy.metric
                FROM atlas.macro_series_taxonomy_current AS taxonomy
                JOIN atlas.node AS node ON node.node_id = taxonomy.series_node_id
                WHERE taxonomy.input_manifest_id = %s
                ORDER BY taxonomy.series_id
                """,
                (input_manifest_id,),
            )
            taxonomy_nodes = cursor.fetchall()
            if not taxonomy_nodes:
                raise ValueError("macro economic graph has no selected taxonomy nodes")
            node_ids = sorted(
                {row[0] for row in taxonomy_nodes} | {edge[1] for edge in edges},
                key=str,
            )
            cursor.execute(
                """
                SELECT node_id, node_type, display_label, canonical_key
                FROM atlas.node WHERE node_id = ANY(%s) ORDER BY node_type, canonical_key
                """,
                (node_ids,),
            )
            concept_nodes = {row[0]: row[1:] for row in cursor.fetchall()}
            node_count = 0
            for (
                node_id, node_type, display_label, canonical_key, taxonomy_record, source,
                frequency, units, category, geo, metric,
            ) in taxonomy_nodes:
                cursor.execute(
                    """INSERT INTO atlas_report.macro_economic_graph_node_snapshot (
                           serving_snapshot_id, node_id, node_type, display_label, temporal_status,
                           input_manifest_id, source_record, details
                       ) VALUES (%s, %s, %s, %s, 'current_only', %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (snapshot_id, node_id, node_type, display_label, input_manifest_id, taxonomy_record,
                     Jsonb({
                         "canonical_key": canonical_key, "source": source,
                         "frequency": frequency, "units": units, "econ_category": category,
                         "geo": geo, "metric": metric, "temporal_status": "current_only",
                     })),
                )
                node_count += 1
            for node_id in sorted({edge[1] for edge in edges}, key=str):
                node_type, display_label, canonical_key = concept_nodes[node_id]
                source_record = f"macro-economic-graph-node:{canonical_key}"
                cursor.execute(
                    """INSERT INTO atlas_report.macro_economic_graph_node_snapshot (
                           serving_snapshot_id, node_id, node_type, display_label, temporal_status,
                           input_manifest_id, source_record, details
                       ) VALUES (%s, %s, %s, %s, 'current_only', %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (snapshot_id, node_id, node_type, display_label, input_manifest_id, source_record,
                     Jsonb({"canonical_key": canonical_key, "temporal_status": "current_only"})),
                )
                node_count += 1
            for source_id, target_id, assertion_id, source_record, provenance in edges:
                cursor.execute(
                    """INSERT INTO atlas_report.macro_economic_graph_edge_snapshot (
                           serving_snapshot_id, assertion_id, edge_type, source_node_id, target_node_id,
                           temporal_status, input_manifest_id, source_record, provenance
                       ) VALUES (%s, %s, 'measures', %s, %s, 'current_only', %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (snapshot_id, assertion_id, source_id, target_id, input_manifest_id, source_record, Jsonb(provenance)),
                )
                cursor.execute(
                    """INSERT INTO atlas_report.provenance_snapshot (
                           serving_snapshot_id, provenance_kind, subject_id, build_run_id, input_manifest_id,
                           source_record, input_selection_sha256, details
                       ) SELECT %s, 'macro_economic_graph', %s, %s, %s, %s,
                                manifest->>'input_selection_sha256', %s
                         FROM atlas.input_manifest WHERE input_manifest_id = %s
                       ON CONFLICT DO NOTHING""",
                    (snapshot_id, assertion_id, build_run_id, input_manifest_id, source_record, Jsonb(provenance), input_manifest_id),
                )
            cursor.execute(
                """SELECT node_id::text, node_type, display_label, source_record, details
                   FROM atlas_report.macro_economic_graph_node_snapshot
                   WHERE serving_snapshot_id = %s ORDER BY node_id""",
                (snapshot_id,),
            )
            nodes_payload = [list(row) for row in cursor.fetchall()]
            cursor.execute(
                """SELECT assertion_id::text, source_node_id::text, target_node_id::text,
                          edge_type, source_record, provenance
                   FROM atlas_report.macro_economic_graph_edge_snapshot
                   WHERE serving_snapshot_id = %s ORDER BY assertion_id""",
                (snapshot_id,),
            )
            edges_payload = [list(row) for row in cursor.fetchall()]
            output_sha256 = sha256({"nodes": nodes_payload, "edges": edges_payload})
            row_count = node_count + len(edges)
            cursor.execute(
                """UPDATE atlas.serving_snapshot SET snapshot_status = 'validated', output_sha256 = %s,
                       row_count = %s, validation_summary = %s, validated_at = clock_timestamp()
                   WHERE serving_snapshot_id = %s""",
                (output_sha256, row_count, Jsonb({"node_count": node_count, "edge_count": len(edges), "output_sha256": output_sha256}), snapshot_id),
            )
            cursor.execute("UPDATE atlas.build_run SET run_status = 'validated', completed_at = clock_timestamp() WHERE build_run_id = %s", (build_run_id,))
            cursor.execute("SELECT atlas.publish_serving_snapshot(%s, %s)", (PUBLICATION_NAME, snapshot_id))
            result = _snapshot_summary(cursor, snapshot_id)
        return {"status": "macro_economic_graph_published", **result, "node_count": node_count, "edge_count": len(edges)}
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"macro economic graph publication failed: {message}") from error


def build_macro_economic_graph(config: TargetDatabaseConfig, extract: dict[str, Any]) -> dict[str, Any]:
    """Load current context, project source-backed edges, and publish one graph snapshot."""
    return {
        "ingestion": ingest_context_extract(config, extract),
        "projection": project_macro_economic_graph(config, extract),
        "publication": publish_macro_economic_graph(config, extract),
    }
