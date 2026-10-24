"""Portable fixture contract checks; these do not validate a live adapter."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

ALLOWED_EDGES = {
    ("lists", "listing", "instrument"),
    ("issued_by", "instrument", "issuer"),
    ("classified_as", "issuer", "sector"),
    ("member_of", "issuer", "index"),
    ("listed_in", "listing", "country"),
    ("denominated_in", "instrument", "currency"),
    ("measures", "macro_series", "economic_concept"),
    ("covers", "macro_series", "country"),
    ("context_for", "sector", "macro_series"),
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be a UTC ISO-8601 string ending in Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _day(value: str) -> date:
    return date.fromisoformat(value)


def validate_fixture(data: dict) -> list[str]:
    """Return all known contract violations without relying on assertions."""
    errors: list[str] = []
    if data.get("metadata", {}).get("synthetic") is not True:
        errors.append("fixture must be labeled synthetic")
    if data.get("metadata", {}).get("license") != "generated-synthetic":
        errors.append("fixture license label is missing or unexpected")

    entities = data.get("entities", [])
    for key in ("entities", "identifiers", "assertions", "market_observations", "macro_observations", "configured_pairs"):
        if not data.get(key):
            errors.append(f"fixture requires nonempty {key}")
    ids = [item.get("id") for item in entities]
    if len(ids) != len(set(ids)) or None in ids:
        errors.append("entity IDs must be present and unique")
    types = {item["id"]: item.get("type") for item in entities if item.get("id")}

    sessions = data.get("sessions", [])
    try:
        parsed_sessions = [_day(value) for value in sessions]
        if len(sessions) < 61 or parsed_sessions != sorted(set(parsed_sessions)):
            errors.append("sessions must include at least 61 unique sorted days")
    except (TypeError, ValueError):
        errors.append("sessions contain an invalid date")
    session_set = set(sessions)

    identifier_keys: set[tuple] = set()
    for index, row in enumerate(data.get("identifiers", [])):
        label = f"identifier[{index}]"
        if row.get("entity_id") not in types:
            errors.append(f"{label}: unknown entity")
        try:
            start = _day(row["valid_from"])
            end = _day(row["valid_to"]) if row.get("valid_to") else None
            if end is not None and end <= start:
                errors.append(f"{label}: invalid effective interval")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid effective date")
        key = (row.get("source"), row.get("scheme"), row.get("value"), row.get("valid_from"))
        if key in identifier_keys:
            errors.append(f"{label}: duplicate source identifier interval start")
        identifier_keys.add(key)

    assertion_ids: set[str] = set()
    for index, row in enumerate(data.get("assertions", [])):
        label = f"assertion[{index}]"
        if row.get("id") in assertion_ids or not row.get("id"):
            errors.append(f"{label}: missing or duplicate ID")
        assertion_ids.add(row.get("id"))
        source_type = types.get(row.get("source_id"))
        target_type = types.get(row.get("target_id"))
        if (row.get("predicate"), source_type, target_type) not in ALLOWED_EDGES:
            errors.append(f"{label}: invalid predicate or endpoint types")
        if row.get("kind") not in ("reference", "curated_context"):
            errors.append(f"{label}: invalid relationship kind")
        if row.get("predicate") == "context_for" and (row.get("kind") != "curated_context" or not row.get("rationale")):
            errors.append(f"{label}: macro context requires a curated rationale")
        if row.get("status") not in ("accepted", "disputed", "retracted"):
            errors.append(f"{label}: invalid relationship status")
        if not row.get("provenance"):
            errors.append(f"{label}: missing provenance")
        try:
            start = _day(row["valid_from"])
            end = _day(row["valid_to"]) if row.get("valid_to") else None
            if end is not None and end <= start:
                errors.append(f"{label}: invalid effective interval")
            _timestamp(row["available_at"])
            _timestamp(row["recorded_at"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid temporal fields")

    seen_prices: set[tuple] = set()
    for index, row in enumerate(data.get("market_observations", [])):
        label = f"market_observation[{index}]"
        if types.get(row.get("instrument_id")) != "instrument":
            errors.append(f"{label}: unknown instrument")
        key = (row.get("instrument_id"), row.get("session"), row.get("measure"))
        if key in seen_prices:
            errors.append(f"{label}: duplicate observation key")
        seen_prices.add(key)
        if row.get("session") not in session_set or row.get("measure") != "adjusted_close":
            errors.append(f"{label}: invalid session or measure")
        if not isinstance(row.get("value"), (float, int)) or row["value"] <= 0:
            errors.append(f"{label}: price must be positive")
        if not row.get("unit") or not row.get("adjustment") or not row.get("source_record"):
            errors.append(f"{label}: missing measure metadata")
        try:
            _timestamp(row["available_at"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid availability")

    seen_macro: set[tuple] = set()
    for index, row in enumerate(data.get("macro_observations", [])):
        label = f"macro_observation[{index}]"
        if types.get(row.get("series_id")) != "macro_series":
            errors.append(f"{label}: unknown series")
        key = (row.get("series_id"), row.get("period"), row.get("vintage"))
        if key in seen_macro:
            errors.append(f"{label}: duplicate vintage key")
        seen_macro.add(key)
        if not all(row.get(field) for field in ("unit", "frequency", "source_record")):
            errors.append(f"{label}: missing measure metadata")
        try:
            _timestamp(row["available_at"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid availability")

    seen_pairs: set[tuple] = set()
    for index, pair in enumerate(data.get("configured_pairs", [])):
        if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1] or any(types.get(item) != "instrument" for item in pair):
            errors.append(f"configured_pair[{index}]: invalid instruments")
            continue
        key = tuple(sorted(pair))
        if key in seen_pairs:
            errors.append(f"configured_pair[{index}]: duplicate undirected pair")
        seen_pairs.add(key)
    return errors


def available_view(data: dict, cutoff: str) -> dict:
    """Select fixture assertions and macro vintages available by a UTC cutoff.

    This is a source-availability view only. A historical system-record replay
    requires the versioned PostgreSQL graph planned in T-006.
    """
    cutoff_time = _timestamp(cutoff)
    assertions = [row for row in data["assertions"] if _timestamp(row["available_at"]) <= cutoff_time]
    macro: dict[tuple[str, str], dict] = {}
    for row in data["macro_observations"]:
        if _timestamp(row["available_at"]) > cutoff_time:
            continue
        key = (row["series_id"], row["period"])
        if key not in macro or row["available_at"] > macro[key]["available_at"]:
            macro[key] = row
    return {
        "knowledge_cutoff": cutoff,
        "assertion_ids": sorted(row["id"] for row in assertions),
        "macro_vintages": sorted(
            [{"series_id": series, "period": period, "vintage": row["vintage"], "value": row["value"]}
             for (series, period), row in macro.items()],
            key=lambda row: (row["series_id"], row["period"]),
        ),
        "synthetic": True,
        "status": "fixture_availability_only; no_business_or_system_replay",
    }
