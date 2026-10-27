"""Versioned declarations and verification for approved upstream source objects."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_CONTRACTS_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "source_contracts.toml"
)
REGISTRY_VERSION = "source-contract-registry-v1"
LIFECYCLE_STATES = frozenset({"proposed", "reviewed", "supported_live", "retired"})
OBJECT_TYPES = frozenset(
    {"table", "partitioned_table", "view", "materialized_view", "foreign_table"}
)
REQUIRED_CONTRACT_FIELDS = (
    "schema_name",
    "object_name",
    "object_type",
    "lifecycle_state",
    "owner",
    "source_owner_status",
    "purpose",
    "declared_grain",
    "business_key",
    "required_columns",
    "expected_column_fingerprint_sha256",
    "data_classification",
    "redistribution_status",
    "temporal_semantics",
    "adapter",
)


class SourceContractError(ValueError):
    """Raised when a tracked source-contract registry is malformed."""


def object_key(contract: dict[str, Any]) -> str:
    return f"{contract['schema_name']}.{contract['object_name']}"


def _nonempty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceContractError(f"{field} must be a nonempty string")
    return value


def _text_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise SourceContractError(f"{field} must be a nonempty string array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SourceContractError(f"{field} must contain only nonempty strings")
    if len(value) != len(set(value)):
        raise SourceContractError(f"{field} must not contain duplicates")
    return list(value)


def _sha256(value: object, field: str) -> str:
    text = _nonempty_text(value, field)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise SourceContractError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _md5(value: object, field: str) -> str:
    text = _nonempty_text(value, field)
    if len(text) != 32 or any(character not in "0123456789abcdef" for character in text):
        raise SourceContractError(f"{field} must be a lowercase MD5 digest")
    return text


def _validate_contract(raw_contract: object, position: int) -> dict[str, Any]:
    if not isinstance(raw_contract, dict):
        raise SourceContractError(f"contracts[{position}] must be a table")
    missing = [field for field in REQUIRED_CONTRACT_FIELDS if field not in raw_contract]
    if missing:
        raise SourceContractError(
            f"contracts[{position}] is missing required fields: {', '.join(missing)}"
        )
    contract = {
        field: raw_contract[field]
        for field in REQUIRED_CONTRACT_FIELDS
    }
    for field in (
        "schema_name",
        "object_name",
        "owner",
        "source_owner_status",
        "purpose",
        "declared_grain",
        "data_classification",
        "redistribution_status",
        "temporal_semantics",
        "adapter",
    ):
        contract[field] = _nonempty_text(contract[field], f"contracts[{position}].{field}")
    contract["object_type"] = _nonempty_text(
        contract["object_type"], f"contracts[{position}].object_type"
    )
    if contract["object_type"] not in OBJECT_TYPES:
        raise SourceContractError(
            f"contracts[{position}].object_type is not a supported PostgreSQL relation type"
        )
    contract["lifecycle_state"] = _nonempty_text(
        contract["lifecycle_state"], f"contracts[{position}].lifecycle_state"
    )
    if contract["lifecycle_state"] not in LIFECYCLE_STATES:
        raise SourceContractError(
            f"contracts[{position}].lifecycle_state must be one of: "
            f"{', '.join(sorted(LIFECYCLE_STATES))}"
        )
    contract["business_key"] = _text_list(
        contract["business_key"], f"contracts[{position}].business_key"
    )
    contract["required_columns"] = _text_list(
        contract["required_columns"], f"contracts[{position}].required_columns"
    )
    if not set(contract["business_key"]).issubset(contract["required_columns"]):
        raise SourceContractError(
            f"contracts[{position}].business_key must be included in required_columns"
        )
    contract["expected_column_fingerprint_sha256"] = _sha256(
        contract["expected_column_fingerprint_sha256"],
        f"contracts[{position}].expected_column_fingerprint_sha256",
    )
    expected_view_definition = raw_contract.get("expected_view_definition_md5")
    if contract["object_type"] in {"view", "materialized_view"}:
        contract["expected_view_definition_md5"] = _md5(
            expected_view_definition,
            f"contracts[{position}].expected_view_definition_md5",
        )
    elif expected_view_definition is not None:
        raise SourceContractError(
            f"contracts[{position}].expected_view_definition_md5 is only valid for views"
        )
    return contract


def load_source_contract_registry(
    path: Path = DEFAULT_SOURCE_CONTRACTS_PATH,
) -> dict[str, Any]:
    """Load the tracked, non-secret registry of declared source contracts."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SourceContractError(
            f"cannot read source-contract registry at {path}: {error}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise SourceContractError(
            f"invalid source-contract registry at {path}: {error}"
        ) from error
    if document.get("registry_version") != REGISTRY_VERSION:
        raise SourceContractError(
            f"source-contract registry must declare {REGISTRY_VERSION}"
        )
    raw_contracts = document.get("contracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        raise SourceContractError("source-contract registry requires at least one contract")
    contracts = [
        _validate_contract(raw_contract, position)
        for position, raw_contract in enumerate(raw_contracts)
    ]
    keys = [object_key(contract) for contract in contracts]
    if len(keys) != len(set(keys)):
        raise SourceContractError("source-contract registry must not repeat an object")
    contracts.sort(key=object_key)
    return {"registry_version": REGISTRY_VERSION, "contracts": contracts}


def contracts_by_object(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a validated registry by qualified source object name."""
    return {object_key(contract): contract for contract in registry["contracts"]}


def catalog_metadata(contract: dict[str, Any]) -> dict[str, Any]:
    """Expose contract metadata without making non-live objects ingestible."""
    lifecycle_state = contract["lifecycle_state"]
    return {
        "support_state": (
            "supported_live"
            if lifecycle_state == "supported_live"
            else "discovered_not_onboarded"
        ),
        "contract_state": lifecycle_state,
        "owner": contract["owner"],
        "source_owner_status": contract["source_owner_status"],
        "purpose": contract["purpose"],
        "declared_grain": contract["declared_grain"],
        "business_key": contract["business_key"],
        "required_columns": contract["required_columns"],
        "expected_column_fingerprint_sha256": contract[
            "expected_column_fingerprint_sha256"
        ],
        "data_classification": contract["data_classification"],
        "redistribution_status": contract["redistribution_status"],
        "temporal_semantics": contract["temporal_semantics"],
        "adapter": contract["adapter"],
    }


def verify_source_contracts(
    catalog: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify declared source contracts against one metadata-only catalog result."""
    registry = registry or load_source_contract_registry()
    catalog_objects = catalog.get("objects")
    if not isinstance(catalog_objects, list):
        raise SourceContractError("catalog requires an objects array")
    objects = {
        f"{item.get('schema_name')}.{item.get('object_name')}": item
        for item in catalog_objects
        if isinstance(item, dict)
    }
    errors: list[str] = []
    checked_objects: list[str] = []
    for contract in registry["contracts"]:
        key = object_key(contract)
        checked_objects.append(key)
        item = objects.get(key)
        if item is None:
            errors.append(f"{key}: object is absent from catalog")
            continue
        if item.get("object_type") != contract["object_type"]:
            errors.append(f"{key}: object type differs from contract")
        if item.get("can_select") is not True:
            errors.append(f"{key}: source reader lacks SELECT access")
        if item.get("can_write") is not False:
            errors.append(f"{key}: source reader has source-write access")
        if item.get("read_probe_status") != "passed":
            errors.append(f"{key}: zero-row read probe did not pass")
        if (
            item.get("column_fingerprint_sha256")
            != contract["expected_column_fingerprint_sha256"]
        ):
            errors.append(f"{key}: column fingerprint differs from contract")
        actual_columns = {
            column.get("column_name")
            for column in item.get("columns", [])
            if isinstance(column, dict)
        }
        missing_columns = sorted(set(contract["required_columns"]) - actual_columns)
        if missing_columns:
            errors.append(
                f"{key}: required columns are absent: {', '.join(missing_columns)}"
            )
        if contract["object_type"] in {"view", "materialized_view"} and (
            item.get("view_definition_md5")
            != contract["expected_view_definition_md5"]
        ):
            errors.append(f"{key}: view definition fingerprint differs from contract")
        if contract["lifecycle_state"] == "supported_live" and (
            item.get("support_state") not in {None, "supported_live"}
        ):
            errors.append(f"{key}: catalog does not classify the object as supported_live")
    return {
        "status": "valid" if not errors else "invalid",
        "registry_version": registry["registry_version"],
        "catalog_version": catalog.get("catalog_version"),
        "catalog_fingerprint_sha256": catalog.get("catalog_fingerprint_sha256"),
        "contract_count": len(registry["contracts"]),
        "supported_live_count": sum(
            contract["lifecycle_state"] == "supported_live"
            for contract in registry["contracts"]
        ),
        "checked_objects": checked_objects,
        "errors": errors,
    }
