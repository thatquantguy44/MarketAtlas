"""Persist and snapshot-publish approved MacroMedallion context extracts."""

from __future__ import annotations

import json
import platform
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable
from market_atlas.ingestion.macro_medallion import _connect, stable_id
from market_atlas.publishing.fixture_build import _code_revision

SOURCE_NAME = "macro_medallion_ecomedallion"
SOURCE_OBJECT = "gold.dim_series,gold.release_calendar,gold.v_source_coverage"
PUBLICATION_NAME = "macro_context"
ELIGIBLE_STATUS = "source_contract_extracted; not_loaded_to_marketatlas_graph"
ALLOWED_REDISTRIBUTION_STATUSES = {"approved", "unresolved", "restricted"}


def _as_date(value: object, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _as_timestamp(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    raw = str(value)
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO timestamp") from error
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _sha256(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _bool(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise TypeError(f"{field} must be a boolean or a source 0/1 flag")


def _require_string(row: dict[str, Any], field: str, label: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{field} must be a nonempty string")
    return value


def _series_canonical_key(row: dict[str, Any]) -> str:
    """Keep identities source-scoped; dim_series is not limited to FRED."""
    source = _require_string(row, "source", "series_taxonomy").strip().casefold()
    series_id = _require_string(row, "series_id", "series_taxonomy")
    return f"macro:{source}:{series_id}"


def _release_identifier(value: object) -> str:
    """Canonicalize the source's numeric-or-text release identifier for storage."""
    if isinstance(value, bool) or value is None:
        raise ValueError("release_event.release_id must be a nonempty source identifier")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value:
        return value
    raise ValueError("release_event.release_id must be a nonempty source identifier")


def _manifest_identity(manifest: dict[str, Any]) -> str:
    return sha256(
        {
            "source": SOURCE_NAME,
            "source_object": SOURCE_OBJECT,
            "input_selection_sha256": manifest["input_selection_sha256"],
            "source_rows_sha256": manifest["source_rows_sha256"],
            "source_contract_verification": manifest["source_contract_verification"],
        }
    )


def validate_context_extract(extract: dict[str, Any]) -> None:
    """Reject incomplete, unverified, or historically over-claimed context input."""
    manifest = extract.get("manifest")
    taxonomy = extract.get("series_taxonomy")
    releases = extract.get("release_events")
    coverage = extract.get("source_coverage")
    if not isinstance(manifest, dict):
        raise TypeError("context extract requires a manifest object")
    if manifest.get("status") != ELIGIBLE_STATUS:
        raise ValueError("context extract is not an eligible source-contract extract")
    if manifest.get("redistribution_status") not in ALLOWED_REDISTRIBUTION_STATUSES:
        raise ValueError("context extract has an unsupported redistribution status")
    for field in ("input_selection_sha256", "source_rows_sha256"):
        _sha256(manifest.get(field), f"manifest.{field}")
    _as_timestamp(manifest.get("extracted_at"), "manifest.extracted_at")
    if manifest.get("series_taxonomy_temporal_status") != "current_only":
        raise ValueError("series taxonomy must remain explicitly current_only")
    coverage_temporal_status = manifest.get("coverage_temporal_status")
    if coverage_temporal_status == "not_selected" and coverage:
        raise ValueError("unselected source coverage must not contain records")
    if coverage_temporal_status not in {"current_only", "not_selected"}:
        raise ValueError("source coverage must be current_only or explicitly not_selected")
    release_temporal_status = manifest.get("release_event_temporal_status")
    if release_temporal_status == "not_selected" and releases:
        raise ValueError("unselected release events must not contain records")
    if release_temporal_status not in {"scheduled_date_with_source_fetched_at", "not_selected"}:
        raise ValueError("release events require scheduled-date temporal semantics")
    contract_gate = manifest.get("source_contract_verification")
    if not isinstance(contract_gate, dict) or contract_gate.get("status") != "valid":
        raise ValueError("context extract requires a valid source-contract verification")
    _sha256(
        contract_gate.get("catalog_fingerprint_sha256"),
        "source_contract_verification.catalog_fingerprint_sha256",
    )
    if not isinstance(contract_gate.get("registry_version"), str):
        raise ValueError("context extract requires a source-contract registry version")
    if not all(isinstance(rows, list) for rows in (taxonomy, releases, coverage)):
        raise TypeError("context extract records must be lists")
    if not taxonomy:
        raise ValueError("context extract requires taxonomy records")

    selection = {
        key: manifest.get(key)
        for key in (
            "source", "objects", "series_ids", "release_start", "release_end",
            "selection_scope", "page_size", "include_coverage",
        )
        if key in manifest
    }
    if sha256(selection) != manifest["input_selection_sha256"]:
        raise ValueError("context extract input selection hash does not match its manifest")
    if sha256(
        {
            "series_taxonomy": taxonomy,
            "release_events": releases,
            "source_coverage": coverage,
        }
    ) != manifest["source_rows_sha256"]:
        raise ValueError("context extract source rows hash does not match its manifest")

    seen_series: set[str] = set()
    for row in taxonomy:
        if not isinstance(row, dict):
            raise TypeError("series taxonomy record must be an object")
        series_id = _require_string(row, "series_id", "series_taxonomy")
        if series_id in seen_series:
            raise ValueError(f"context extract has duplicate taxonomy series_id: {series_id}")
        seen_series.add(series_id)

    seen_releases: set[tuple[str, date]] = set()
    for row in releases:
        if not isinstance(row, dict):
            raise TypeError("release event record must be an object")
        release_id = _release_identifier(row.get("release_id"))
        key = (release_id, _as_date(row.get("release_date"), "release_event.release_date"))
        if key in seen_releases:
            raise ValueError(f"context extract has duplicate release event: {release_id}")
        seen_releases.add(key)
        _bool(row.get("is_future"), "release_event.is_future")
        _as_timestamp(row.get("fetched_at"), "release_event.fetched_at")

    seen_coverage: set[tuple[str, str]] = set()
    for row in coverage:
        if not isinstance(row, dict):
            raise TypeError("source coverage record must be an object")
        source = _require_string(row, "source", "source_coverage")
        series_id = _require_string(row, "series_id", "source_coverage")
        key = (source, series_id)
        if key in seen_coverage:
            raise ValueError(f"context extract has duplicate source coverage: {source}:{series_id}")
        seen_coverage.add(key)
        _bool(row.get("is_stale"), "source_coverage.is_stale")
        if row.get("latest_observation_date") is not None:
            _as_date(row["latest_observation_date"], "source_coverage.latest_observation_date")


def load_context_extract(path: Path) -> dict[str, Any]:
    try:
        extract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load context extract at {path}: {error}") from error
    if not isinstance(extract, dict):
        raise TypeError("context extract root must be an object")
    validate_context_extract(extract)
    return extract


def _node_ids(cursor: Any, taxonomy: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resolve or create current-taxonomy identities without fabricating observations."""
    series_ids = set(taxonomy)
    canonical_keys = {
        _series_canonical_key(row)
        for row in taxonomy.values()
    }
    cursor.execute(
        """
        SELECT canonical_key, node_id
        FROM atlas.node
        WHERE node_type = 'macro_series'
          AND canonical_key = ANY(%s)
        """,
        (sorted(canonical_keys),),
    )
    existing_by_canonical = {
        canonical_key: node_id
        for canonical_key, node_id in cursor.fetchall()
    }
    node_ids = {
        series_id: existing_by_canonical[canonical_key]
        for series_id, row in taxonomy.items()
        if (canonical_key := _series_canonical_key(row)) in existing_by_canonical
    }
    missing = sorted(series_ids - set(node_ids))
    if missing:
        from psycopg.types.json import Jsonb

        for series_id in missing:
            row = taxonomy[series_id]
            canonical_key = _series_canonical_key(row)
            cursor.execute(
                """
                INSERT INTO atlas.node (
                    node_id, node_type, canonical_key, display_label, entity_status, provenance
                ) VALUES (%s, 'macro_series', %s, %s, 'active', %s)
                ON CONFLICT (node_type, canonical_key) DO UPDATE
                SET display_label = EXCLUDED.display_label,
                    provenance = EXCLUDED.provenance
                RETURNING node_id
                """,
                (
                    stable_id("node", canonical_key),
                    canonical_key,
                    row.get("title") or series_id,
                    Jsonb(
                        {
                            "source": SOURCE_NAME,
                            "source_object": "gold.dim_series",
                            "source_identifier": series_id,
                            "taxonomy_temporal_status": "current_only",
                        }
                    ),
                ),
            )
            node_ids[series_id] = cursor.fetchone()[0]
    return node_ids


def ingest_context_extract(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Write only dedicated current-context tables after full payload validation."""
    validate_context_extract(extract)
    manifest = extract["manifest"]
    manifest_sha256 = _manifest_identity(manifest)
    input_manifest_id = stable_id("macro-context-input-manifest", manifest_sha256)
    extracted_at = _as_timestamp(manifest["extracted_at"], "manifest.extracted_at")
    taxonomy = extract["series_taxonomy"]
    releases = extract["release_events"]
    coverage = extract["source_coverage"]
    taxonomy_by_id = {row["series_id"]: row for row in taxonomy}
    required_series = set(taxonomy_by_id) | {row["series_id"] for row in coverage}

    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO atlas.input_manifest (
                    input_manifest_id, source_name, source_object,
                    source_snapshot_reference, manifest_sha256, extracted_at,
                    redistribution_status, manifest
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_name, source_object, manifest_sha256) DO UPDATE
                SET manifest = EXCLUDED.manifest
                RETURNING input_manifest_id
                """,
                (
                    input_manifest_id,
                    SOURCE_NAME,
                    SOURCE_OBJECT,
                    manifest["source_rows_sha256"],
                    manifest_sha256,
                    extracted_at,
                    manifest["redistribution_status"],
                    Jsonb(manifest),
                ),
            )
            input_manifest_id = cursor.fetchone()[0]
            missing_taxonomy = sorted(required_series - set(taxonomy_by_id))
            if missing_taxonomy:
                raise ValueError(
                    "source coverage has series absent from the selected taxonomy: "
                    + ", ".join(missing_taxonomy)
                )
            node_ids = _node_ids(cursor, taxonomy_by_id)

            for row in taxonomy:
                series_id = row["series_id"]
                source_record = f"gold.dim_series:{series_id}"
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_series_taxonomy_current (
                        macro_series_taxonomy_id, series_node_id, series_id, title, source,
                        frequency, units, econ_category, polarity, default_transform, scale,
                        decimals, notes, geo, metric, input_manifest_id, source_record,
                        source_extracted_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s)
                    ON CONFLICT (series_node_id) DO UPDATE SET
                        series_id = EXCLUDED.series_id, title = EXCLUDED.title,
                        source = EXCLUDED.source, frequency = EXCLUDED.frequency,
                        units = EXCLUDED.units, econ_category = EXCLUDED.econ_category,
                        polarity = EXCLUDED.polarity,
                        default_transform = EXCLUDED.default_transform, scale = EXCLUDED.scale,
                        decimals = EXCLUDED.decimals, notes = EXCLUDED.notes, geo = EXCLUDED.geo,
                        metric = EXCLUDED.metric, input_manifest_id = EXCLUDED.input_manifest_id,
                        source_record = EXCLUDED.source_record,
                        source_extracted_at = EXCLUDED.source_extracted_at,
                        recorded_at = clock_timestamp()
                    """,
                    (
                        stable_id("macro-series-taxonomy", source_record), node_ids[series_id],
                        series_id, row.get("title"), row.get("source"), row.get("frequency"),
                        row.get("units"), row.get("econ_category"), row.get("polarity"),
                        row.get("default_transform"), row.get("scale"), row.get("decimals"),
                        row.get("notes"), row.get("geo"), row.get("metric"), input_manifest_id,
                        source_record, extracted_at,
                    ),
                )

            for row in releases:
                release_id = _release_identifier(row["release_id"])
                release_date = _as_date(row["release_date"], "release_event.release_date")
                source_record = f"gold.release_calendar:{release_id}:{release_date.isoformat()}"
                representative = row.get("representative_series_id")
                representative_node_id = node_ids.get(representative)
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_release_event_current (
                        macro_release_event_id, release_id, release_name, release_date,
                        importance, econ_category, representative_series_id,
                        representative_series_node_id, is_future, source_fetched_at,
                        input_manifest_id, source_record, source_extracted_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (release_id, release_date) DO UPDATE SET
                        release_name = EXCLUDED.release_name, importance = EXCLUDED.importance,
                        econ_category = EXCLUDED.econ_category,
                        representative_series_id = EXCLUDED.representative_series_id,
                        representative_series_node_id = EXCLUDED.representative_series_node_id,
                        is_future = EXCLUDED.is_future, source_fetched_at = EXCLUDED.source_fetched_at,
                        input_manifest_id = EXCLUDED.input_manifest_id,
                        source_record = EXCLUDED.source_record,
                        source_extracted_at = EXCLUDED.source_extracted_at,
                        recorded_at = clock_timestamp()
                    """,
                    (
                        stable_id("macro-release-event", source_record), release_id,
                        row.get("release_name"), release_date, row.get("importance"),
                        row.get("econ_category"), representative, representative_node_id,
                        _bool(row["is_future"], "release_event.is_future"),
                        _as_timestamp(row["fetched_at"], "release_event.fetched_at"),
                        input_manifest_id, source_record, extracted_at,
                    ),
                )

            for row in coverage:
                source, series_id = row["source"], row["series_id"]
                source_record = f"gold.v_source_coverage:{source}:{series_id}"
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_source_coverage_current (
                        macro_source_coverage_id, source, series_node_id, series_id, category,
                        frequency, latest_observation_date, observation_count, days_since_last,
                        is_stale, input_manifest_id, source_record, source_extracted_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, series_node_id) DO UPDATE SET
                        series_id = EXCLUDED.series_id, category = EXCLUDED.category,
                        frequency = EXCLUDED.frequency,
                        latest_observation_date = EXCLUDED.latest_observation_date,
                        observation_count = EXCLUDED.observation_count,
                        days_since_last = EXCLUDED.days_since_last,
                        is_stale = EXCLUDED.is_stale,
                        input_manifest_id = EXCLUDED.input_manifest_id,
                        source_record = EXCLUDED.source_record,
                        source_extracted_at = EXCLUDED.source_extracted_at,
                        recorded_at = clock_timestamp()
                    """,
                    (
                        stable_id("macro-source-coverage", source_record), source,
                        node_ids[series_id], series_id, row.get("category"),
                        row.get("frequency"),
                        _as_date(row["latest_observation_date"], "source_coverage.latest_observation_date")
                        if row.get("latest_observation_date") is not None else None,
                        row.get("observation_count"), row.get("days_since_last"),
                        _bool(row["is_stale"], "source_coverage.is_stale"),
                        input_manifest_id, source_record, extracted_at,
                    ),
                )
        return {
            "status": "macro_context_ingested_current_only",
            "input_manifest_id": str(input_manifest_id),
            "manifest_sha256": manifest_sha256,
            "series_taxonomy_count": len(taxonomy),
            "release_event_count": len(releases),
            "source_coverage_count": len(coverage),
        }
    except (ValueError, TypeError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001 - do not expose driver detail directly
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"macro context ingestion failed: {message}") from error


def _snapshot_summary(cursor: Any, snapshot_id: Any) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT snapshot_status, row_count, output_sha256, failure_reason
        FROM atlas.serving_snapshot WHERE serving_snapshot_id = %s
        """,
        (snapshot_id,),
    )
    status, row_count, output_sha256, failure_reason = cursor.fetchone()
    return {
        "snapshot_id": str(snapshot_id), "snapshot_status": status,
        "row_count": row_count, "output_sha256": output_sha256,
        "failure_reason": failure_reason,
    }


def _context_configuration(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "publication": PUBLICATION_NAME,
        "snapshot_contract": "macro-source-context-v1",
        "temporal_semantics": {
            "series_taxonomy": "current_only",
            "source_coverage": "current_only",
            "release_event": "scheduled_event",
        },
        "input_selection_sha256": manifest["input_selection_sha256"],
        "source_contract_catalog_fingerprint": manifest["source_contract_verification"][
            "catalog_fingerprint_sha256"
        ],
    }


def _materialize_snapshot(
    cursor: Any, snapshot_id: Any, build_run_id: Any, input_manifest_id: Any
) -> dict[str, int]:
    """Copy one immutable report surface from the current tables for this manifest."""
    statements = (
        (
            "series_taxonomy",
            """
            SELECT macro_series_taxonomy_id, series_node_id, source_record, temporal_status,
                   jsonb_build_object('series_id', series_id, 'title', title, 'source', source,
                     'frequency', frequency, 'units', units, 'econ_category', econ_category,
                     'polarity', polarity, 'default_transform', default_transform,
                     'scale', scale, 'decimals', decimals, 'notes', notes, 'geo', geo,
                     'metric', metric, 'source_extracted_at', source_extracted_at)
            FROM atlas.macro_series_taxonomy_current
            WHERE input_manifest_id = %s
            """,
        ),
        (
            "release_event",
            """
            SELECT macro_release_event_id, representative_series_node_id, source_record,
                   temporal_status, release_date,
                   jsonb_build_object('release_id', release_id, 'release_name', release_name,
                     'importance', importance, 'econ_category', econ_category,
                     'representative_series_id', representative_series_id, 'is_future', is_future,
                     'source_fetched_at', source_fetched_at, 'source_extracted_at', source_extracted_at)
            FROM atlas.macro_release_event_current
            WHERE input_manifest_id = %s
            """,
        ),
        (
            "source_coverage",
            """
            SELECT macro_source_coverage_id, series_node_id, source_record, temporal_status,
                   jsonb_build_object('source', source, 'series_id', series_id,
                     'category', category, 'frequency', frequency,
                     'latest_observation_date', latest_observation_date,
                     'observation_count', observation_count, 'days_since_last', days_since_last,
                     'is_stale', is_stale, 'source_extracted_at', source_extracted_at)
            FROM atlas.macro_source_coverage_current
            WHERE input_manifest_id = %s
            """,
        ),
    )
    from psycopg.types.json import Jsonb

    counts: dict[str, int] = {}
    for kind, query in statements:
        cursor.execute(query, (input_manifest_id,))
        rows = cursor.fetchall()
        for subject_id, series_node_id, source_record, temporal_status, *tail in rows:
            effective_date = tail[0] if kind == "release_event" else None
            details = tail[1] if kind == "release_event" else tail[0]
            cursor.execute(
                """
                INSERT INTO atlas_report.macro_source_context_snapshot (
                    serving_snapshot_id, context_kind, context_subject_id, series_node_id,
                    effective_date, temporal_status, input_manifest_id, source_record, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (snapshot_id, kind, subject_id, series_node_id, effective_date,
                 temporal_status, input_manifest_id, source_record, Jsonb(details)),
            )
            cursor.execute(
                """
                INSERT INTO atlas_report.provenance_snapshot (
                    serving_snapshot_id, provenance_kind, subject_id, build_run_id,
                    input_manifest_id, source_record, input_selection_sha256, details
                ) SELECT %s, 'macro_source_context', %s, %s, %s, %s,
                         manifest->>'input_selection_sha256', %s
                  FROM atlas.input_manifest WHERE input_manifest_id = %s
                ON CONFLICT DO NOTHING
                """,
                (snapshot_id, subject_id, build_run_id, input_manifest_id, source_record,
                 Jsonb(details), input_manifest_id),
            )
        counts[kind] = len(rows)
    return counts


def publish_context_snapshot(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Build, validate, and atomically publish an immutable macro-context snapshot."""
    validate_context_extract(extract)
    manifest = extract["manifest"]
    manifest_sha256 = _manifest_identity(manifest)
    input_manifest_id = stable_id("macro-context-input-manifest", manifest_sha256)
    configuration = _context_configuration(manifest)
    configuration_sha256 = sha256(configuration)
    code_revision = _code_revision()
    build_key = stable_id(
        "macro-context-build-key", f"{manifest_sha256}:{configuration_sha256}:{code_revision}"
    )
    build_run_id = stable_id("macro-context-build-run", str(build_key))
    snapshot_key = stable_id("macro-context-snapshot-key", str(build_key))
    snapshot_id = stable_id("macro-context-serving-snapshot", str(snapshot_key))
    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO atlas.build_run (
                    build_run_id, build_key, input_manifest_id, knowledge_cutoff,
                    configuration_sha256, configuration, code_revision, environment, run_status
                ) VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, 'building')
                ON CONFLICT (build_key) DO NOTHING
                """,
                (build_run_id, build_key, input_manifest_id, configuration_sha256,
                 Jsonb(configuration), code_revision, Jsonb({"python": platform.python_version()})),
            )
            cursor.execute(
                """
                INSERT INTO atlas.serving_snapshot (
                    serving_snapshot_id, snapshot_key, build_run_id, input_manifest_id,
                    knowledge_cutoff, snapshot_status
                ) VALUES (%s, %s, %s, %s, NULL, 'building')
                ON CONFLICT (snapshot_key) DO NOTHING
                """,
                (snapshot_id, snapshot_key, build_run_id, input_manifest_id),
            )
            existing = _snapshot_summary(cursor, snapshot_id)
            if existing["snapshot_status"] == "published":
                return {"status": "macro_context_snapshot_reused", **existing}

            counts = _materialize_snapshot(cursor, snapshot_id, build_run_id, input_manifest_id)
            if not all(counts.values()):
                raise ValueError("macro context snapshot requires taxonomy, release, and coverage rows")
            cursor.execute(
                """
                SELECT context_kind, context_subject_id::text, series_node_id::text,
                       effective_date::text, temporal_status, input_manifest_id::text,
                       source_record, details
                FROM atlas_report.macro_source_context_snapshot
                WHERE serving_snapshot_id = %s
                ORDER BY context_kind, context_subject_id
                """,
                (snapshot_id,),
            )
            payload = [list(row) for row in cursor.fetchall()]
            output_sha256 = sha256(payload)
            cursor.execute(
                """
                UPDATE atlas.serving_snapshot
                SET snapshot_status = 'validated', output_sha256 = %s, row_count = %s,
                    validation_summary = %s, validated_at = clock_timestamp()
                WHERE serving_snapshot_id = %s
                """,
                (output_sha256, len(payload), Jsonb({**counts, "output_sha256": output_sha256,
                                                     "input_manifest_id": str(input_manifest_id)}), snapshot_id),
            )
            cursor.execute(
                """UPDATE atlas.build_run SET run_status = 'validated', completed_at = clock_timestamp()
                   WHERE build_run_id = %s""",
                (build_run_id,),
            )
            cursor.execute("SELECT atlas.publish_serving_snapshot(%s, %s)", (PUBLICATION_NAME, snapshot_id))
            result = _snapshot_summary(cursor, snapshot_id)
        return {"status": "macro_context_snapshot_published", **result, **counts}
    except (ValueError, TypeError, DatabaseUnavailable):
        raise
    except Exception as error:  # noqa: BLE001
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"macro context publication failed: {message}") from error


def validate_context_publication(
    config: TargetDatabaseConfig, extract: dict[str, Any]
) -> dict[str, Any]:
    """Validate the report surface against the exact bounded extract grain."""
    validate_context_extract(extract)
    manifest_sha256 = _manifest_identity(extract["manifest"])
    input_manifest_id = stable_id("macro-context-input-manifest", manifest_sha256)
    expected = {
        "series_taxonomy": len(extract["series_taxonomy"]),
        "release_event": len(extract["release_events"]),
        "source_coverage": len(extract["source_coverage"]),
    }
    try:
        with _connect(config) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT context_kind, count(*), count(DISTINCT input_manifest_id),
                       bool_and(
                           (context_kind IN ('series_taxonomy', 'source_coverage')
                            AND temporal_status = 'current_only')
                           OR (context_kind = 'release_event'
                               AND temporal_status = 'scheduled_event')
                       )
                FROM atlas_report.current_macro_source_context
                GROUP BY context_kind
                ORDER BY context_kind
                """
            )
            rows = cursor.fetchall()
            actual = {kind: count for kind, count, _, _ in rows}
            manifest_counts_ok = all(manifest_count == 1 for _, _, manifest_count, _ in rows)
            temporal_status_ok = all(status_ok for _, _, _, status_ok in rows)
            cursor.execute(
                """
                SELECT count(*)
                FROM atlas_report.current_provenance
                WHERE provenance_kind = 'macro_source_context'
                  AND input_manifest_id = %s
                """,
                (input_manifest_id,),
            )
            provenance_count = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT snapshot.serving_snapshot_id::text, snapshot.output_sha256
                FROM atlas.publication AS publication
                JOIN atlas.serving_snapshot AS snapshot
                  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id
                WHERE publication.publication_name = %s
                """,
                (PUBLICATION_NAME,),
            )
            publication = cursor.fetchone()
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            cursor.execute("SELECT count(*) FROM atlas_report.current_macro_source_context")
            report_reader_row_count = cursor.fetchone()[0]
        expected_total = sum(expected.values())
        passed = (
            actual == expected
            and manifest_counts_ok
            and temporal_status_ok
            and provenance_count == expected_total
            and publication is not None
            and report_reader_row_count == expected_total
        )
        return {
            "status": "valid" if passed else "invalid",
            "expected_counts": expected,
            "actual_counts": actual,
            "provenance_count": provenance_count,
            "temporal_status_ok": temporal_status_ok,
            "single_manifest_per_kind": manifest_counts_ok,
            "published_snapshot_id": publication[0] if publication else None,
            "output_sha256": publication[1] if publication else None,
            "report_reader_row_count": report_reader_row_count,
        }
    except DatabaseUnavailable:
        raise
    except Exception as error:  # noqa: BLE001
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"macro context publication validation failed: {message}") from error
