"""Fixed-window, no-forward-fill rolling return correlations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from itertools import pairwise
from math import sqrt

from market_atlas.contracts import sha256

WINDOW_SESSION_COUNT = 60
MINIMUM_PAIRED_RETURN_COUNT = 45
METHOD_VERSION = "rolling-pearson-simple-return-v1"
CONFIGURATION = {
    "calendar_alignment": "declared_common_session_grid",
    "minimum_paired_return_count": MINIMUM_PAIRED_RETURN_COUNT,
    "missing_data_policy": "no_forward_fill_no_window_expansion",
    "return_definition": "simple_adjusted_close_return",
    "window_session_count": WINDOW_SESSION_COUNT,
}
CONFIGURATION_SHA256 = sha256(CONFIGURATION)


@dataclass(frozen=True)
class MarketPoint:
    instrument_id: str
    session_date: date
    value: float
    unit: str
    calendar_name: str
    adjustment_basis: str
    available_at: datetime | None
    source_record: str
    selection_status: str


@dataclass(frozen=True)
class RollingCorrelationEstimate:
    instrument_low_id: str
    instrument_high_id: str
    endpoint_session_date: date
    window_start_session_date: date
    paired_return_count: int
    correlation: float | None
    estimate_status: str
    adjustment_basis: str
    max_input_available_at: datetime | None
    input_selection_sha256: str


def _is_supported(point: MarketPoint) -> bool:
    return point.selection_status in {"supported", "current_context"}


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_deviation = [value - left_mean for value in left]
    right_deviation = [value - right_mean for value in right]
    left_sum_squares = sum(value * value for value in left_deviation)
    right_sum_squares = sum(value * value for value in right_deviation)
    if left_sum_squares == 0 or right_sum_squares == 0:
        return None
    value = sum(
        left_value * right_value
        for left_value, right_value in zip(left_deviation, right_deviation, strict=True)
    ) / sqrt(left_sum_squares * right_sum_squares)
    return max(-1.0, min(1.0, value))


def compute_rolling_correlations(
    sessions: Iterable[date],
    points: Iterable[MarketPoint],
    configured_pairs: Iterable[tuple[str, str]],
) -> list[RollingCorrelationEstimate]:
    """Calculate only complete fixed session windows without filling missing prices."""
    ordered_sessions = list(sessions)
    if ordered_sessions != sorted(set(ordered_sessions)):
        raise ValueError("sessions must be unique and sorted")
    if len(ordered_sessions) < WINDOW_SESSION_COUNT:
        return []

    points_by_instrument: dict[str, dict[date, list[MarketPoint]]] = {}
    for point in points:
        points_by_instrument.setdefault(point.instrument_id, {}).setdefault(
            point.session_date, []
        ).append(point)

    estimates: list[RollingCorrelationEstimate] = []
    for raw_left, raw_right in configured_pairs:
        if raw_left == raw_right:
            raise ValueError("configured pair cannot contain the same instrument twice")
        low_id, high_id = sorted((raw_left, raw_right))
        for endpoint_index in range(WINDOW_SESSION_COUNT - 1, len(ordered_sessions)):
            window = ordered_sessions[
                endpoint_index - WINDOW_SESSION_COUNT + 1 : endpoint_index + 1
            ]
            left_by_session = points_by_instrument.get(low_id, {})
            right_by_session = points_by_instrument.get(high_id, {})
            all_points = [
                point
                for session in window
                for point in (
                    *left_by_session.get(session, []),
                    *right_by_session.get(session, []),
                )
            ]
            selection_payload = [
                {
                    "instrument_id": point.instrument_id,
                    "session_date": point.session_date.isoformat(),
                    "value": point.value,
                    "unit": point.unit,
                    "calendar_name": point.calendar_name,
                    "adjustment_basis": point.adjustment_basis,
                    "available_at": point.available_at.isoformat()
                    if point.available_at
                    else None,
                    "source_record": point.source_record,
                    "selection_status": point.selection_status,
                }
                for point in sorted(
                    all_points,
                    key=lambda point: (
                        point.instrument_id,
                        point.session_date,
                        point.source_record,
                    ),
                )
            ]
            input_selection_sha256 = sha256(selection_payload)
            supported_points = [point for point in all_points if _is_supported(point)]
            max_available_at = max(
                (
                    point.available_at
                    for point in supported_points
                    if point.available_at
                ),
                default=None,
            )
            adjustment_values = sorted(
                {point.adjustment_basis for point in supported_points}
            )
            adjustment_basis = (
                adjustment_values[0]
                if len(adjustment_values) == 1
                else "incompatible_adjustment_basis"
            )

            if any(not _is_supported(point) for point in all_points):
                status, correlation, sample_count = "unsupported_history", None, 0
            elif (
                any(
                    len(by_session.get(session, [])) > 1
                    for by_session in (left_by_session, right_by_session)
                    for session in window
                )
                or len({point.unit for point in supported_points}) > 1
                or len({point.calendar_name for point in supported_points}) > 1
                or len(adjustment_values) > 1
            ):
                status, correlation, sample_count = "incompatible_input", None, 0
            else:
                left_returns: dict[date, float] = {}
                right_returns: dict[date, float] = {}
                for prior_session, session in pairwise(window):
                    left_prior = left_by_session.get(prior_session, [])
                    left_current = left_by_session.get(session, [])
                    right_prior = right_by_session.get(prior_session, [])
                    right_current = right_by_session.get(session, [])
                    if len(left_prior) == len(left_current) == 1:
                        left_returns[session] = (
                            left_current[0].value / left_prior[0].value - 1
                        )
                    if len(right_prior) == len(right_current) == 1:
                        right_returns[session] = (
                            right_current[0].value / right_prior[0].value - 1
                        )
                paired_sessions = sorted(set(left_returns) & set(right_returns))
                sample_count = len(paired_sessions)
                left_values = [left_returns[session] for session in paired_sessions]
                right_values = [right_returns[session] for session in paired_sessions]
                if sample_count < MINIMUM_PAIRED_RETURN_COUNT:
                    status, correlation = "insufficient_sample", None
                else:
                    correlation = _correlation(left_values, right_values)
                    status = "supported" if correlation is not None else "zero_variance"

            estimates.append(
                RollingCorrelationEstimate(
                    instrument_low_id=low_id,
                    instrument_high_id=high_id,
                    endpoint_session_date=window[-1],
                    window_start_session_date=window[0],
                    paired_return_count=sample_count,
                    correlation=correlation,
                    estimate_status=status,
                    adjustment_basis=adjustment_basis,
                    max_input_available_at=max_available_at,
                    input_selection_sha256=input_selection_sha256,
                )
            )
    return estimates
