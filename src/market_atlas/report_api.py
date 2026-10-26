"""Local report-only HTTP endpoint for the published macro economic graph."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from market_atlas.config import TargetDatabaseConfig
from market_atlas.database import DatabaseUnavailable

REPORT_READER_ROLE = "marketatlas_report_reader"


def load_macro_economic_graph(config: TargetDatabaseConfig) -> dict[str, Any]:
    """Read only the atomically published report views under the report role."""
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
                SELECT node_id::text, node_type, display_label, temporal_status,
                       source_record, details
                FROM atlas_report.current_macro_economic_graph_node
                ORDER BY node_type, display_label
                """
            )
            nodes = [
                {
                    "id": node_id,
                    "node_type": node_type,
                    "display_label": display_label,
                    "temporal_status": temporal_status,
                    "source_record": source_record,
                    "details": details,
                }
                for node_id, node_type, display_label, temporal_status, source_record, details in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT assertion_id::text, edge_type, source_node_id::text, target_node_id::text,
                       temporal_status, source_record, provenance
                FROM atlas_report.current_macro_economic_graph_edge
                ORDER BY assertion_id
                """
            )
            edges = [
                {
                    "id": assertion_id,
                    "edge_type": edge_type,
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "temporal_status": temporal_status,
                    "source_record": source_record,
                    "provenance": provenance,
                }
                for assertion_id, edge_type, source_node_id, target_node_id, temporal_status, source_record, provenance in cursor.fetchall()
            ]
    except (DatabaseUnavailable, ValueError):
        raise
    except Exception as error:  # noqa: BLE001
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"report API query failed: {message}") from error
    return {
        "publication": "macro_economic_graph",
        "snapshot_id": snapshot_id,
        "published_at": published_at,
        "input_manifest_id": input_manifest_id,
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
            if origin in {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5187", "http://127.0.0.1:5187"}:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            if self.path == "/healthz":
                self._send_json(HTTPStatus.OK, {"status": "ok", "service": "marketatlas-report-api"})
                return
            if self.path != "/api/v1/macro-economic-graph":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                self._send_json(HTTPStatus.OK, load_macro_economic_graph(config))
            except (DatabaseUnavailable, ValueError) as error:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
