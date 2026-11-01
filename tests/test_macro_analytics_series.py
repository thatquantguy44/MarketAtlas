import copy
import math
import unittest
from unittest.mock import MagicMock, patch

from market_atlas.analytics.macro_series import (
    capture_and_prepare,
    prepare_series,
    validate_settings,
)
from market_atlas.contracts import sha256


def settings(frequency="m", transform="difference"):
    return {
        "version": "test-v1",
        "observation_start": "2023-01-01",
        "output_start": "2024-01-01",
        "max_rows": 1000,
        "redistribution_status": "synthetic",
        "groups": [
            {
                "id": "test",
                "frequency": frequency,
                "window": 3,
                "minimum_pairs": 3,
                "baseline": 3,
                "minimum_baseline": 3,
                "change_lag_evaluations": 1,
                "members": [
                    {
                        "series_id": key,
                        "unit": "Percent",
                        "transform": transform,
                        "orientation": 1,
                    }
                    for key in ("A", "B", "C")
                ],
            }
        ],
    }


def capture(config, periods=None):
    periods = periods or [f"2023-{month:02d}-01" for month in range(1, 13)] + [
        f"2024-{month:02d}-01" for month in range(1, 7)
    ]
    entities, observations = [], []
    for member in config["groups"][0]["members"]:
        sid = member["series_id"]
        entities.append(
            {
                "canonical_key": f"macro:fred:{sid}",
                "type": "macro_series",
                "source_identifier": sid,
                "frequency": config["groups"][0]["frequency"],
                "unit": "Percent",
                "active": True,
                "vintage_enabled": True,
            }
        )
        value = 100
        for index, period in enumerate(periods):
            value += index % 5 + 1
            observations.append(
                {
                    "series_canonical_key": f"macro:fred:{sid}",
                    "reference_period": period,
                    "value": str(value),
                    "available_on": period,
                    "source_valid_through_inclusive": "9999-12-31",
                    "is_missing": False,
                    "source_record": f"{sid}:{period}:v1",
                }
            )
    selection = {
        "source": "macro_medallion_postgresql",
        "objects": ["meta.fred_series", "gold.fred_point_in_time"],
        "series_ids": [m["series_id"] for m in config["groups"][0]["members"]],
        "observation_start": config["observation_start"],
        "observation_end": "2024-06-30",
        "knowledge_cutoff": "2024-06-30",
    }
    result = {
        "entities": entities,
        "macro_observations": observations,
        "manifest": {
            **selection,
            "input_selection_sha256": sha256(selection),
            "redistribution_status": "synthetic",
            "extracted_at": "2024-07-01T00:00:00+00:00",
            "series_metadata_context": "current_not_point_in_time",
        },
    }
    rehash(result)
    return result


def rehash(value):
    value["manifest"]["source_rows_sha256"] = sha256(
        {key: value[key] for key in ("entities", "macro_observations")}
    )


def first_member(prepared, panel_index=-1):
    return prepared["panels"][panel_index]["members"][0]


class MacroPreparationTests(unittest.TestCase):
    def test_unapproved_catalog_identity_is_rejected_before_source_extraction(self):
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            ("A",),
            ("B",),
        ]
        with (
            patch(
                "market_atlas.adapters.macro_medallion._read_only_connection"
            ) as reader,
            patch("market_atlas.adapters.macro_medallion.extract") as extractor,
        ):
            reader.return_value.__enter__.return_value = connection
            with self.assertRaisesRegex(ValueError, "approved FRED catalog"):
                capture_and_prepare(object(), settings(), "2024-06-30")
            extractor.assert_not_called()

    def test_difference_orientation_and_past_only_standardization(self):
        config = settings()
        config["groups"][0]["members"][0]["orientation"] = -1
        prepared = prepare_series(capture(config), config, "2024-06-30")
        latest = first_member(prepared)
        # May 2024 change is 2; its preceding changes are 4, 5, 1.
        self.assertEqual(-2, latest["points"][-1]["value"])
        self.assertAlmostEqual(-10 / 3, latest["baseline_mean"])
        self.assertAlmostEqual((4 / 3) / math.sqrt(13 / 3), latest["zscore"])
        self.assertEqual("2024-05-01", latest["points"][-1]["reference_period"])

    def test_later_revision_cannot_change_earlier_panel(self):
        config = settings()
        original = capture(config)
        revised = copy.deepcopy(original)
        row = next(
            r
            for r in revised["macro_observations"]
            if r["source_record"] == "A:2023-12-01:v1"
        )
        row["source_valid_through_inclusive"] = "2024-03-14"
        revised["macro_observations"].append(
            {
                **row,
                "value": "999",
                "available_on": "2024-03-15",
                "source_valid_through_inclusive": "9999-12-31",
                "source_record": "A:2023-12-01:v2",
            }
        )
        rehash(revised)
        before = prepare_series(original, config, "2024-06-30")
        after = prepare_series(revised, config, "2024-06-30")
        self.assertEqual(first_member(before, 0), first_member(after, 0))
        self.assertNotEqual(first_member(before, 2), first_member(after, 2))

    def test_gap_does_not_create_a_multi_period_change(self):
        config = settings()
        data = capture(config)
        data["macro_observations"] = [
            r
            for r in data["macro_observations"]
            if r["source_record"] != "A:2024-04-01:v1"
        ]
        rehash(data)
        points = first_member(prepare_series(data, config, "2024-06-30"))["points"]
        self.assertIsNone(points[-1]["value"])
        self.assertEqual("absent_period", points[-1]["status"])

    def test_unknown_dates_and_conflicting_versions_are_withheld(self):
        for variant, expected in (
            ("unknown", "unknown_vintage"),
            ("conflict", "ambiguous_vintage"),
        ):
            with self.subTest(variant=variant):
                config = settings()
                data = capture(config)
                row = next(
                    r
                    for r in data["macro_observations"]
                    if r["source_record"] == "A:2024-05-01:v1"
                )
                if variant == "unknown":
                    row["available_on"] = ""
                    row["source_valid_through_inclusive"] = ""
                else:
                    data["macro_observations"].append(
                        {**row, "source_record": "conflict", "value": "999"}
                    )
                rehash(data)
                latest = first_member(prepare_series(data, config, "2024-06-30"))
                self.assertEqual(expected, latest["points"][-1]["status"])
                self.assertIsNone(latest["points"][-1]["value"])

    def test_log_changes_and_nonpositive_levels(self):
        config = settings(transform="log_change")
        data = capture(config)
        result = prepare_series(data, config, "2024-06-30")
        rows = {
            r["reference_period"]: float(r["value"])
            for r in data["macro_observations"]
            if r["series_canonical_key"] == "macro:fred:A"
        }
        self.assertAlmostEqual(
            100 * math.log(rows["2024-05-01"] / rows["2024-04-01"]),
            first_member(result)["points"][-1]["value"],
        )
        next(
            r
            for r in data["macro_observations"]
            if r["source_record"] == "A:2024-05-01:v1"
        )["value"] = "0"
        rehash(data)
        latest = first_member(prepare_series(data, config, "2024-06-30"))
        self.assertEqual("nonpositive_log_input", latest["points"][-1]["status"])

    def test_metadata_mismatch_and_tampering(self):
        config = settings()
        data = capture(config)
        data["entities"][0]["frequency"] = "q"
        rehash(data)
        result = prepare_series(data, config, "2024-06-30")
        self.assertEqual("metadata_mismatch", result["eligibility"][0]["status"])
        self.assertTrue(all(p["value"] is None for p in first_member(result)["points"]))
        data["macro_observations"][0]["value"] = "99999"
        with self.assertRaisesRegex(ValueError, "hash"):
            prepare_series(data, config, "2024-06-30")

    def test_daily_grid_excludes_weekends_and_does_not_fill_holidays(self):
        config = settings(frequency="d")
        config["output_start"] = "2024-01-05"
        periods = [
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
            "2024-01-09",
            "2024-01-10",
        ]
        data = capture(config, periods)
        result = prepare_series(data, config, "2024-06-30")
        panels = {p["knowledge_date"]: p for p in result["panels"]}
        self.assertNotIn("2024-01-06", panels)
        latest = panels["2024-01-10"]["members"][0]["points"][-1]
        self.assertEqual("2024-01-09", latest["reference_period"])
        self.assertEqual("absent_period", latest["status"])

    def test_bounds_duplicates_and_unknown_settings_fail(self):
        for mutate in (
            lambda c: c.update({"typo": 1}),
            lambda c: c["groups"][0].update({"frequency": "q"}),
            lambda c: c["groups"][0].update({"minimum_pairs": 4}),
            lambda c: c["groups"][0]["members"].append(c["groups"][0]["members"][0]),
        ):
            config = settings()
            mutate(config)
            with self.assertRaises(ValueError):
                validate_settings(config, "2024-06-30")

    def test_closed_vintage_intervals_and_absent_availability_are_distinct(self):
        config = settings()
        original = capture(config)
        row = next(
            r
            for r in original["macro_observations"]
            if r["source_record"] == "A:2023-12-01:v1"
        )
        row["source_valid_through_inclusive"] = "2024-01-31"
        original["macro_observations"].append(
            {
                **row,
                "value": "200",
                "available_on": "2024-02-01",
                "source_valid_through_inclusive": "9999-12-31",
                "source_record": "A:2023-12-01:v2",
            }
        )
        rehash(original)
        result = prepare_series(original, config, "2024-06-30")
        january = first_member(result, 0)["points"][-1]
        february = first_member(result, 1)["points"][-2]
        self.assertIn("A:2023-12-01:v1", january["source_records"])
        self.assertIn("A:2023-12-01:v2", february["source_records"])
        self.assertNotIn("A:2023-12-01:v2", january["source_records"])
        # An expired version without a replacement cannot be carried forward.
        original["macro_observations"].pop()
        rehash(original)
        expired = prepare_series(original, config, "2024-06-30")
        self.assertEqual(
            "not_available_at_cutoff", first_member(expired, 1)["points"][-2]["status"]
        )

    def test_nonfinite_values_and_invalid_missing_flags_are_withheld(self):
        for updates in (
            {"value": True},
            {"value": "NaN"},
            {"value": "Infinity"},
            {"value": None},
            {"is_missing": 0},
            {"is_missing": True, "value": "100"},
        ):
            with self.subTest(updates=updates):
                config = settings()
                data = capture(config)
                next(
                    r
                    for r in data["macro_observations"]
                    if r["source_record"] == "A:2024-05-01:v1"
                ).update(updates)
                rehash(data)
                latest = first_member(prepare_series(data, config, "2024-06-30"))
                self.assertEqual("invalid_value_state", latest["points"][-1]["status"])
                self.assertIsNone(latest["zscore"])

    def test_constant_baselines_and_source_row_limits(self):
        config = settings()
        data = capture(config)
        for i, row in enumerate(data["macro_observations"]):
            row["value"] = str(i)
        rehash(data)
        latest = first_member(prepare_series(data, config, "2024-06-30"))
        self.assertEqual("zero_baseline_variance", latest["zscore_status"])
        self.assertIsNone(latest["zscore"])
        config["max_rows"] = 1
        with self.assertRaisesRegex(ValueError, "bounds"):
            prepare_series(data, config, "2024-06-30")

    def test_monthly_leap_day_and_partial_month_cutoffs(self):
        config = settings()
        config["output_start"] = "2024-02-01"
        data = capture(config)
        # A retained extract is pinned to its declared selection cutoff.
        data["manifest"].update(
            observation_end="2024-03-15", knowledge_cutoff="2024-03-15"
        )
        selection = {
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
        data["manifest"]["input_selection_sha256"] = sha256(selection)
        data["macro_observations"] = [
            r
            for r in data["macro_observations"]
            if r["reference_period"] <= "2024-03-15"
        ]
        rehash(data)
        result = prepare_series(data, config, "2024-03-15")
        self.assertEqual(
            ["2024-02-29", "2024-03-15"],
            [p["knowledge_date"] for p in result["panels"]],
        )
        self.assertEqual("2024-02-01", result["panels"][-1]["reference_end"])


if __name__ == "__main__":
    unittest.main()
