import unittest

from market_atlas.adapters.macro_medallion import _validate_iso_date


class MacroMedallionAdapterTests(unittest.TestCase):
    def test_validates_iso_dates(self):
        self.assertEqual(
            "2024-01-02", _validate_iso_date("2024-01-02", "date").isoformat()
        )
        with self.assertRaisesRegex(ValueError, "date must be an ISO date"):
            _validate_iso_date("01/02/2024", "date")


if __name__ == "__main__":
    unittest.main()
