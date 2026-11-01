import copy
import unittest

from test_macro_analytics_series import capture, settings

from market_atlas.analytics.macro_relationships import (
    calculate_relationships,
    panel_estimates,
)
from market_atlas.analytics.macro_series import prepare_series


def numeric_panel():
    return {
        "group_id": "test",
        "knowledge_date": "2024-06-30",
        "reference_start": "2024-03-01",
        "reference_end": "2024-05-01",
        "input_sha256": "a" * 64,
        "max_input_available_on": "2024-06-01",
        "members": [
            {
                "series_id": sid,
                "points": [
                    {
                        "reference_period": f"2024-{i + 3:02d}-01",
                        "value": x,
                        "status": "supported",
                    }
                    for i, x in enumerate(values)
                ],
                "zscore": z,
                "zscore_status": "supported",
                "baseline_count": 3,
                "baseline_input_sha256": "b" * 64,
            }
            for sid, values, z in (
                ("A", [1, 2, 3], 2),
                ("B", [1, 3, 2], 0),
                ("C", [3, 2, 1], -2),
            )
        ],
    }


class MacroRelationshipTests(unittest.TestCase):
    def test_independent_closed_form_correlation_distance_and_dispersion(self):
        pairs, group, nodes = panel_estimates(numeric_panel(), settings()["groups"][0])
        estimates = {(p["series_low_id"], p["series_high_id"]): p for p in pairs}
        # For A=(1,2,3), B=(1,3,2): centered dot=1, both squared norms=2.
        self.assertAlmostEqual(0.5, estimates["A", "B"]["correlation"])
        self.assertAlmostEqual(1, estimates["A", "B"]["distance"])
        self.assertAlmostEqual(-1, estimates["A", "C"]["correlation"])
        self.assertAlmostEqual(2, estimates["A", "C"]["distance"])
        # z=(2,0,-2), mean=0, sample SD=sqrt((4+0+4)/2)=2.
        self.assertEqual(0, group["group_mean_zscore"])
        self.assertEqual(2, group["dispersion"])
        self.assertEqual(2, nodes[0]["deviation_from_group_mean"])
        self.assertAlmostEqual(1.5, nodes[0]["mean_peer_distance"])
        self.assertTrue(all(p["paired_count"] == 3 for p in pairs))

    def test_incomplete_sample_constant_series_and_missing_group_member(self):
        panel = numeric_panel()
        panel["members"][0]["points"][0].update(value=None, status="source_missing")
        panel["members"][0].update(zscore=None, zscore_status="insufficient_baseline")
        for p in panel["members"][2]["points"]:
            p["value"] = 1
        pairs, group, nodes = panel_estimates(panel, settings()["groups"][0])
        self.assertEqual("insufficient_sample", pairs[0]["estimate_status"])
        self.assertEqual("zero_variance", pairs[-1]["estimate_status"])
        self.assertTrue(all(p["correlation"] is None for p in pairs))
        self.assertEqual("incomplete_group", group["estimate_status"])
        self.assertEqual(2, group["usable_member_count"])
        self.assertIsNone(group["dispersion"])
        self.assertTrue(all(n["mean_peer_distance"] is None for n in nodes))
        self.assertTrue(all(n["deviation_from_group_mean"] is None for n in nodes))

    def test_pair_canonicalization_and_grid_mismatch_rejection(self):
        panel = numeric_panel()
        panel["members"].reverse()
        pairs, _, _ = panel_estimates(panel, settings()["groups"][0])
        self.assertEqual(
            ("A", "B"), (pairs[0]["series_low_id"], pairs[0]["series_high_id"])
        )
        panel["members"][0]["points"][0]["reference_period"] = "2024-02-01"
        with self.assertRaisesRegex(ValueError, "grid"):
            panel_estimates(panel, settings()["groups"][0])

    def test_finite_large_values_do_not_turn_overflow_into_zero_correlation(self):
        panel = numeric_panel()
        for member in panel["members"]:
            for point, value in zip(
                member["points"], [-1e308, 1e308, -1e308], strict=True
            ):
                point["value"] = value
        pairs, _, _ = panel_estimates(panel, settings()["groups"][0])
        self.assertTrue(all(abs(row["correlation"] - 1) < 1e-12 for row in pairs))

    def test_exact_prior_evaluation_is_not_replaced_by_nearest_supported(self):
        config = settings()
        data = capture(
            config,
            [f"2023-{m:02d}-01" for m in range(1, 13)]
            + [f"2024-{m:02d}-01" for m in range(1, 10)],
        )
        data["manifest"].update(
            observation_end="2024-09-30", knowledge_cutoff="2024-09-30"
        )
        from market_atlas.contracts import sha256

        data["manifest"]["input_selection_sha256"] = sha256(
            {
                k: data["manifest"][k]
                for k in (
                    "source",
                    "objects",
                    "series_ids",
                    "observation_start",
                    "observation_end",
                    "knowledge_cutoff",
                )
            }
        )
        # March is absent: estimates recover in August after unavailable windows.
        data["macro_observations"] = [
            r
            for r in data["macro_observations"]
            if r["source_record"] != "A:2024-03-01:v1"
        ]
        from test_macro_analytics_series import rehash

        rehash(data)
        result = calculate_relationships(prepare_series(data, config, "2024-09-30"))
        rows = [
            r
            for r in result["relationships"]
            if (r["series_low_id"], r["series_high_id"]) == ("A", "B")
        ]
        self.assertEqual("supported", rows[1]["distance_change_status"])
        self.assertAlmostEqual(0, rows[1]["distance_change"])
        by_date = {r["knowledge_date"]: r for r in rows}
        recovered = by_date["2024-08-31"]
        self.assertEqual("supported", recovered["estimate_status"])
        self.assertEqual(
            "prior_estimate_unavailable", recovered["distance_change_status"]
        )
        self.assertIsNone(recovered["distance_change"])
        self.assertEqual("2024-07-31", recovered["comparison_knowledge_date"])
        self.assertEqual("supported", by_date["2024-09-30"]["distance_change_status"])

    def test_derived_panel_tampering_is_rejected_even_with_new_envelope_hash(self):
        config = settings()
        prepared = prepare_series(capture(config), config, "2024-06-30")
        changed = copy.deepcopy(prepared)
        changed["panels"][0]["members"][0]["points"][0]["value"] = 1000
        from market_atlas.contracts import sha256

        changed["prepared_sha256"] = sha256(
            {k: v for k, v in changed.items() if k != "prepared_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "reconstructed"):
            calculate_relationships(changed)


if __name__ == "__main__":
    unittest.main()
