"""Conservative temporal predicates; date evidence never becomes a known instant."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from market_atlas.contracts import canonical_bytes
from market_atlas.securities_finance.contracts import TimestampEvidence, _require
from market_atlas.securities_finance.records import SourceRecord


@dataclass(frozen=True)
class Cutoffs:
    business_as_of: datetime
    knowledge_cutoff: datetime
    system_cutoff: datetime

    def __post_init__(self):
        for name in ("business_as_of", "knowledge_cutoff", "system_cutoff"):
            value = getattr(self, name)
            _require(
                isinstance(value, datetime) and value.utcoffset() is not None,
                "invalid_cutoff",
                "offset-aware instant required",
                name,
            )
            object.__setattr__(self, name, value.astimezone(UTC))

    @classmethod
    def from_mapping(cls, values):
        return cls(
            **{
                name: TimestampEvidence(value, "instant").as_utc()
                for name, value in values.items()
            }
        )


def evidence_bounds(value: TimestampEvidence | None):
    """Return (earliest, upper, exact); date upper bounds are exclusive."""
    if value is None:
        return None
    instant = value.as_utc()
    if instant is not None:
        return instant, instant, True
    if value.source_timezone is None:
        return None
    zone = ZoneInfo(value.source_timezone)
    try:
        day = datetime.fromisoformat(value.value).date()
        midnights = []
        for date in (day, day + timedelta(days=1)):
            local = datetime.combine(date, time())
            candidates = set()
            for fold in (0, 1):
                utc = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                if utc.astimezone(zone).replace(tzinfo=None) == local:
                    candidates.add(utc)
            if len(candidates) != 1:
                return None
            midnights.append(candidates.pop())
        if midnights[0] >= midnights[1]:
            return None
        return *midnights, False
    except (ValueError, OverflowError):
        return None


def at_or_before(value: TimestampEvidence | None, cutoff: datetime) -> bool | None:
    bounds = evidence_bounds(value)
    if bounds is None:
        return None
    low, high, exact = bounds
    if exact:
        return low <= cutoff
    if high <= cutoff:
        return True
    if low > cutoff:
        return False
    return None


def after(value: TimestampEvidence | None, cutoff: datetime) -> bool | None:
    result = at_or_before(value, cutoff)
    return None if result is None else not result


def compare(left: TimestampEvidence | None, right: TimestampEvidence | None):
    """-1/0/1 only when order/equality is proved; overlapping days are unknown."""
    a, b = evidence_bounds(left), evidence_bounds(right)
    if a is None or b is None:
        return None
    if a[2] and b[2] and a[0] == b[0]:
        return 0
    if a[1] < b[0] or (a[1] == b[0] and not a[2]):
        return -1
    if b[1] < a[0] or (b[1] == a[0] and not b[2]):
        return 1
    return None


@dataclass(frozen=True)
class Decision:
    record: SourceRecord
    status: str
    reasons: tuple[str, ...] = ()


def select_versions(records: tuple[SourceRecord, ...], cutoffs: Cutoffs):
    """Retain a decision for every version; never infer a winner from row order."""
    groups = defaultdict(list)
    decisions = []
    for row in records:
        env = row.envelope
        if env is None:
            decisions.append(Decision(row, "selected"))
            continue
        checks = {
            "business_start": at_or_before(
                env.effective_at
                if row.record_type == "lifecycle_event"
                else env.effective_from,
                cutoffs.business_as_of,
            ),
            "business_end": True
            if env.effective_to is None
            else after(env.effective_to, cutoffs.business_as_of),
            "source_availability": at_or_before(
                env.source_available_at, cutoffs.knowledge_cutoff
            ),
            "system_start": at_or_before(env.recorded_from, cutoffs.system_cutoff),
            "system_end": True
            if env.recorded_to is None
            else after(env.recorded_to, cutoffs.system_cutoff),
        }
        status = (
            "excluded"
            if False in checks.values()
            else "unknown"
            if None in checks.values()
            else "selected"
        )
        reasons = tuple(
            f"{name}_{'unknown' if result is None else 'outside_cutoff'}"
            for name, result in checks.items()
            if result is not True
        )
        groups[(env.key.source_name, env.key.record_type, env.key.record_id)].append(
            Decision(row, status, reasons)
        )
    for group in groups.values():
        candidates = [item for item in group if item.status == "selected"]
        uncertain = any(item.status == "unknown" for item in group)
        winner = candidates[0] if len(candidates) == 1 else None
        # Explicit event correction chains may establish one visible tip. A future
        # correction is excluded before this step and cannot suppress an old fact.
        if candidates and candidates[0].record.record_type == "lifecycle_event":
            by_version = {
                item.record.envelope.key.version_id: item for item in candidates
            }
            parents = {
                version: item.record.payload["supersedes_version_id"]
                for version, item in by_version.items()
            }
            tips = set(parents) - set(parents.values())
            if len(tips) == 1:
                tip = next(iter(tips))
                visited, cursor = set(), tip
                while cursor in parents and cursor not in visited:
                    visited.add(cursor)
                    cursor = parents[cursor]
                winner = (
                    by_version[tip]
                    if visited == set(parents) and cursor not in visited
                    else None
                )
            else:
                winner = None
        for item in group:
            if item.status == "selected" and (uncertain or winner is None):
                item = Decision(item.record, "unknown", ("ambiguous_active_versions",))
            elif item.status == "selected" and item is not winner:
                item = Decision(item.record, "excluded", ("superseded_event_version",))
            decisions.append(item)
    return tuple(
        sorted(
            decisions,
            key=lambda item: (
                item.record.record_type,
                item.record.source_name,
                canonical_bytes(item.record.to_row(semantic=True)),
            ),
        )
    )
