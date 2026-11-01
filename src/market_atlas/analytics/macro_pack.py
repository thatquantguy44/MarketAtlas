"""Immutable private JSON/CSV evidence packs for macro relationship research."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from market_atlas.analytics.macro_relationships import (
    METHOD_VERSION,
    calculate_relationships,
)
from market_atlas.analytics.macro_series import verify_prepared
from market_atlas.contracts import canonical_bytes, sha256

PACK_VERSION = "macro-analytics-pack-v1"
COMMON = "method_version:text prepared_sha256:text settings_sha256:text source_rows_sha256:text as_of:date captured_at:timestamp redistribution_status:text"
PANEL = "group_id:text knowledge_date:date reference_start:date reference_end:date input_sha256:text max_input_available_on:date"
SCHEMAS = {
    "series_eligibility": "group_id:text series_id:text unit:text transform:text orientation:integer frequency:text status:text raw_version_count:integer unknown_vintage_count:integer invalid_vintage_count:integer usable_period_count_as_of:integer earliest_usable_period_as_of:date observed_frequency:text observed_unit:text",
    "relationships": PANEL
    + " series_low_id:text series_high_id:text window_count:integer minimum_pairs:integer paired_count:integer coverage_ratio:number estimate_status:text correlation:number distance:number pair_input_sha256:text comparison_knowledge_date:date distance_change_status:text distance_change:number",
    "group_dispersion": PANEL
    + " member_count:integer usable_member_count:integer estimate_status:text group_mean_zscore:number dispersion:number baseline_window:integer minimum_baseline:integer comparison_knowledge_date:date dispersion_change_status:text dispersion_change:number",
    "node_divergence": PANEL
    + " series_id:text zscore:number zscore_status:text baseline_count:integer baseline_input_sha256:text current_change:number current_change_status:text deviation_from_group_mean:number absolute_deviation_from_group_mean:number group_comparison_status:text peer_count:integer usable_peer_count:integer peer_distance_status:text mean_peer_distance:number comparison_knowledge_date:date mean_peer_distance_change_status:text mean_peer_distance_change:number",
}
KEYS = {
    "series_eligibility": ["group_id", "series_id"],
    "relationships": ["group_id", "knowledge_date", "series_low_id", "series_high_id"],
    "group_dispersion": ["group_id", "knowledge_date"],
    "node_divergence": ["group_id", "knowledge_date", "series_id"],
}


def load_json(path: Path, *, max_bytes=512 * 1024 * 1024):
    if path.stat().st_size > max_bytes:
        raise ValueError("analytics artifact exceeds file-size bound")
    return json.loads(path.read_text(encoding="utf-8"))


def write_prepared(prepared, output: Path):
    verify_prepared(prepared)
    output.mkdir(parents=True, exist_ok=True)
    target = output / prepared["prepared_sha256"]
    payload = canonical_bytes(prepared)
    if target.exists():
        if (target / "prepared.json").read_bytes() != payload:
            raise ValueError("existing preparation has different content")
        return target / "prepared.json"
    stage = Path(tempfile.mkdtemp(prefix=".preparing-", dir=output))
    try:
        (stage / "prepared.json").write_bytes(payload)
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return target / "prepared.json"


def _pack_id(prepared):
    return sha256(
        {
            "pack_version": PACK_VERSION,
            "method_version": METHOD_VERSION,
            "prepared_sha256": prepared["prepared_sha256"],
        }
    )


def _artifact_files(prepared, results):
    common = {
        key: results[key]
        for key in (
            "method_version",
            "prepared_sha256",
            "settings_sha256",
            "source_rows_sha256",
        )
    }
    common.update(
        as_of=prepared["as_of"],
        captured_at=prepared["capture"]["manifest"]["extracted_at"],
        redistribution_status=prepared["settings"]["redistribution_status"],
    )
    tables = {
        "series_eligibility": prepared["eligibility"],
        **{table: results[table] for table in SCHEMAS if table != "series_eligibility"},
    }
    schema = {
        "pack_version": PACK_VERSION,
        "null_encoding": "empty_csv_field",
        "availability_precision": prepared["availability_precision"],
        "tables": {},
    }
    files = {
        "prepared.json": canonical_bytes(prepared),
        "results.json": canonical_bytes(results),
    }
    for table, rows in tables.items():
        columns = dict(
            part.split(":") for part in (COMMON + " " + SCHEMAS[table]).split()
        )
        schema["tables"][table] = {
            "file": f"{table}.csv",
            "columns": columns,
            "primary_key": KEYS[table],
            "row_count": len(rows),
        }
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        seen = set()
        for row in rows:
            key = tuple(row[k] for k in KEYS[table])
            if key in seen:
                raise ValueError("analytics output contains a duplicate table key")
            seen.add(key)
            if set(common) | set(row) != set(columns):
                raise ValueError(
                    "analytics output differs from its declared table schema"
                )
            writer.writerow({**common, **row})
        files[f"{table}.csv"] = stream.getvalue().encode("utf-8")
    files["schema.json"] = canonical_bytes(schema)
    return files, schema


def _manifest(prepared, results, files, schema):
    manifest = {
        "pack_version": PACK_VERSION,
        "pack_id": _pack_id(prepared),
        "method_version": METHOD_VERSION,
        "prepared_sha256": prepared["prepared_sha256"],
        "settings_sha256": prepared["settings_sha256"],
        "source_rows_sha256": results["source_rows_sha256"],
        "as_of": prepared["as_of"],
        "redistribution_status": prepared["settings"]["redistribution_status"],
        "interpretation": results["interpretation"],
        "row_counts": {
            table: info["row_count"] for table, info in schema["tables"].items()
        },
        "estimate_status_counts": {
            table: dict(
                sorted(Counter(r["estimate_status"] for r in results[table]).items())
            )
            for table in ("relationships", "group_dispersion")
        },
        "files": {
            name: {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
            for name, payload in sorted(files.items())
        },
    }
    return {**manifest, "manifest_sha256": sha256(manifest)}


def _summary(directory, manifest):
    return {
        "status": "valid",
        "pack_directory": str(directory),
        "pack_id": manifest["pack_id"],
        "prepared_sha256": manifest["prepared_sha256"],
        "row_counts": manifest["row_counts"],
        "estimate_status_counts": manifest["estimate_status_counts"],
    }


def validate_pack(directory: Path):
    """Recompute source selection, preparation, estimates, schemas and CSV bytes."""
    manifest = load_json(directory / "manifest.json", max_bytes=1024 * 1024)
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256(body):
        raise ValueError("analytics manifest integrity mismatch")
    expected_names = {"prepared.json", "results.json", "schema.json"} | {
        f"{table}.csv" for table in SCHEMAS
    }
    if set(manifest["files"]) != expected_names:
        raise ValueError("analytics manifest file set differs from the pack contract")
    for name in sorted(expected_names):
        path = directory / name
        if path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError("analytics artifact exceeds file-size bound")
        payload = path.read_bytes()
        if {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        } != manifest["files"][name]:
            raise ValueError(f"analytics file integrity mismatch: {name}")
    prepared = load_json(directory / "prepared.json")
    results = calculate_relationships(prepared)
    files, schema = _artifact_files(prepared, results)
    expected = _manifest(prepared, results, files, schema)
    if expected != manifest or any(
        (directory / name).read_bytes() != payload for name, payload in files.items()
    ):
        raise ValueError(
            "analytics pack differs from independently reconstructed artifacts"
        )
    return _summary(directory, manifest)


def build_pack(prepared_path: Path, output: Path):
    prepared = load_json(prepared_path)
    results = calculate_relationships(prepared)
    target = output / _pack_id(prepared)
    if target.exists():
        return validate_pack(target)
    output.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".building-", dir=output))
    try:
        files, schema = _artifact_files(prepared, results)
        manifest = _manifest(prepared, results, files, schema)
        for name, payload in files.items():
            (stage / name).write_bytes(payload)
        (stage / "manifest.json").write_bytes(canonical_bytes(manifest))
        validate_pack(stage)
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return _summary(target, manifest)
