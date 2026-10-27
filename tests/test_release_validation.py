import unittest

from market_atlas.validation.release import summarize_timing


class ReleaseValidationTests(unittest.TestCase):
    def test_uses_nearest_rank_p95_for_twenty_prepared_query_samples(self):
        result = summarize_timing([value / 100 for value in range(1, 21)], 2.0)

        self.assertEqual(result["sample_count"], 20)
        self.assertEqual(result["p95_seconds"], 0.19)
        self.assertTrue(result["target_met"])

    def test_rejects_insufficient_performance_samples(self):
        with self.assertRaisesRegex(ValueError, "at least 20"):
            summarize_timing([0.01] * 19, 2.0)

    def test_reports_a_missed_target_without_hiding_the_measurement(self):
        result = summarize_timing([0.01] * 18 + [2.01, 2.01], 2.0)

        self.assertEqual(result["p95_seconds"], 2.01)
        self.assertFalse(result["target_met"])


if __name__ == "__main__":
    unittest.main()
