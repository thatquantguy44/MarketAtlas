import unittest
from datetime import UTC, date, datetime, timedelta

from market_atlas.analytics.rolling_correlation import (
    MINIMUM_PAIRED_RETURN_COUNT,
    MarketPoint,
    compute_rolling_correlations,
)


class RollingCorrelationTests(unittest.TestCase):
    def setUp(self):
        self.sessions = [
            date(2024, 1, 2) + timedelta(days=index) for index in range(60)
        ]

    def _points(self, right_constant: bool = False) -> list[MarketPoint]:
        points: list[MarketPoint] = []
        for index, session in enumerate(self.sessions):
            for instrument, value in (
                ("instrument-a", 100.0 + index),
                ("instrument-b", 50.0 if right_constant else 50.0 + index * 0.5),
            ):
                points.append(
                    MarketPoint(
                        instrument_id=instrument,
                        session_date=session,
                        value=value,
                        unit="USD",
                        calendar_name="test-calendar",
                        adjustment_basis="test-adjustment",
                        available_at=datetime(2024, 1, 2, 22, tzinfo=UTC),
                        source_record=f"{instrument}-{index}",
                        selection_status="supported",
                    )
                )
        return points

    def test_calculates_canonical_fixed_window_estimate(self):
        estimate = compute_rolling_correlations(
            self.sessions, self._points(), [("instrument-b", "instrument-a")]
        )[0]
        self.assertEqual("instrument-a", estimate.instrument_low_id)
        self.assertEqual("instrument-b", estimate.instrument_high_id)
        self.assertEqual(59, estimate.paired_return_count)
        self.assertEqual("supported", estimate.estimate_status)
        self.assertIsNotNone(estimate.correlation)

    def test_returns_explicit_undefined_statuses(self):
        zero_variance = compute_rolling_correlations(
            self.sessions,
            self._points(right_constant=True),
            [("instrument-a", "instrument-b")],
        )[0]
        self.assertEqual("zero_variance", zero_variance.estimate_status)

        insufficient_points = self._points()
        insufficient_points = [
            point
            for point in insufficient_points
            if not (
                point.instrument_id == "instrument-b" and point.session_date.day % 2
            )
        ]
        insufficient = compute_rolling_correlations(
            self.sessions, insufficient_points, [("instrument-a", "instrument-b")]
        )[0]
        self.assertLess(insufficient.paired_return_count, MINIMUM_PAIRED_RETURN_COUNT)
        self.assertEqual("insufficient_sample", insufficient.estimate_status)

        unsupported_points = self._points()
        unsupported_points[0] = MarketPoint(
            **{
                **unsupported_points[0].__dict__,
                "selection_status": "unsupported_adjusted_history",
            }
        )
        unsupported = compute_rolling_correlations(
            self.sessions, unsupported_points, [("instrument-a", "instrument-b")]
        )[0]
        self.assertEqual("unsupported_history", unsupported.estimate_status)


if __name__ == "__main__":
    unittest.main()
