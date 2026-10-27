"""Local report-only HTTP endpoint for the published macro economic graph."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from market_atlas.config import TargetDatabaseConfig
from market_atlas.database import DatabaseUnavailable

REPORT_READER_ROLE = "marketatlas_report_reader"


def load_revision_quality(config: TargetDatabaseConfig, series_node_id: str) -> dict[str, Any]:
    """Read one selected series from a single, independent quality snapshot."""
    try:
        series_node_id = str(UUID(series_node_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("series_node_id must be a UUID") from error
    try:
        import psycopg

        kwargs = config.connection_kwargs() | {
            "application_name": "marketatlas-quality-report-api",
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000",
        }
        with psycopg.connect(**kwargs) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            # A single SQL statement pins metadata and the selected row to one
            # MVCC snapshot even if another transaction publishes concurrently.
            cursor.execute(
                """WITH published AS (
                    SELECT serving_snapshot_id, published_at
                    FROM atlas_report.current_macro_revision_quality LIMIT 1
                )
                SELECT published.serving_snapshot_id::text, published.published_at::text,
                       selected.input_manifest_id::text, selected.build_run_id::text,
                       selected.series_node_id::text, selected.series_id,
                       selected.source_record, selected.details
                FROM published LEFT JOIN atlas_report.macro_revision_quality_snapshot AS selected
                  ON selected.serving_snapshot_id = published.serving_snapshot_id
                 AND selected.series_node_id = %s::uuid""", (series_node_id,),
            )
            result = cursor.fetchone()
    except Exception as error:
        raise DatabaseUnavailable("revision quality report is unavailable") from error
    if result is None:
        return {"publication": "macro_revision_quality", "status": "not_published",
                "series_node_id": series_node_id, "summary": None}
    snapshot_id, published_at, input_id, build_id, node_id, series_id, source_record, details = result
    return {"publication": "macro_revision_quality", "status": "selected" if node_id else "not_selected",
            "snapshot_id": snapshot_id, "published_at": published_at,
            "series_node_id": series_node_id, "input_manifest_id": input_id,
            "build_run_id": build_id, "source_record": source_record,
            "summary": {"series_id": series_id, **details} if details is not None else None}


def load_macro_economic_graph(
    config: TargetDatabaseConfig,
    concept_id: str | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Read a bounded graph neighborhood from report-only published views.

    The catalog publication can contain hundreds or thousands of series.  The
    default response is therefore a source-to-concept navigation graph; a
    concept selection returns one paged series neighborhood and its actual
    source-backed ``measures`` assertions.
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("offset must be zero or greater")
    search = query.strip() if query else ""
    try:
        import psycopg
    except ImportError as error:
        raise DatabaseUnavailable("PostgreSQL support is not installed") from error
    kwargs = config.connection_kwargs() | {
        "application_name": "marketatlas-report-api",
        "options": "-c default_transaction_read_only=on -c statement_timeout=5000",
    }
    try:
        with psycopg.connect(**kwargs) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            cursor.execute(
                """
                SELECT serving_snapshot_id::text, published_at::text, input_manifest_id::text
                FROM atlas_report.current_macro_economic_graph_node
                LIMIT 1
                """
            )
            metadata = cursor.fetchone()
            if metadata is None:
                raise ValueError("no macro economic graph snapshot is published")
            snapshot_id, published_at, input_manifest_id = metadata
            cursor.execute(
                """
                SELECT node.node_id::text, node.display_label, count(edge.assertion_id)::int
                FROM atlas_report.current_macro_economic_graph_node AS node
                LEFT JOIN atlas_report.current_macro_economic_graph_edge AS edge
                  ON edge.target_node_id = node.node_id
                WHERE node.node_type = 'economic_concept'
                GROUP BY node.node_id, node.display_label
                ORDER BY node.display_label
                """
            )
            concepts = cursor.fetchall()
            cursor.execute(
                """
                SELECT COALESCE(NULLIF(details->>'frequency', ''), 'Unspecified'), count(*)::int
                FROM atlas_report.current_macro_economic_graph_node
                WHERE node_type = 'macro_series'
                GROUP BY 1 ORDER BY 2 DESC, 1
                """
            )
            frequencies = [
                {"frequency": frequency, "series_count": count}
                for frequency, count in cursor.fetchall()
            ]
            total_series = sum(count for _, _, count in concepts)
            catalog_id = f"macro-catalog:{snapshot_id}"
            if concept_id:
                cursor.execute(
                    """
                    SELECT node_id::text, node_type, display_label, temporal_status, source_record, details
                    FROM atlas_report.current_macro_economic_graph_node
                    WHERE node_id::text = %s AND node_type = 'economic_concept'
                    """,
                    (concept_id,),
                )
                selected_concept = cursor.fetchone()
                if selected_concept is None:
                    raise ValueError("selected economic concept is not present in the published graph")
                cursor.execute(
                    """
                    SELECT count(*)::int
                    FROM atlas_report.current_macro_economic_graph_edge AS edge
                    JOIN atlas_report.current_macro_economic_graph_node AS series
                      ON series.node_id = edge.source_node_id
                    WHERE edge.target_node_id::text = %s
                      AND series.node_type = 'macro_series'
                      AND (%s = '' OR series.display_label ILIKE '%%' || %s || '%%'
                           OR series.details->>'canonical_key' ILIKE '%%' || %s || '%%')
                    """,
                    (concept_id, search, search, search),
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT edge.assertion_id::text, edge.edge_type, edge.source_node_id::text,
                           edge.target_node_id::text, edge.temporal_status, edge.source_record,
                           edge.provenance, series.node_type, series.display_label,
                           series.temporal_status, series.source_record, series.details,
                           concept.node_type, concept.display_label, concept.temporal_status,
                           concept.source_record, concept.details
                    FROM atlas_report.current_macro_economic_graph_edge AS edge
                    JOIN atlas_report.current_macro_economic_graph_node AS series
                      ON series.node_id = edge.source_node_id
                    JOIN atlas_report.current_macro_economic_graph_node AS concept
                      ON concept.node_id = edge.target_node_id
                    WHERE edge.target_node_id::text = %s
                      AND series.node_type = 'macro_series'
                      AND (%s = '' OR series.display_label ILIKE '%%' || %s || '%%'
                           OR series.details->>'canonical_key' ILIKE '%%' || %s || '%%')
                    ORDER BY series.display_label
                    LIMIT %s OFFSET %s
                    """,
                    (concept_id, search, search, search, limit, offset),
                )
                rows = cursor.fetchall()
                (
                    selected_id, selected_type, selected_label, selected_temporal,
                    selected_source_record, selected_details,
                ) = selected_concept
                nodes_by_id: dict[str, dict[str, Any]] = {
                    selected_id: {
                        "id": selected_id, "node_type": selected_type,
                        "display_label": selected_label, "temporal_status": selected_temporal,
                        "source_record": selected_source_record, "details": selected_details,
                    }
                }
                edges = []
                for (
                    assertion_id, edge_type, source_id, target_id, temporal_status, source_record,
                    provenance, source_type, source_label, source_temporal, source_source_record,
                    source_details, target_type, target_label, target_temporal, target_source_record,
                    target_details,
                ) in rows:
                    nodes_by_id[source_id] = {
                        "id": source_id, "node_type": source_type,
                        "display_label": source_label, "temporal_status": source_temporal,
                        "source_record": source_source_record, "details": source_details,
                    }
                    nodes_by_id[target_id] = {
                        "id": target_id, "node_type": target_type,
                        "display_label": target_label, "temporal_status": target_temporal,
                        "source_record": target_source_record, "details": target_details,
                    }
                    edges.append({
                        "id": assertion_id, "edge_type": edge_type,
                        "source_node_id": source_id, "target_node_id": target_id,
                        "temporal_status": temporal_status, "source_record": source_record,
                        "provenance": provenance,
                    })
                nodes = list(nodes_by_id.values())
                pagination = {"limit": limit, "offset": offset, "total": total}
                view = "concept_neighborhood"
            else:
                nodes = [{
                    "id": catalog_id, "node_type": "catalog_source",
                    "display_label": "Approved MacroMedallion catalog",
                    "temporal_status": "current_only",
                    "source_record": "atlas_report.current_macro_economic_graph_node",
                    "details": {"canonical_key": "macro-catalog", "temporal_status": "current_only"},
                }]
                edges = []
                for target_id, label, series_count in concepts:
                    nodes.append({
                        "id": target_id, "node_type": "economic_concept",
                        "display_label": label, "temporal_status": "current_only",
                        "source_record": "atlas_report.current_macro_economic_graph_node",
                        "details": {"canonical_key": f"published-concept:{target_id}", "temporal_status": "current_only", "series_count": series_count},
                    })
                    edges.append({
                        "id": f"catalog-navigation:{target_id}", "edge_type": "contains",
                        "source_node_id": catalog_id, "target_node_id": target_id,
                        "temporal_status": "current_only",
                        "source_record": "atlas_report.current_macro_economic_graph_edge",
                        "provenance": {"kind": "aggregate_navigation", "series_count": series_count},
                        "aggregate": True, "series_count": series_count,
                    })
                pagination = {"limit": 0, "offset": 0, "total": total_series}
                view = "catalog_summary"
    except (DatabaseUnavailable, ValueError):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"report API query failed: {message}") from error
    return {
        "publication": "macro_economic_graph",
        "snapshot_id": snapshot_id,
        "published_at": published_at,
        "input_manifest_id": input_manifest_id,
        "view": view,
        "facets": {"frequency": frequencies, "series_count": total_series, "concept_count": len(concepts)},
        "pagination": pagination,
        "nodes": nodes,
        "edges": edges,
    }


def serve_macro_economic_graph(
    config: TargetDatabaseConfig, host: str = "127.0.0.1", port: int = 8765
) -> None:
    """Serve the bounded report API on an explicit local interface."""
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            origin = self.headers.get("Origin", "")
            if origin in {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5187", "http://127.0.0.1:5187", "http://localhost:5188", "http://127.0.0.1:5188"}:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            request = urlparse(self.path)
            if request.path == "/healthz":
                self._send_json(HTTPStatus.OK, {"status": "ok", "service": "marketatlas-report-api"})
                return
            if request.path == "/api/v1/macro-revision-quality":
                params = parse_qs(request.query, keep_blank_values=True)
                try:
                    payload = load_revision_quality(config, params.get("series_node_id", [""])[0])
                    self._send_json(HTTPStatus.OK, payload)
                except ValueError as error:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                except DatabaseUnavailable as error:
                    self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})
                return
            if request.path != "/api/v1/macro-economic-graph":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                params = parse_qs(request.query, keep_blank_values=True)
                concept_id = params.get("concept_id", [None])[0] or None
                query = params.get("q", [None])[0] or None
                limit = int(params.get("limit", ["50"])[0])
                offset = int(params.get("offset", ["0"])[0])
                self._send_json(
                    HTTPStatus.OK,
                    load_macro_economic_graph(config, concept_id, query, limit, offset),
                )
            except (DatabaseUnavailable, ValueError) as error:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
