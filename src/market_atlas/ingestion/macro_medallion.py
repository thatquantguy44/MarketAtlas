"""Idempotent ingestion of the verified MacroMedallion/EcoMedallion extract."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid5

from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable

UPSTREAM_NAMESPACE = UUID("9de3d55e-5ae9-4e50-9d12-87651e46690b")
SOURCE_NAME = "macro_medallion_ecomedallion"
SOURCE_OBJECT = "meta.fred_series,gold.fred_point_in_time"
ALLOWED_REDISTRIBUTION_STATUSES = {
    "synthetic",
    "approved",
    "unresolved",
    "restricted",
}


def stable_id(record_type: str, source_id: str) -> UUID:
    """Return stable IDs isolated from the synthetic-fixture namespace."""
    return uuid5(UPSTREAM_NAMESPACE, f"{record_type}:{source_id}")


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
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    raw = str(value)
    if len(raw) == 10:
        raw = f"{raw}T00:00:00+00:00"
    elif raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO timestamp or date") from error
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _require_sha256(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def validate_extract(extract: dict[str, Any]) -> None:
    """Validate the adapter payload before any MarketAtlas write transaction begins."""
    manifest = extract.get("manifest")
    entities = extract.get("entities")
    observations = extract.get("macro_observations")
    if not isinstance(manifest, dict):
        raise TypeError("extract requires a manifest object")
    if (
        manifest.get("status")
        != "source_contract_extracted; not_loaded_to_marketatlas_graph"
    ):
        raise ValueError("extract manifest is not an eligible source-contract extract")
    if manifest.get("redistribution_status") not in ALLOWED_REDISTRIBUTION_STATUSES:
        raise ValueError("extract manifest has an unsupported redistribution status")
    _require_sha256(manifest.get("input_selection_sha256"), "input_selection_sha256")
    _require_sha256(manifest.get("source_rows_sha256"), "source_rows_sha256")
    _as_timestamp(manifest.get("extracted_at"), "manifest.extracted_at")
    if not isinstance(entities, list) or not entities:
        raise ValueError("extract requires at least one macro-series entity")
    if not isinstance(observations, list):
        raise TypeError("extract macro_observations must be a list")

    canonical_keys: set[str] = set()
    entity_by_key: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            raise TypeError("extract entity must be an object")
        canonical_key = entity.get("canonical_key")
        if (
            not isinstance(canonical_key, str)
            or not canonical_key.startswith("macro:fred:")
            or entity.get("type") != "macro_series"
        ):
            raise ValueError("extract entity must be a FRED macro_series canonical key")
        if canonical_key in canonical_keys:
            raise ValueError(f"extract has duplicate canonical key: {canonical_key}")
        required = ("label", "frequency", "unit", "source_identifier")
        if any(
            not isinstance(entity.get(field), str) or not entity[field]
            for field in required
        ):
            raise ValueError(f"extract entity {canonical_key} has incomplete metadata")
        canonical_keys.add(canonical_key)
        entity_by_key[canonical_key] = entity

    source_records: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise TypeError("extract macro observation must be an object")
        canonical_key = observation.get("series_canonical_key")
        if canonical_key not in entity_by_key:
            raise ValueError("extract observation references an unknown macro series")
        source_record = observation.get("source_record")
        if not isinstance(source_record, str) or not source_record:
            raise ValueError("extract macro observation requires source_record")
        if source_record in source_records:
            raise ValueError(f"extract has duplicate source_record: {source_record}")
        source_records.add(source_record)
        _as_date(observation.get("reference_period"), "reference_period")
        _as_date(observation.get("available_on"), "available_on")
        _as_date(
            observation.get("source_valid_through_inclusive"),
            "source_valid_through_inclusive",
        )
        _as_timestamp(observation.get("source_ingested_at"), "source_ingested_at")
        if observation.get("availability_precision") != "date":
            raise TypeError(
                "extract macro observation must have date availability precision"
            )
        if not isinstance(observation.get("revision_number"), int):
            raise TypeError(
                "extract macro observation requires integer revision_number"
            )
        is_missing = observation.get("is_missing")
        if not isinstance(is_missing, bool):
            raise TypeError("extract macro observation requires boolean is_missing")
        if is_missing and observation.get("value") is not None:
            raise ValueError("missing macro observation must not carry a value")
        if not is_missing and observation.get("value") is None:
            raise ValueError("present macro observation requires a value")


def _connect(config: TargetDatabaseConfig) -> Any:
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error
    connection = psycopg.connect(**config.connection_kwargs())
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(config.role)))
    return connection


def _manifest_identity(manifest: dict[str, Any]) -> str:
    return sha256(
        {
            "source": SOURCE_NAME,
            "source_object": SOURCE_OBJECT,
            "input_selection_sha256": manifest["input_selection_sha256"],
            "source_rows_sha256": manifest["source_rows_sha256"],
        }
    )


def ingest(config: TargetDatabaseConfig, extract: dict[str, Any]) -> dict[str, object]:
    """Write a validated upstream extract only to MarketAtlas-owned schemas."""
    validate_extract(extract)
    manifest = extract["manifest"]
    manifest_sha256 = _manifest_identity(manifest)
    input_manifest_id = stable_id("input-manifest", manifest_sha256)
    extracted_at = _as_timestamp(manifest["extracted_at"], "manifest.extracted_at")
    entity_by_key = {entity["canonical_key"]: entity for entity in extract["entities"]}
    node_ids: dict[str, UUID] = {}

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
                ON CONFLICT (source_name, source_object, manifest_sha256) DO NOTHING
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
            created_manifest = cursor.fetchone() is not None

            for canonical_key, entity in entity_by_key.items():
                node_id = stable_id("node", canonical_key)
                cursor.execute(
                    """
                    INSERT INTO atlas.node (
                        node_id, node_type, canonical_key, display_label,
                        entity_status, provenance
                    ) VALUES (%s, 'macro_series', %s, %s, %s, %s)
                    ON CONFLICT (node_type, canonical_key) DO UPDATE
                    SET display_label = EXCLUDED.display_label,
                        entity_status = EXCLUDED.entity_status,
                        provenance = EXCLUDED.provenance
                    RETURNING node_id
                    """,
                    (
                        node_id,
                        canonical_key,
                        entity["label"],
                        "active" if entity["active"] else "inactive",
                        Jsonb(
                            {
                                "source": SOURCE_NAME,
                                "source_identifier": entity["source_identifier"],
                                "category": entity["category"],
                                "frequency": entity["frequency"],
                                "unit": entity["unit"],
                                "vintage_enabled": entity["vintage_enabled"],
                                "load_type": entity["load_type"],
                                "source_metadata_updated_at": str(
                                    entity["source_metadata_updated_at"]
                                ),
                            }
                        ),
                    ),
                )
                node_ids[canonical_key] = cursor.fetchone()[0]

            inserted_observations = 0
            for observation in extract["macro_observations"]:
                source_record = observation["source_record"]
                vintage = (
                    f"{observation['available_on']}#{observation['revision_number']}"
                )
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_observation_version (
                        macro_observation_version_id, series_node_id,
                        reference_period, reference_period_label, frequency, value,
                        unit, is_missing, vintage, source_valid_through_inclusive,
                        available_at, availability_status, source_ingested_at,
                        source_record, input_manifest_id, recorded_from
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, 'known', %s, %s, %s, %s
                    )
                    ON CONFLICT (macro_observation_version_id) DO NOTHING
                    """,
                    (
                        stable_id("macro-observation-version", source_record),
                        node_ids[observation["series_canonical_key"]],
                        _as_date(observation["reference_period"], "reference_period"),
                        str(observation["reference_period"]),
                        entity_by_key[observation["series_canonical_key"]]["frequency"],
                        observation["value"],
                        entity_by_key[observation["series_canonical_key"]]["unit"],
                        observation["is_missing"],
                        vintage,
                        _as_date(
                            observation["source_valid_through_inclusive"],
                            "source_valid_through_inclusive",
                        ),
                        _as_timestamp(observation["available_on"], "available_on"),
                        _as_timestamp(
                            observation["source_ingested_at"], "source_ingested_at"
                        ),
                        source_record,
                        input_manifest_id,
                        extracted_at,
                    ),
                )
                inserted_observations += cursor.rowcount

        return {
            "status": "macro_medallion_ecomedallion_ingested",
            "input_manifest_id": str(input_manifest_id),
            "manifest_created": created_manifest,
            "manifest_sha256": manifest_sha256,
            "source_rows_sha256": manifest["source_rows_sha256"],
            "macro_series_count": len(node_ids),
            "macro_observation_inserted_count": inserted_observations,
            "macro_observation_seen_count": len(extract["macro_observations"]),
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"MacroMedallion/EcoMedallion ingestion failed: {message}"
        ) from error
