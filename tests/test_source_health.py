"""Quality diagnostics must distinguish source policy, clocks and unknown evidence."""

import contextlib
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from market_atlas.source_health import (
    analyze,
    collect,
    prepare_recovery_review,
    run_diagnostics,
)


def capture():
    return {
        "captured_at": "2026-10-31T12:00:00+00:00",
        "clock": {"source_date": "2026-10-31", "source_timezone": "Etc/UTC"},
        "window": {"start": "2024-01-01", "end": "2026-10-31"},
        "contract_gate": {"status": "valid"},
        "runs": [],
        "metadata": [
            {
                "series_id": s,
                "title": s,
                "frequency": "m",
                "units": "Percent",
                "active": 1,
                "vintage_enabled": enabled,
                "load_type": "incremental",
                "expected_update_frequency": "monthly",
            }
            for s, enabled in [("A", 0), ("B", 1), ("C", 1)]
        ],
        "coverage": [
            {
                "series_id": "A",
                "frequency": "m",
                "latest_observation_date": "2026-08-01",
                "days_since_last": 91,
                "is_stale": 1,
            },
            {
                "series_id": "B",
                "frequency": "m",
                "latest_observation_date": "2026-09-01",
                "days_since_last": 60,
                "is_stale": 0,
            },
        ],
        "vintages": [
            {
                "series_id": "A",
                "observation_versions": 2,
                "undated_versions": 2,
                "dated_versions": 0,
                "last_changed_at": "2026-10-31T10:00:00+00:00",
            },
            {
                "series_id": "B",
                "observation_versions": 2,
                "undated_versions": 1,
                "dated_versions": 1,
            },
        ],
        "attempts": [
            {
                "series_id": "A",
                "status": "skipped_not_due",
                "started_at": "2026-10-31T11:00:00+00:00",
            },
            {"series_id": "B", "status": "succeeded", "rows_merged_silver": 0},
        ],
    }


class SourceHealthTests(unittest.TestCase):
    def test_collection_batches_ids_and_checks_hard_catalog_limit(self):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        connection = SimpleNamespace(cursor=lambda: cursor)
        metadata = [{"series_id": str(i)} for i in range(26)]
        with (
            patch("market_atlas.source_health.inspect_source"),
            patch("market_atlas.source_health.build_source_catalog"),
            patch(
                "market_atlas.source_health.verify_source_contracts",
                return_value={"status": "valid"},
            ),
            patch(
                "market_atlas.source_health._read_only_connection",
                side_effect=lambda _: contextlib.nullcontext(connection),
            ),
            patch(
                "market_atlas.source_health._rows",
                side_effect=[
                    [{"source_date": "2026-10-31"}],
                    metadata,
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
            ) as reads,
        ):
            result = collect(
                SimpleNamespace(role="marketatlas_source_reader"),
                start="2024-01-01",
                end="2026-10-31",
            )
            reads.side_effect = [[{"source_date": "2026-10-31"}], metadata]
            with self.assertRaisesRegex(ValueError, "series limit"):
                collect(
                    SimpleNamespace(role="marketatlas_source_reader"),
                    start="2024-01-01",
                    end="2026-10-31",
                    max_series=25,
                )
        self.assertEqual(len(result["metadata"]), 26)
        batches = [
            call.args[1][0]
            for call in cursor.execute.call_args_list
            if len(call.args) > 1 and isinstance(call.args[1][0], list)
        ]
        self.assertEqual(
            [len(batch) for batch in batches], [25, 25, 25, 25, 1, 1, 1, 1]
        )
        self.assertEqual(cursor.execute.call_args_list[1].args[1], (1001,))

    def test_current_only_policy_is_distinct_from_corrupt_or_absent_vintages(self):
        source = capture()
        before = copy.deepcopy(source)
        result = analyze(source)
        rows = {r["series_id"]: r for r in result["series"]}
        self.assertEqual(rows["A"]["vintage_status"], "current_only_by_source_policy")
        self.assertEqual(
            rows["B"]["vintage_status"], "unexpected_missing_or_invalid_vintages"
        )
        self.assertEqual(rows["C"]["vintage_status"], "no_observations_in_window")
        self.assertEqual(result["summary"]["stale_latest_attempt_skipped"], 1)
        self.assertEqual(result["summary"]["unknown_stale_flags"], 1)
        self.assertEqual(source, before)
        self.assertNotIn("available_on", json.dumps(result))

    def test_empty_window_and_exact_api_page_size_trigger_pagination_review(self):
        source = capture()
        source["successes"] = [{"series_id": "C", "observations_extracted": 100000}]
        result = analyze(source)
        self.assertEqual(
            result["summary"]["observation_page_limit_suspected_series"], 1
        )
        self.assertEqual(
            result["series"][2]["freshness_action"], "review_observation_pagination"
        )

    def test_recent_row_change_does_not_clear_staleness_or_verify_poll(self):
        result = analyze(capture())
        row = result["series"][0]
        self.assertTrue(row["reported_stale"])
        self.assertEqual(row["freshness_action"], "force_source_poll_review")
        self.assertFalse(row["coverage_rule_mismatch"])
        self.assertEqual(result["summary"]["coverage_rule_mismatches"], 0)

    def test_threshold_boundary_and_unknown_rules(self):
        source = capture()
        source["coverage"][0].update(
            latest_observation_date="2026-08-17", days_since_last=75, is_stale=0
        )
        result = analyze(source)
        self.assertFalse(result["series"][0]["recomputed_stale"])
        source["coverage"][0]["is_stale"] = 1
        self.assertTrue(analyze(source)["series"][0]["coverage_rule_mismatch"])
        source["coverage"][0]["frequency"] = "unknown"
        self.assertIsNone(analyze(source)["series"][0]["recomputed_stale"])
        source["coverage"][0]["frequency"] = "m"
        source["coverage"][0]["is_stale"] = None
        self.assertIsNone(analyze(source)["series"][0]["reported_stale"])

    def test_source_failures_and_coverage_disagreements_prioritized(self):
        source = capture()
        source["attempts"][0]["status"] = "failed"
        self.assertEqual(
            analyze(source)["series"][0]["freshness_action"], "review_source_failure"
        )
        source["coverage"][0]["days_since_last"] = 0
        self.assertEqual(
            analyze(source)["series"][0]["freshness_action"],
            "review_frequency_or_coverage_rule",
        )

    def test_review_manifests_and_commands_do_not_execute_or_embed_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            prepare_recovery_review(analyze(capture()), directory)
            root = Path(directory)
            freshness = json.loads((root / "freshness-review.yml").read_text())
            vintage = json.loads((root / "vintages-review.yml").read_text())
            self.assertFalse(freshness["series"][0]["vintage_enabled"])
            self.assertTrue(vintage["series"][0]["vintage_enabled"])
            plan = json.loads((root / "dry-run-plan.json").read_text())
            for command in plan["commands"]:
                self.assertIn("--dry-run", command["argv"])
                self.assertIn("--no-skip-not-due", command["argv"])
                self.assertFalse(command["executed"])
            self.assertNotIn("api_key", (root / "recovery-config.yml").read_text())
            self.assertEqual(
                json.loads((root / "recovery-config.yml").read_text())["default"][
                    "notify_on"
                ],
                "never",
            )

    def test_invalid_role_bounds_window_or_output_fail_before_database_access(self):
        for kwargs, role in [
            ({}, "fred"),
            ({"batch_size": 26}, "marketatlas_source_reader"),
            ({"max_series": 1001}, "marketatlas_source_reader"),
        ]:
            with (
                self.subTest(kwargs=kwargs, role=role),
                patch("market_atlas.source_health.inspect_source") as inspect,
            ):
                with self.assertRaises(ValueError):
                    collect(
                        SimpleNamespace(role=role),
                        start="2024-01-01",
                        end="2026-10-31",
                        **kwargs,
                    )
                inspect.assert_not_called()
        with (
            tempfile.TemporaryDirectory() as outside,
            self.assertRaisesRegex(ValueError, "ignored"),
        ):
            run_diagnostics("configs/local.toml", outside)
