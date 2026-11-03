"""Conservative temporal predicates; date evidence never becomes a known instant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from market_atlas.securities_finance.contracts import TimestampEvidence, _require


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
