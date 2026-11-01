import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_macro_analytics_series import capture, rehash, settings

from market_atlas.analytics.macro_pack import build_pack, write_prepared
from market_atlas.analytics.macro_series import prepare_series
from market_atlas.reporting.macro_analytics import QUERY_IDS, analytics_queries


class BrowserAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        config = settings()
        raw = capture(config)
        next(
            r
            for r in raw["macro_observations"]
            if r["source_record"] == "A:2024-05-01:v1"
        ).update(value=None, is_missing=True)
        rehash(raw)
        self.prepared = prepare_series(raw, config, "2024-06-30")
        source = write_prepared(self.prepared, self.root / "prepared")
        self.pack = Path(build_pack(source, self.root / "packs")["pack_directory"])

    def test_exact_estimates_and_deduplicated_source_windows_are_retained(self):
        queries = analytics_queries(self.pack)
        self.assertEqual(set(QUERY_IDS), set(queries))
        pairs = queries["macro_analytics_relationships"]["rows"]
        original = json.loads((self.pack / "results.json").read_text())["relationships"]
        self.assertEqual(
            original,
            [{k: v for k, v in row.items() if k != "pair_key"} for row in pairs],
        )
        points = {
            row["point_id"]: row for row in queries["macro_analytics_points"]["rows"]
        }
        evidence = queries["macro_analytics_evidence"]["rows"]
        for panel in self.prepared["panels"]:
            for member in panel["members"]:
                linked = next(
                    row
                    for row in evidence
                    if row["knowledge_date"] == panel["knowledge_date"]
                    and row["series_id"] == member["series_id"]
                )
                decoded = [points[i] for i in json.loads(linked["window_point_ids"])]
                self.assertEqual(
                    member["points"],
                    [
                        {
                            **{
                                k: v
                                for k, v in row.items()
                                if k not in {"point_id", "series_id", "group_id"}
                            },
                            "source_records": json.loads(row["source_records"]),
                        }
                        for row in decoded
                    ],
                )
        self.assertLess(len(points), len(evidence) * 3)
        self.assertIn(
            "window_point_ids", queries["macro_analytics_evidence"]["payloadColumns"]
        )
        self.assertNotIn(str(self.root), json.dumps(queries))

    def test_tampering_rejected_before_browser_rows_exist(self):
        (self.pack / "relationships.csv").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            analytics_queries(self.pack)

    def test_browser_snapshot_option_is_explicit_and_uses_separate_query_identities(
        self,
    ):
        # The existing publication snapshot remains independently validated.
        from market_atlas.reporting.browser import browser_snapshot

        with (
            patch(
                "market_atlas.reporting.browser.validate_pack",
                side_effect=ValueError("not a report pack"),
            ),
            self.assertRaisesRegex(ValueError, "not a report pack"),
        ):
            browser_snapshot(self.pack, analytics_pack=self.pack)


if __name__ == "__main__":
    unittest.main()
