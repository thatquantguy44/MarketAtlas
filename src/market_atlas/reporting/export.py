"""Immutable CSV packs with manifests, bounded report-only reads and validation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.database import DatabaseUnavailable

from .fixture import fixture_tables

CONTRACT = "marketatlas-powerbi-pack-v1"


def _generator():
    package = Path(__file__).resolve().parents[1]
    fingerprints = {
        str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package.rglob("*.py"))
    }
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=package,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = "unresolved"
    return {
        "python_version": platform.python_version(),
        "git_base_revision": revision,
        "source_sha256": sha256(fingerprints),
        "dependencies": "stdlib; psycopg only for published report reads",
    }


# Every SQL identifier comes from this allowlist, never from command-line text.
TABLES = {
    "synthetic_fixture": {
        "nodes": ("node_snapshot", ("node_id",)),
        "relationships": ("relationship_snapshot", ("assertion_id",)),
        "contexts": ("macro_context_snapshot", ("curated_macro_context_version_id",)),
        "correlations": (
            "rolling_correlation_estimate_snapshot",
            ("rolling_correlation_estimate_version_id",),
        ),
        "provenance": ("provenance_snapshot", ("provenance_kind", "subject_id")),
    },
    "macro_economic_graph": {
        "macro_nodes": ("macro_economic_graph_node_snapshot", ("node_id",)),
        "macro_edges": ("macro_economic_graph_edge_snapshot", ("assertion_id",)),
        "macro_graph_provenance": (
            "provenance_snapshot",
            ("provenance_kind", "subject_id"),
        ),
    },
    "macro_context": {
        "source_context": (
            "macro_source_context_snapshot",
            ("context_kind", "context_subject_id"),
        ),
        "source_context_provenance": (
            "provenance_snapshot",
            ("provenance_kind", "subject_id"),
        ),
    },
    "macro_revision_quality": {
        "revision_quality": ("macro_revision_quality_snapshot", ("series_node_id",)),
        "quality_provenance": (
            "provenance_snapshot",
            ("provenance_kind", "subject_id"),
        ),
    },
}
KEYS = {name: keys for tables in TABLES.values() for name, (_, keys) in tables.items()}
KEYS.update(publications=("publication_name",), pairs=("pair_id",), dates=("date",))
NUMBER_COLUMNS = {
    "correlation",
    "avg_revision_count",
    "avg_abs_revision_pct",
    "max_abs_revision_pct",
}
INTEGER_COLUMNS = {
    "paired_return_count",
    "row_count",
    "observation_count",
    "max_revision_count",
    "days_since_last",
}
DETAIL_COLUMNS = {
    "revision_quality": [
        "series_id",
        "quality_status",
        "observation_count",
        "avg_revision_count",
        "max_revision_count",
        "avg_abs_revision_pct",
        "max_abs_revision_pct",
        "temporal_status",
        "redistribution_status",
        "source_extracted_at",
        "source_availability_time",
        "historical_support",
        "method_version",
        "summary_present",
    ],
    "macro_nodes": [
        "canonical_key",
        "source",
        "frequency",
        "units",
        "econ_category",
        "geo",
        "metric",
        "source_extracted_at",
        "temporal_status",
    ],
    "source_context": [
        "series_id",
        "title",
        "source",
        "frequency",
        "units",
        "econ_category",
        "polarity",
        "default_transform",
        "scale",
        "decimals",
        "notes",
        "geo",
        "metric",
        "release_id",
        "release_name",
        "importance",
        "representative_series_id",
        "is_future",
        "source_fetched_at",
        "latest_observation_date",
        "observation_count",
        "days_since_last",
        "is_stale",
        "source_extracted_at",
    ],
}


def _scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str, allow_nan=False)
    return str(value)


def _flatten(row):
    result = {}
    for key, value in row.items():
        if isinstance(value, dict):
            # Retain complete JSON lineage as well as useful scalar columns.
            result[key + "_json"] = _scalar(value)
            if key == "details":
                result.update(
                    {
                        "details_" + k: v
                        for k, v in value.items()
                        if not isinstance(v, (dict, list, tuple))
                    }
                )
        else:
            result[key] = value
    return result


def _type(name, values):
    base = name.removeprefix("details_")
    present = [v for v in values if v is not None]
    if base in NUMBER_COLUMNS:
        return "number"
    if base in INTEGER_COLUMNS:
        return "integer"
    if base in {"is_stale", "is_future", "summary_present", "synthetic"} or (
        present and all(isinstance(v, bool) for v in present)
    ):
        return "logical"
    if base.endswith("_at") or base in {"knowledge_cutoff", "source_availability_time"}:
        return "datetimezone"
    if base == "date" or base.endswith("_date"):
        return "date"
    if present and all(isinstance(v, int) and not isinstance(v, bool) for v in present):
        return "integer"
    if present and all(
        isinstance(v, (float, int, Decimal)) and not isinstance(v, bool)
        for v in present
    ):
        return "number"
    return "text"


def _derived(tables):
    tables = dict(tables)
    correlations = tables.get("correlations")
    if correlations is not None:
        labels = {str(r["node_id"]): r["display_label"] for r in tables["nodes"]}
        pairs = {}
        for r in correlations:
            pair_id = (
                str(r["instrument_low_node_id"])
                + ":"
                + str(r["instrument_high_node_id"])
            )
            r["pair_id"] = pair_id
            pairs[pair_id] = {
                "pair_id": pair_id,
                "instrument_low_node_id": r["instrument_low_node_id"],
                "instrument_high_node_id": r["instrument_high_node_id"],
                "pair_label": labels[str(r["instrument_low_node_id"])]
                + " / "
                + labels[str(r["instrument_high_node_id"])],
            }
        tables["pairs"] = list(pairs.values())
        tables["dates"] = [
            {"date": d}
            for d in sorted({r["endpoint_session_date"] for r in correlations})
        ]
    return tables


def read_published(config, publications, max_rows=100000):
    """Read all selected surfaces within one repeatable-read, read-only transaction."""
    if (
        not publications
        or len(set(publications)) != len(publications)
        or any(p not in TABLES for p in publications)
    ):
        raise ValueError("select unique publications from: " + ", ".join(TABLES))
    if not 1 <= max_rows <= 1000000:
        raise ValueError("max_rows must be between 1 and 1000000 per table")
    try:
        import psycopg

        kwargs = config.connection_kwargs() | {
            "application_name": "marketatlas-powerbi-export",
            "options": "-c default_transaction_read_only=on -c statement_timeout=30000",
        }
        with psycopg.connect(**kwargs) as connection, connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            return _read_cursor(cursor, publications, max_rows)
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        # Server diagnostics can contain private connection details or row values.
        raise DatabaseUnavailable(
            "Power BI report export failed; check the local report connection and grants"
        ) from error


def _rows(cursor):
    columns = [c.name for c in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _read_cursor(cursor, publications, max_rows):
    cursor.execute(
        "SELECT * FROM atlas_report.current_snapshot_metadata WHERE publication_name = ANY(%s)",
        (list(publications),),
    )
    metadata = _rows(cursor)
    by_name = {r["publication_name"]: r for r in metadata}
    if set(by_name) != set(publications):
        raise ValueError("selected report publication is not published")
    tables = {}
    for publication in publications:
        snapshot_id = by_name[publication]["serving_snapshot_id"]
        for name, (table, keys) in TABLES[publication].items():
            cursor.execute(
                f"SELECT * FROM atlas_report.{table} WHERE serving_snapshot_id = %s "
                f"ORDER BY {', '.join(keys)} LIMIT %s",
                (snapshot_id, max_rows + 1),
            )
            columns = [c.name for c in cursor.description]
            rows = _rows(cursor)
            if len(rows) > max_rows:
                raise ValueError(f"{name} exceeds max_rows; no pack published")
            # Header-only exports retain the database schema when a fact has no rows.
            tables[name] = (
                columns,
                [dict(r, publication_name=publication) for r in rows],
            )
    return metadata, tables


def _csv_bytes(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: _scalar(r.get(k)) for k in columns} for r in rows)
    return stream.getvalue().encode("utf-8")


def export_pack(
    output: Path, *, config=None, publications=("synthetic_fixture",), max_rows=100000
):
    """Create or reuse a content-addressed pack; never replace a complete pack."""
    if config is None:
        metadata, source = fixture_tables()
        source = {k: (list(v[0]), v) for k, v in source.items()}
        source_kind, rights = "synthetic_fixture", "generated_synthetic"
    else:
        metadata, source = read_published(config, publications, max_rows)
        source_kind, rights = "published_report", "restricted_internal_only"
    columns = {name: cols for name, (cols, _) in source.items()}
    tables = _derived({name: rows for name, (_, rows) in source.items()})
    tables["publications"] = metadata
    payloads, descriptions = {}, {}
    for name, raw in sorted(tables.items()):
        rows = [_flatten(r) for r in raw]
        # Original JSON columns are replaced by explicit *_json columns.
        observed = {k for r in rows for k in r}
        if not rows:
            observed = {
                k + "_json"
                if k in {"provenance", "details", "validation_summary"}
                else k
                for k in columns.get(name, [])
            }
            if name not in {"pairs", "dates"}:
                observed.add("publication_name")
        observed.update("details_" + k for k in DETAIL_COLUMNS.get(name, []))
        headers = sorted(observed)
        if not headers:  # Empty derived tables still have usable typed headers.
            headers = (
                ["date"]
                if name == "dates"
                else [
                    "pair_id",
                    "pair_label",
                    "instrument_low_node_id",
                    "instrument_high_node_id",
                ]
            )
        rows.sort(key=lambda r: tuple(_scalar(r.get(k)) for k in KEYS[name]))
        payload = _csv_bytes(headers, rows)
        payloads[name] = payload
        descriptions[name] = {
            "file": name + ".csv",
            "rows": len(rows),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "primary_key": list(KEYS[name]),
            "columns": [
                {"name": k, "type": _type(k, [r.get(k) for r in rows])} for k in headers
            ],
        }
    manifest = {
        "contract": CONTRACT,
        "source_kind": source_kind,
        "redistribution_status": rights,
        "generator": _generator(),
        "tables": descriptions,
    }
    manifest["pack_id"] = sha256(manifest)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / manifest["pack_id"]
    if destination.exists():
        if validate_pack(destination)["pack_id"] != manifest["pack_id"]:
            raise ValueError("existing pack directory has a different identity")
        return {
            "status": "reused",
            "pack": str(destination),
            "pack_id": manifest["pack_id"],
        }
    staging = Path(tempfile.mkdtemp(prefix=".powerbi-", dir=output))
    try:
        for name, payload in payloads.items():
            (staging / (name + ".csv")).write_bytes(payload)
        (staging / "manifest.json").write_bytes(canonical_bytes(manifest))
        validate_pack(staging)
        try:
            os.rename(staging, destination)
        except OSError:
            # Another identical job may have finished while we were validating.
            if not destination.exists():
                raise
            if validate_pack(destination)["pack_id"] != manifest["pack_id"]:
                raise ValueError("existing pack directory has a different identity")
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "status": "exported",
        "pack": str(destination),
        "pack_id": manifest["pack_id"],
    }


def validate_pack(directory: Path):
    manifest = json.loads((directory / "manifest.json").read_text())
    identity = {k: v for k, v in manifest.items() if k != "pack_id"}
    if manifest.get("contract") != CONTRACT or manifest.get("pack_id") != sha256(
        identity
    ):
        raise ValueError("invalid pack contract or manifest identity")
    tables = {}
    for name, table in manifest["tables"].items():
        if name not in KEYS or table["file"] != name + ".csv":
            raise ValueError("invalid pack table/file")
        payload = (directory / table["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != table["sha256"]:
            raise ValueError(f"{name}: checksum mismatch")
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
        if reader.fieldnames != [c["name"] for c in table["columns"]]:
            raise ValueError(f"{name}: schema mismatch")
        rows = list(reader)
        if len(rows) != table["rows"]:
            raise ValueError(f"{name}: row count mismatch")
        seen = set()
        for row in rows:
            key = tuple(row.get(k) for k in KEYS[name])
            if not all(key) or key in seen:
                raise ValueError(f"{name}: empty or duplicate key")
            seen.add(key)
            for col in table["columns"]:
                value = row[col["name"]]
                if value == "":
                    continue
                kind = col["type"]
                if kind == "integer":
                    int(value)
                elif kind == "number" and not math.isfinite(float(value)):
                    raise ValueError(f"{name}: non-finite number")
                elif kind == "logical" and value not in {"true", "false"}:
                    raise ValueError(f"{name}: invalid logical value")
                elif kind == "date":
                    date.fromisoformat(value)
                elif (
                    kind == "datetimezone"
                    and datetime.fromisoformat(value).tzinfo is None
                ):
                    raise ValueError(f"{name}: timestamp has no timezone")
        tables[name] = rows
    _validate_relations(tables)
    return {
        "status": "valid",
        "pack_id": manifest["pack_id"],
        "counts": {name: len(rows) for name, rows in tables.items()},
    }


def _validate_relations(tables):
    metadata = {
        r["publication_name"]: r["serving_snapshot_id"] for r in tables["publications"]
    }
    for name, rows in tables.items():
        if name in {"publications", "pairs", "dates"}:
            continue
        for row in rows:
            if row["serving_snapshot_id"] != metadata.get(row["publication_name"]):
                raise ValueError(f"{name}: mixed publication snapshots")
    for dim, facts in [
        (
            "nodes",
            {
                "relationships": ("source_node_id", "target_node_id"),
                "contexts": ("macro_series_node_id", "target_node_id"),
                "correlations": ("instrument_low_node_id", "instrument_high_node_id"),
            },
        ),
        ("macro_nodes", {"macro_edges": ("source_node_id", "target_node_id")}),
    ]:
        if dim not in tables:
            continue
        ids = {r["node_id"] for r in tables[dim]}
        for name, keys in facts.items():
            for row in tables.get(name, []):
                if any(row[k] not in ids for k in keys):
                    raise ValueError(f"{name}: orphan endpoint")
    for row in tables.get("correlations", []):
        value = row["correlation"]
        if row["estimate_status"] == "supported":
            if value == "" or not -1 <= float(value) <= 1:
                raise ValueError("invalid supported correlation")
        elif value != "":
            raise ValueError("undefined correlation must be null")
        if (
            int(row["paired_return_count"]) < 0
            or row["window_start_session_date"] > row["endpoint_session_date"]
        ):
            raise ValueError("invalid correlation sample or window")
    if "correlations" in tables:
        pairs = {r["pair_id"] for r in tables["pairs"]}
        dates = {r["date"] for r in tables["dates"]}
        if any(
            r["pair_id"] not in pairs or r["endpoint_session_date"] not in dates
            for r in tables["correlations"]
        ):
            raise ValueError("correlation has no pair or date dimension")
        expected = {
            (kind, r[key])
            for name, kind, key in (
                ("relationships", "relationship", "assertion_id"),
                ("contexts", "macro_context", "curated_macro_context_version_id"),
                (
                    "correlations",
                    "rolling_correlation",
                    "rolling_correlation_estimate_version_id",
                ),
            )
            for r in tables[name]
        }
        actual = {(r["provenance_kind"], r["subject_id"]) for r in tables["provenance"]}
        if expected != actual:
            raise ValueError("core report provenance is missing or orphaned")
    for row in tables.get("revision_quality", []):
        metrics = (
            "observation_count",
            "avg_revision_count",
            "max_revision_count",
            "avg_abs_revision_pct",
            "max_abs_revision_pct",
        )
        status = row.get("details_quality_status")
        values = [row.get("details_" + k) for k in metrics]
        if status == "unknown" and any(v not in (None, "") for v in values):
            raise ValueError("unknown quality metrics must be null")
        if status not in {"unknown", "available"} or (
            status == "available" and any(v in (None, "") for v in values)
        ):
            raise ValueError("invalid revision-quality status or incomplete metrics")
        if status == "available" and (
            any(float(v) < 0 for v in values)
            or float(values[1]) > float(values[2])
            or float(values[3]) > float(values[4])
        ):
            raise ValueError("invalid revision-quality metrics")
