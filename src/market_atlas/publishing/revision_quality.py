"""Validate and atomically publish restricted, current-only revision quality."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from market_atlas.adapters.macro_context import build_revision_summary_extract
from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable
from market_atlas.ingestion.macro_medallion import _connect, stable_id
from market_atlas.publishing.fixture_build import _code_revision
from market_atlas.publishing.macro_context import (
    ELIGIBLE_STATUS,
    SOURCE_NAME,
    _as_timestamp,
    _sha256,
    _snapshot_summary,
)

PUBLICATION_NAME = "macro_revision_quality"
SOURCE_OBJECT = "gold.dim_series,gold.v_series_revision_summary"
TEMPORAL_STATUS = "current_only_revision_quality"
METHOD_VERSION = "macro-revision-quality-v1"
METRICS = (
    "observation_count",
    "avg_revision_count",
    "max_revision_count",
    "avg_abs_revision_pct",
    "max_abs_revision_pct",
)
SELECTION_FIELDS = ("source", "objects", "series_ids", "selection_scope", "page_size")


def validate_revision_extract(extract: dict[str, Any]) -> None:
    """Verify the entire T-016 envelope before starting any write transaction."""
    manifest = extract.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("status") != ELIGIBLE_STATUS:
        raise ValueError("revision quality requires an eligible extract manifest")
    if manifest.get("redistribution_status") != "restricted":
        raise ValueError("revision quality requires restricted internal-only rights")
    if manifest.get("temporal_status") != TEMPORAL_STATUS:
        raise ValueError("revision quality must remain current_only_revision_quality")
    gate = manifest.get("source_contract_verification")
    if not isinstance(gate, dict) or gate.get("status") != "valid":
        raise ValueError("revision quality requires valid source-contract verification")
    _sha256(gate.get("catalog_fingerprint_sha256"), "catalog fingerprint")
    if (
        not isinstance(gate.get("registry_version"), str)
        or not gate["registry_version"]
    ):
        raise ValueError("revision quality requires a source-contract registry version")
    _as_timestamp(manifest.get("extracted_at"), "extracted_at")
    if (
        manifest.get("source") != "macro_medallion_postgresql"
        or manifest.get("objects") != SOURCE_OBJECT.split(",")
        or manifest.get("selection_scope") != "configured_approved_dim_series"
    ):
        raise ValueError(
            "revision quality requires the approved bounded source selection"
        )
    selection = {field: manifest.get(field) for field in SELECTION_FIELDS}
    if sha256(selection) != manifest.get("input_selection_sha256"):
        raise ValueError("revision quality selection hash does not match its manifest")
    rows, missing = extract.get("revision_summaries"), extract.get("missing_series_ids")
    if not isinstance(rows, list) or not isinstance(missing, list):
        raise TypeError("revision quality rows and missing series must be lists")
    if sha256(
        {"revision_summaries": rows, "missing_series_ids": missing}
    ) != manifest.get("source_rows_sha256"):
        raise ValueError(
            "revision quality source rows hash does not match its manifest"
        )
    selected = manifest.get("series_ids")
    if not isinstance(selected, list) or type(manifest.get("page_size")) is not int:
        raise ValueError(
            "revision quality requires selected series and an integer page size"
        )
    # Reuse the extractor's field/range/duplicate rules, then verify missing accounting.
    normalized = build_revision_summary_extract(selected, rows, manifest["page_size"])
    if normalized["missing_series_ids"] != missing:
        raise ValueError(
            "revision quality missing series do not match selected summaries"
        )
    for row in rows:
        if any(
            type(row[field]) is not int
            for field in ("observation_count", "max_revision_count")
        ):
            raise ValueError("revision quality counts must be integers, not booleans")
        if (
            row["avg_revision_count"] > row["max_revision_count"]
            or row["avg_abs_revision_pct"] > row["max_abs_revision_pct"]
        ):
            raise ValueError("revision quality averages cannot exceed maxima")


def quality_records(extract: dict[str, Any]) -> list[dict[str, Any]]:
    validate_revision_extract(extract)
    by_id = {row["series_id"]: row for row in extract["revision_summaries"]}
    return [
        {
            "series_id": series_id,
            "quality_status": "available" if series_id in by_id else "unknown",
            **{field: by_id.get(series_id, {}).get(field) for field in METRICS},
        }
        for series_id in sorted(extract["manifest"]["series_ids"])
    ]


def load_revision_extract(path: Path) -> dict[str, Any]:
    try:
        extract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load revision quality extract at {path}") from error
    if not isinstance(extract, dict):
        raise TypeError("revision quality extract root must be an object")
    validate_revision_extract(extract)
    return extract


def _materialize_snapshot(
    cursor: Any,
    extract: dict[str, Any],
    node_ids: dict[str, Any],
    input_id: Any,
    build_id: Any,
    snapshot_id: Any,
) -> str:
    from psycopg.types.json import Jsonb

    manifest = extract["manifest"]
    extracted_at = _as_timestamp(manifest["extracted_at"], "extracted_at")
    payload = []
    for row in quality_records(extract):
        series_id = row["series_id"]
        version_id = stable_id("revision-quality-version", f"{input_id}:{series_id}")
        source_record = f"gold.v_series_revision_summary:{series_id}"
        details = {
            **row,
            "temporal_status": TEMPORAL_STATUS,
            "redistribution_status": "restricted",
            "source_extracted_at": extracted_at.isoformat(),
            "source_availability_time": None,
            "historical_support": "unsupported",
            "method_version": METHOD_VERSION,
            "summary_present": row["quality_status"] == "available",
        }
        cursor.execute(
            """INSERT INTO atlas.macro_revision_quality_version (
                revision_quality_version_id, input_manifest_id, series_node_id, series_id,
                quality_status, observation_count, avg_revision_count, max_revision_count,
                avg_abs_revision_pct, max_abs_revision_pct, source_record, source_extracted_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (input_manifest_id, series_id) DO NOTHING""",
            (
                version_id,
                input_id,
                node_ids[series_id],
                series_id,
                row["quality_status"],
                *(row[field] for field in METRICS),
                source_record,
                extracted_at,
            ),
        )
        cursor.execute(
            """INSERT INTO atlas_report.macro_revision_quality_snapshot (
                serving_snapshot_id, revision_quality_version_id, series_node_id, series_id,
                input_manifest_id, build_run_id, source_record, details
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                snapshot_id,
                version_id,
                node_ids[series_id],
                series_id,
                input_id,
                build_id,
                source_record,
                Jsonb(details),
            ),
        )
        cursor.execute(
            """INSERT INTO atlas_report.provenance_snapshot (
                serving_snapshot_id, provenance_kind, subject_id, build_run_id,
                input_manifest_id, source_record, method_version, input_selection_sha256, details
            ) VALUES (%s,'macro_revision_quality',%s,%s,%s,%s,%s,%s,%s)""",
            (
                snapshot_id,
                version_id,
                build_id,
                input_id,
                source_record,
                METHOD_VERSION,
                manifest["input_selection_sha256"],
                Jsonb(details),
            ),
        )
        payload.append([str(node_ids[series_id]), source_record, details])
    cursor.execute(
        """SELECT count(*), count(DISTINCT series_node_id) FROM
           atlas_report.macro_revision_quality_snapshot WHERE serving_snapshot_id = %s""",
        (snapshot_id,),
    )
    count, distinct = cursor.fetchone()
    if count != len(payload) or distinct != count:
        raise ValueError("revision quality report grain does not match selected series")
    return sha256(payload)


def publish_revision_quality(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Retain immutable inputs and publish a fully validated, separate snapshot."""
    records = quality_records(extract)
    manifest = extract["manifest"]
    # Capture time is part of identity: identical files reuse; a fresh capture gets
    # its own identity even if upstream values have not changed.
    manifest_hash = sha256(manifest)
    input_id = stable_id("revision-quality-input", manifest_hash)
    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))", (PUBLICATION_NAME,)
            )
            cursor.execute(
                """SELECT series_id, series_node_id FROM atlas.macro_series_taxonomy_current
                   WHERE series_id = ANY(%s)""",
                (manifest["series_ids"],),
            )
            node_ids = dict(cursor.fetchall())
            if set(node_ids) != set(manifest["series_ids"]):
                raise ValueError(
                    "revision quality requires already onboarded series identities"
                )
            configuration = {
                "publication": PUBLICATION_NAME,
                "method_version": METHOD_VERSION,
                "implementation_sha256": sha256(
                    Path(__file__).read_text(encoding="utf-8")
                ),
                "series_nodes": {
                    key: str(value) for key, value in sorted(node_ids.items())
                },
            }
            configuration_hash = sha256(configuration)
            code_revision = _code_revision()
            build_key = stable_id(
                "revision-quality-build-key",
                f"{manifest_hash}:{configuration_hash}:{code_revision}",
            )
            build_id = stable_id("revision-quality-build", str(build_key))
            snapshot_id = stable_id("revision-quality-snapshot", str(build_key))
            cursor.execute(
                """INSERT INTO atlas.input_manifest (
                    input_manifest_id, source_name, source_object, source_snapshot_reference,
                    manifest_sha256, extracted_at, redistribution_status, manifest
                ) VALUES (%s,%s,%s,%s,%s,%s,'restricted',%s) ON CONFLICT DO NOTHING""",
                (
                    input_id,
                    SOURCE_NAME,
                    SOURCE_OBJECT,
                    manifest["source_rows_sha256"],
                    manifest_hash,
                    _as_timestamp(manifest["extracted_at"], "extracted_at"),
                    Jsonb(manifest),
                ),
            )
            cursor.execute(
                """INSERT INTO atlas.build_run (
                    build_run_id, build_key, input_manifest_id, configuration_sha256,
                    configuration, code_revision, environment, run_status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,'building') ON CONFLICT DO NOTHING""",
                (
                    build_id,
                    build_key,
                    input_id,
                    configuration_hash,
                    Jsonb(configuration),
                    code_revision,
                    Jsonb({"python": platform.python_version()}),
                ),
            )
            cursor.execute(
                """INSERT INTO atlas.serving_snapshot (
                    serving_snapshot_id, snapshot_key, build_run_id, input_manifest_id, snapshot_status
                ) VALUES (%s,%s,%s,%s,'building') ON CONFLICT DO NOTHING""",
                (snapshot_id, snapshot_id, build_id, input_id),
            )
            existing = _snapshot_summary(cursor, snapshot_id)
            if existing["snapshot_status"] in {"published", "superseded"}:
                return {"status": "revision_quality_snapshot_reused", **existing}
            try:
                # Savepoint ensures a partial materialization leaves no rows, while
                # the outer transaction can retain the failed build diagnostics.
                with connection.transaction():
                    cursor.execute(
                        """UPDATE atlas.serving_snapshot SET snapshot_status='building',
                           failure_reason=NULL WHERE serving_snapshot_id=%s""",
                        (snapshot_id,),
                    )
                    cursor.execute(
                        """UPDATE atlas.build_run SET run_status='building', error_detail=NULL,
                           completed_at=NULL WHERE build_run_id=%s""",
                        (build_id,),
                    )
                    output_hash = _materialize_snapshot(
                        cursor, extract, node_ids, input_id, build_id, snapshot_id
                    )
                    counts = {
                        "selected_series": len(records),
                        "available": len(extract["revision_summaries"]),
                        "unknown": len(extract["missing_series_ids"]),
                    }
                    cursor.execute(
                        """UPDATE atlas.serving_snapshot SET snapshot_status='validated',
                           output_sha256=%s, row_count=%s, validation_summary=%s,
                           validated_at=clock_timestamp() WHERE serving_snapshot_id=%s""",
                        (output_hash, len(records), Jsonb(counts), snapshot_id),
                    )
                    cursor.execute(
                        "SELECT atlas.publish_serving_snapshot(%s,%s)",
                        (PUBLICATION_NAME, snapshot_id),
                    )
            except Exception as error:  # noqa: BLE001 - retain failure after rolling back the savepoint
                # A stage/type code is useful without copying SQL values or source
                # payloads from a driver's error message into retained diagnostics.
                reason = (
                    f"revision quality materialization failed ({type(error).__name__})"
                )
                cursor.execute(
                    """UPDATE atlas.build_run SET run_status='failed', error_detail=%s,
                       completed_at=clock_timestamp() WHERE build_run_id=%s""",
                    (reason, build_id),
                )
                cursor.execute(
                    """UPDATE atlas.serving_snapshot SET snapshot_status='failed', failure_reason=%s
                       WHERE serving_snapshot_id=%s""",
                    (reason, snapshot_id),
                )
                return {
                    "status": "revision_quality_snapshot_failed",
                    **_snapshot_summary(cursor, snapshot_id),
                }
            return {
                "status": "revision_quality_snapshot_published",
                **_snapshot_summary(cursor, snapshot_id),
                **counts,
            }
    except (ValueError, TypeError, DatabaseUnavailable):
        raise
    except Exception as error:
        raise DatabaseUnavailable(
            "revision quality publication failed; inspect local database availability"
        ) from error
