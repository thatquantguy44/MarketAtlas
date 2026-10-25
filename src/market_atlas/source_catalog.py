"""Build a safe, metadata-only support catalog for source relations."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .contracts import sha256

CATALOG_VERSION = "source-catalog-v1"
MARKETATLAS_SCHEMAS = {"atlas", "atlas_report"}
SUPPORTED_OBJECTS = {
    "meta.fred_series": {
        "support_state": "supported_live",
        "purpose": "macro-series identity and metadata",
        "declared_grain": "one row per series_id",
        "business_key": ["series_id"],
        "data_classification": "restricted_pending_rights",
        "adapter": "macro_medallion_ecomedallion",
    },
    "gold.fred_point_in_time": {
        "support_state": "supported_live",
        "purpose": "point-in-time macro observation versions",
        "declared_grain": "one row per series_id, observation_date, realtime_start",
        "business_key": ["series_id", "observation_date", "realtime_start"],
        "data_classification": "restricted_pending_rights",
        "adapter": "macro_medallion_ecomedallion",
    },
}


def _object_key(row: dict[str, Any]) -> str:
    return f"{row['schema_name']}.{row['object_name']}"


def build_source_catalog(inspection: dict[str, Any]) -> dict[str, Any]:
    """Classify every inspected relation without reading source data or definitions."""
    columns_by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for column in inspection["columns"]:
        columns_by_object[_object_key(column)].append(
            {
                "ordinal_position": column["ordinal_position"],
                "column_name": column["column_name"],
                "data_type": column["data_type"],
                "udt_name": column["udt_name"],
                "is_nullable": column["is_nullable"],
            }
        )

    indexes_by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index in inspection.get("indexes", []):
        indexes_by_object[_object_key(index)].append(
            {
                "index_name": index["index_name"],
                "is_primary": index["is_primary"],
                "is_unique": index["is_unique"],
                "key_columns": index["key_columns"],
            }
        )

    definitions_by_object = {
        _object_key(definition): definition["definition_md5"]
        for definition in inspection.get("view_definitions", [])
    }

    entries: list[dict[str, Any]] = []
    for object_row in inspection["objects"]:
        key = _object_key(object_row)
        catalog_entry = {
            "schema_name": object_row["schema_name"],
            "object_name": object_row["object_name"],
            "object_type": object_row["object_type"],
            "estimated_rows": object_row["estimated_rows"],
            "can_select": object_row["can_select"],
            "can_write": object_row["can_write"],
            "read_probe_status": object_row.get("read_probe_status", "not_run"),
            "columns": columns_by_object[key],
            "column_fingerprint_sha256": sha256(columns_by_object[key]),
            "key_indexes": indexes_by_object[key],
            "view_definition_md5": definitions_by_object.get(key),
        }
        if object_row["schema_name"] in MARKETATLAS_SCHEMAS:
            catalog_entry.update(
                {
                    "support_state": "marketatlas_owned",
                    "purpose": "MarketAtlas-owned serving or graph storage",
                    "declared_grain": "not an upstream source contract",
                    "business_key": [],
                    "data_classification": "marketatlas_internal",
                    "adapter": None,
                }
            )
        elif key in SUPPORTED_OBJECTS:
            catalog_entry.update(SUPPORTED_OBJECTS[key])
        elif object_row["can_select"]:
            catalog_entry.update(
                {
                    "support_state": "discovered_not_onboarded",
                    "purpose": "unclassified; requires owner and grain review",
                    "declared_grain": "unclassified",
                    "business_key": [],
                    "data_classification": "unclassified",
                    "adapter": None,
                }
            )
        else:
            catalog_entry.update(
                {
                    "support_state": "unavailable_to_source_role",
                    "purpose": "not approved for MarketAtlas source access",
                    "declared_grain": "unclassified",
                    "business_key": [],
                    "data_classification": "unclassified",
                    "adapter": None,
                }
            )
        entries.append(catalog_entry)

    entries.sort(key=lambda entry: (entry["schema_name"], entry["object_name"]))
    support_counts = dict(
        sorted(Counter(entry["support_state"] for entry in entries).items())
    )
    source_entries = [
        entry for entry in entries if entry["support_state"] != "marketatlas_owned"
    ]
    fingerprint_payload = {
        "catalog_version": CATALOG_VERSION,
        "server": {
            "database": inspection["server"]["database"],
            "server_version": inspection["server"]["server_version"],
        },
        "objects": entries,
    }
    return {
        "status": "cataloged_read_only",
        "catalog_version": CATALOG_VERSION,
        "upstream_asset": "MacroMedallion/EcoMedallion",
        "server": inspection["server"],
        "source_object_count": len(source_entries),
        "marketatlas_object_count": len(entries) - len(source_entries),
        "support_counts": support_counts,
        "catalog_fingerprint_sha256": sha256(fingerprint_payload),
        "objects": entries,
    }
