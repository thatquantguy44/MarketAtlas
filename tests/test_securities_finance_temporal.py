import unittest
from datetime import UTC, datetime, timedelta

from market_atlas.securities_finance.contracts import ContractError, TimestampEvidence
from market_atlas.securities_finance.temporal import (
    Cutoffs,
    after,
    at_or_before,
    compare,
    evidence_bounds,
)


class TemporalTests(unittest.TestCase):
    def test_exact_offsets_and_cutoffs(self):
        point = TimestampEvidence("2026-11-03T07:00:00-05:00", "instant")
        noon = datetime(2026, 11, 3, 12, tzinfo=UTC)
        self.assertTrue(at_or_before(point, noon))
        self.assertFalse(after(point, noon))
        self.assertFalse(at_or_before(point, noon - timedelta(microseconds=1)))
        self.assertEqual(
            0, compare(point, TimestampEvidence(noon.isoformat(), "instant"))
        )
        self.assertEqual(noon, Cutoffs(noon, noon, noon).business_as_of)
        with self.assertRaises(ContractError):
            Cutoffs(noon.replace(tzinfo=None), noon, noon)

    def test_day_boundaries_are_conservative(self):
        day = TimestampEvidence("2026-11-03", "date", "UTC")
        start = datetime(2026, 11, 3, tzinfo=UTC)
        end = start + timedelta(days=1)
        self.assertIsNone(at_or_before(day, start))
        self.assertIsNone(after(day, start))
        self.assertFalse(at_or_before(day, start - timedelta(microseconds=1)))
        self.assertTrue(at_or_before(day, end))
        self.assertIsNone(compare(day, day))
        self.assertEqual(
            -1, compare(day, TimestampEvidence(end.isoformat(), "instant"))
        )
        self.assertEqual(1, compare(TimestampEvidence(end.isoformat(), "instant"), day))

    def test_timezone_days_follow_dst(self):
        spring = evidence_bounds(
            TimestampEvidence("2026-03-08", "date", "America/New_York")
        )
        fall = evidence_bounds(
            TimestampEvidence("2026-11-01", "date", "America/New_York")
        )
        self.assertEqual(timedelta(hours=23), spring[1] - spring[0])
        self.assertEqual(timedelta(hours=25), fall[1] - fall[0])

    def test_missing_or_unsupported_day_is_unknown(self):
        for value in (
            None,
            TimestampEvidence("2026-11-03", "date"),
            TimestampEvidence("9999-12-31", "date", "UTC"),
            TimestampEvidence("2011-12-30", "date", "Pacific/Apia"),
        ):
            with self.subTest(value=value):
                self.assertIsNone(evidence_bounds(value))
                self.assertIsNone(
                    at_or_before(value, datetime(2026, 11, 3, tzinfo=UTC))
                )


if __name__ == "__main__":
    unittest.main()
