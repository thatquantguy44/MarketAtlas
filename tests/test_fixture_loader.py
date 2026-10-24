import unittest
from uuid import UUID

from market_atlas.fixtures import build_fixture
from market_atlas.graph.fixture_loader import _reference_period_date, stable_id


class FixtureLoaderTests(unittest.TestCase):
    def test_stable_ids_are_deterministic_and_type_scoped(self):
        first = stable_id("node", "I-A")
        self.assertIsInstance(first, UUID)
        self.assertEqual(first, stable_id("node", "I-A"))
        self.assertNotEqual(first, stable_id("identifier", "I-A"))

    def test_fixture_has_late_capture_and_reference_retraction(self):
        assertions = {row["id"]: row for row in build_fixture()["assertions"]}
        self.assertGreater(
            assertions["A14"]["recorded_at"], assertions["A14"]["available_at"]
        )
        self.assertEqual("A6", assertions["A15"]["supersedes_id"])
        self.assertEqual("retracted", assertions["A15"]["status"])

    def test_normalizes_monthly_macro_periods(self):
        self.assertEqual("2024-01-01", _reference_period_date("2024-01").isoformat())
        self.assertEqual("2024-01-15", _reference_period_date("2024-01-15").isoformat())


if __name__ == "__main__":
    unittest.main()
