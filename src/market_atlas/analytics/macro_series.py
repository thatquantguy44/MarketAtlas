"""Explicit macro transformations and source-vintage-aware research panels."""

from __future__ import annotations

import calendar
import math
import re
import statistics
import tomllib
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from market_atlas.contracts import sha256

METHOD_VERSION = "macro-comparable-series-v1"
MAX_PANELS = 10000
MAX_CELLS = 2000000


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("dates must be YYYY-MM-DD strings")
    return date.fromisoformat(value)


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError(f"{label} has missing or unknown settings")


def validate_settings(settings, as_of):
    _keys(
        settings,
        "version observation_start output_start max_rows redistribution_status groups",
        "macro analytics",
    )
    cutoff, start, output = map(
        _day, (as_of, settings["observation_start"], settings["output_start"])
    )
    if not start <= output <= cutoff or (cutoff - start).days > 366 * 25:
        raise ValueError("analytics dates must be ordered within a 25-year bound")
    if not isinstance(settings["version"], str) or not settings["version"]:
        raise ValueError("settings version is required")
    if settings["redistribution_status"] not in {"restricted", "synthetic"}:
        raise ValueError("analytics outputs must be restricted or synthetic")
    if type(settings["max_rows"]) is not int or not 1 <= settings["max_rows"] <= 250000:
        raise ValueError("max_rows must be between 1 and 250000")
    groups = settings["groups"]
    if not isinstance(groups, list) or not 1 <= len(groups) <= 10:
        raise ValueError("one to ten explicit groups are required")
    seen_groups, seen_series, pairs, panels, cells = set(), set(), 0, 0, 0
    for group in groups:
        _keys(
            group,
            "id frequency window minimum_pairs baseline minimum_baseline change_lag_evaluations members",
            "group",
        )
        if (
            not isinstance(group["id"], str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", group["id"])
            or group["id"] in seen_groups
        ):
            raise ValueError("group IDs must be unique safe identifiers")
        seen_groups.add(group["id"])
        if group["frequency"] not in {"m", "d"}:
            raise ValueError("only explicit monthly or daily groups are supported")
        for key in (
            "window",
            "minimum_pairs",
            "baseline",
            "minimum_baseline",
            "change_lag_evaluations",
        ):
            if type(group[key]) is not int or not 1 <= group[key] <= 252:
                raise ValueError("group sample settings must be bounded integers")
        if (
            not 3 <= group["minimum_pairs"] <= group["window"]
            or not 3 <= group["minimum_baseline"] <= group["baseline"]
        ):
            raise ValueError(
                "sample minima must be at least three and within their windows"
            )
        members = group["members"]
        if not isinstance(members, list) or not 2 <= len(members) <= 10:
            raise ValueError("each group must have two to ten explicit members")
        for member in members:
            _keys(member, "series_id unit transform orientation", "member")
            sid = member["series_id"]
            if (
                not isinstance(sid, str)
                or not re.fullmatch(r"[A-Za-z0-9_]{1,64}", sid)
                or sid in seen_series
            ):
                raise ValueError(
                    "series IDs must be unique across the research universe"
                )
            seen_series.add(sid)
            if not isinstance(member["unit"], str) or not member["unit"].strip():
                raise ValueError("expected units are required")
            if member["transform"] not in {"difference", "log_change"}:
                raise ValueError("unsupported macro transformation")
            if type(member["orientation"]) is not int or member["orientation"] not in {
                -1,
                1,
            }:
                raise ValueError("orientation must be +1 or -1")
        count = len(_knowledge_dates(output, cutoff, group["frequency"]))
        panels += count
        cells += count * len(members) * (group["window"] + group["baseline"] + 1)
        pairs += len(members) * (len(members) - 1) // 2
    if len(seen_series) > 50 or pairs > 100 or panels > MAX_PANELS or cells > MAX_CELLS:
        raise ValueError("analytics selection exceeds series/pair/panel/cell bounds")
    return settings


def load_settings(path: Path, as_of: str):
    return validate_settings(tomllib.loads(path.read_text(encoding="utf-8")), as_of)


def _previous(period, frequency):
    if frequency == "m":
        return (period.replace(day=1) - timedelta(days=1)).replace(day=1)
    previous = period - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    return previous


def _knowledge_dates(start, end, frequency):
    result = []
    current = start
    while current <= end:
        if frequency == "d":
            if current.weekday() < 5:
                result.append(current)
            current += timedelta(days=1)
        else:
            last = current.replace(
                day=calendar.monthrange(current.year, current.month)[1]
            )
            if last > end:
                result.append(end)
                break
            result.append(last)
            current = last + timedelta(days=1)
    return result


def _capture_index(capture, settings, as_of):
    entities, rows, manifest = (
        capture[key] for key in ("entities", "macro_observations", "manifest")
    )
    captured_at = datetime.fromisoformat(manifest["extracted_at"])
    if (
        captured_at.tzinfo is None
        or manifest.get("series_metadata_context") != "current_not_point_in_time"
    ):
        raise ValueError(
            "capture requires a timezone-aware record time and current metadata label"
        )
    if (
        not isinstance(entities, list)
        or not isinstance(rows, list)
        or len(rows) > settings["max_rows"]
    ):
        raise ValueError(
            "source capture exceeds configured bounds or has invalid lists"
        )
    if manifest["source_rows_sha256"] != sha256(
        {"entities": entities, "macro_observations": rows}
    ):
        raise ValueError("source capture hash mismatch")
    fields = [
        "source",
        "objects",
        "series_ids",
        "observation_start",
        "observation_end",
        "knowledge_cutoff",
    ]
    if manifest["input_selection_sha256"] != sha256(
        {key: manifest[key] for key in fields}
    ):
        raise ValueError("source selection hash mismatch")
    ids = {
        member["series_id"]
        for group in settings["groups"]
        for member in group["members"]
    }
    if (
        set(manifest["series_ids"]) != ids
        or len(manifest["series_ids"]) != len(ids)
        or manifest["source"] != "macro_medallion_postgresql"
        or manifest["objects"] != ["meta.fred_series", "gold.fred_point_in_time"]
        or manifest["observation_start"] != settings["observation_start"]
        or manifest["observation_end"] != as_of
        or manifest["knowledge_cutoff"] != as_of
        or manifest["redistribution_status"] != settings["redistribution_status"]
    ):
        raise ValueError("source capture selection differs from analytics settings")
    metadata = {}
    for entity in entities:
        sid = entity["source_identifier"]
        if (
            sid not in ids
            or sid in metadata
            or entity["canonical_key"] != f"macro:fred:{sid}"
            or entity["type"] != "macro_series"
        ):
            raise ValueError("source capture contains invalid series identities")
        metadata[sid] = entity
    index = {sid: defaultdict(list) for sid in ids}
    source_records = set()
    for row in rows:
        sid = row["series_canonical_key"].removeprefix("macro:fred:")
        if sid not in ids or row["series_canonical_key"] != f"macro:fred:{sid}":
            raise ValueError("source observation is outside the declared universe")
        period = _day(row["reference_period"])
        if not _day(settings["observation_start"]) <= period <= _day(as_of):
            raise ValueError("source observation is outside capture bounds")
        record = row["source_record"]
        if not isinstance(record, str) or not record or record in source_records:
            raise ValueError("source records must be nonempty and unique")
        source_records.add(record)
        try:
            available = _day(row["available_on"])
            through = _day(row["source_valid_through_inclusive"])
            status = (
                "supported" if period <= available <= through else "invalid_vintage"
            )
        except (ValueError, TypeError):
            available = through = None
            status = (
                "unknown_vintage"
                if not row.get("available_on")
                and not row.get("source_valid_through_inclusive")
                else "invalid_vintage"
            )
        index[sid][period].append(
            {**row, "start": available, "end": through, "vintage_status": status}
        )
    return metadata, index


def _select(versions, knowledge_date):
    if not versions:
        return {
            "value": None,
            "status": "absent_period",
            "source_records": [],
            "available_on": None,
        }
    invalid = [v for v in versions if v["vintage_status"] != "supported"]
    candidates = [
        v
        for v in versions
        if v["start"] is not None and v["start"] <= knowledge_date <= v["end"]
    ]
    status = (
        invalid[0]["vintage_status"]
        if invalid
        else "ambiguous_vintage"
        if len(candidates) > 1
        else "not_available_at_cutoff"
        if not candidates
        else "supported"
    )
    if status != "supported":
        return {
            "value": None,
            "status": status,
            "source_records": [],
            "available_on": None,
        }
    row = candidates[0]
    try:
        value = float(row["value"]) if row["value"] is not None else None
    except (TypeError, ValueError, OverflowError):
        value = None
    if (
        isinstance(row["value"], bool)
        or type(row["is_missing"]) is not bool
        or (row["is_missing"] and row["value"] is not None)
    ):
        status = "invalid_value_state"
    elif row["is_missing"]:
        status = "source_missing"
    elif value is None or not math.isfinite(value):
        status = "invalid_value_state"
    return {
        "value": value if status == "supported" else None,
        "status": status,
        "source_records": [row["source_record"]],
        "available_on": row["start"].isoformat(),
    }


def _transform(previous, current, member, period):
    status = (
        current["status"] if current["status"] != "supported" else previous["status"]
    )
    value = None
    if status == "supported":
        left, right = previous["value"], current["value"]
        if member["transform"] == "log_change" and (left <= 0 or right <= 0):
            status = "nonpositive_log_input"
        else:
            # Log subtraction avoids overflow/underflow in the ratio.
            value = (
                (math.log(right) - math.log(left)) * 100
                if member["transform"] == "log_change"
                else right - left
            ) * member["orientation"]
            if not math.isfinite(value):
                status, value = "nonfinite_transformation", None
    dates = [v["available_on"] for v in (previous, current) if v["available_on"]]
    return {
        "reference_period": period.isoformat(),
        "value": value,
        "status": status,
        "available_on": max(dates, default=None),
        "source_records": sorted(
            set(previous["source_records"] + current["source_records"])
        ),
    }


def prepare_series(capture, settings, as_of):
    """Reconstruct each panel at its own source-date cutoff, never capture time."""
    validate_settings(settings, as_of)
    metadata, index = _capture_index(capture, settings, as_of)
    panels, eligibility = [], []
    for group in settings["groups"]:
        statuses = {}
        for member in group["members"]:
            sid = member["series_id"]
            entity = metadata.get(sid, {})
            status = (
                "supported"
                if entity.get("active") is True
                and entity.get("frequency") == group["frequency"]
                and entity.get("unit") == member["unit"]
                else "metadata_mismatch"
            )
            statuses[sid] = status
            raw = [v for versions in index[sid].values() for v in versions]
            usable = [
                period
                for period, versions in index[sid].items()
                if _select(versions, _day(as_of))["status"] == "supported"
                and (
                    period.day == 1
                    if group["frequency"] == "m"
                    else period.weekday() < 5
                )
            ]
            eligibility.append(
                {
                    "group_id": group["id"],
                    **member,
                    "frequency": group["frequency"],
                    "status": status,
                    "raw_version_count": len(raw),
                    "unknown_vintage_count": sum(
                        v["vintage_status"] == "unknown_vintage" for v in raw
                    ),
                    "invalid_vintage_count": sum(
                        v["vintage_status"] == "invalid_vintage" for v in raw
                    ),
                    "usable_period_count_as_of": len(usable)
                    if status == "supported"
                    else 0,
                    "earliest_usable_period_as_of": min(usable).isoformat()
                    if usable and status == "supported"
                    else None,
                    "observed_frequency": entity.get("frequency"),
                    "observed_unit": entity.get("unit"),
                }
            )
        for knowledge_date in _knowledge_dates(
            _day(settings["output_start"]), _day(as_of), group["frequency"]
        ):
            frequency = group["frequency"]
            anchor = (
                knowledge_date.replace(day=1) if frequency == "m" else knowledge_date
            )
            reference_end = _previous(anchor, frequency)
            grid = [reference_end]
            for _ in range(group["window"] + group["baseline"]):
                grid.append(_previous(grid[-1], frequency))
            grid.reverse()
            members, lineage = [], {}
            for member in group["members"]:
                sid = member["series_id"]
                selected = [
                    _select(index[sid].get(period, []), knowledge_date)
                    for period in grid
                ]
                if statuses[sid] != "supported":
                    selected = [
                        {
                            "value": None,
                            "status": statuses[sid],
                            "source_records": [],
                            "available_on": None,
                        }
                        for _ in grid
                    ]
                for period, item in zip(grid, selected, strict=True):
                    lineage[f"{sid}:{period}"] = item
                transformed = [
                    _transform(left, right, member, period)
                    for left, right, period in zip(selected, selected[1:], grid[1:])
                ]
                points = transformed[-group["window"] :]
                baseline = transformed[-group["baseline"] - 1 : -1]
                values = [p["value"] for p in baseline if p["status"] == "supported"]
                mean = statistics.mean(values) if values else None
                sd = statistics.stdev(values) if len(values) > 1 else None
                latest = points[-1]
                zstatus = (
                    latest["status"]
                    if latest["status"] != "supported"
                    else "insufficient_baseline"
                    if len(values) < group["minimum_baseline"]
                    else "zero_baseline_variance"
                    if sd == 0
                    else "supported"
                )
                zscore = (
                    (latest["value"] - mean) / sd if zstatus == "supported" else None
                )
                if zscore is not None and not math.isfinite(zscore):
                    zscore, zstatus = None, "nonfinite_standardization"
                members.append(
                    {
                        "series_id": sid,
                        "points": points,
                        "usable_change_count": sum(
                            p["status"] == "supported" for p in points
                        ),
                        "point_status_counts": dict(
                            sorted(Counter(p["status"] for p in points).items())
                        ),
                        "baseline_count": len(values),
                        "baseline_mean": mean,
                        "baseline_sd": sd,
                        "baseline_input_sha256": sha256(baseline),
                        "zscore": zscore,
                        "zscore_status": zstatus,
                    }
                )
            used = [value for value in lineage.values() if value["source_records"]]
            panels.append(
                {
                    "group_id": group["id"],
                    "knowledge_date": knowledge_date.isoformat(),
                    "reference_start": points[0]["reference_period"],
                    "reference_end": reference_end.isoformat(),
                    "members": members,
                    "input_sha256": sha256(lineage),
                    "source_records": sorted(
                        {record for v in used for record in v["source_records"]}
                    ),
                    "max_input_available_on": max(
                        (v["available_on"] for v in used), default=None
                    ),
                }
            )
    payload = {
        "method_version": METHOD_VERSION,
        "as_of": as_of,
        "settings": settings,
        "settings_sha256": sha256(settings),
        "capture": capture,
        "availability_precision": "date_end_of_day",
        "metadata_scope": "current_metadata_fixed_operator_universe_not_historical_taxonomy",
        "historical_scope": "source_history_reconstructed_at_capture_not_marketatlas_record_time_replay",
        "eligibility": eligibility,
        "panels": panels,
    }
    return {**payload, "prepared_sha256": sha256(payload)}


def capture_and_prepare(database, settings, as_of):
    """Use only the existing approved, read-only PostgreSQL source interfaces."""
    from market_atlas.adapters.macro_medallion import _read_only_connection, extract
    from market_atlas.config import MacroMedallionConfig

    validate_settings(settings, as_of)
    ids = sorted(
        member["series_id"]
        for group in settings["groups"]
        for member in group["members"]
    )
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT series_id FROM gold.dim_series WHERE source = 'fred' AND series_id = ANY(%s) LIMIT 51",
            (ids,),
        )
        if {row[0] for row in cursor.fetchall()} != set(ids):
            raise ValueError(
                "analytics universe contains series outside the approved FRED catalog"
            )
    pilot = MacroMedallionConfig(
        tuple(ids),
        settings["observation_start"],
        as_of,
        as_of,
        settings["redistribution_status"],
    )
    capture = extract(database, pilot, max_rows=settings["max_rows"])
    return prepare_series(capture, settings, as_of)


def verify_prepared(prepared):
    """Check both the envelope hash and all derived preparation against raw inputs."""
    payload = {
        key: value for key, value in prepared.items() if key != "prepared_sha256"
    }
    if prepared.get("prepared_sha256") != sha256(payload):
        raise ValueError("prepared input hash mismatch")
    rebuilt = prepare_series(
        prepared["capture"], prepared["settings"], prepared["as_of"]
    )
    if rebuilt != prepared:
        raise ValueError("prepared input differs from reconstructed source evidence")
    return prepared
