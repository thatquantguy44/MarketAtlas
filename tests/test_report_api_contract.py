import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from market_atlas.config import TargetDatabaseConfig
from market_atlas.report_api import load_revision_quality


class ReportApiContractTests(unittest.TestCase):
    def test_revision_quality_rejects_unbounded_or_invalid_selections(self):
        config = TargetDatabaseConfig("unused", 5432, "unused", "unused", "unused")
        for selection in ("", "not-a-uuid", "a,b"):
            with (
                self.subTest(selection=selection),
                self.assertRaisesRegex(ValueError, "UUID"),
            ):
                load_revision_quality(config, selection)

    def test_revision_quality_distinguishes_unpublished_unselected_and_unknown(self):
        config = TargetDatabaseConfig("unused", 5432, "unused", "unused", "unused")
        selected_id = "11111111-1111-1111-1111-111111111111"
        cases = [
            (None, "not_published"),
            (("snapshot", "date", None, None, None, None, None, None), "not_selected"),
            (
                (
                    "snapshot",
                    "date",
                    "input",
                    "build",
                    selected_id,
                    "SYNTH_A",
                    "synthetic-source",
                    {"quality_status": "unknown", "observation_count": None},
                ),
                "selected",
            ),
        ]
        for row, expected in cases:
            connect = MagicMock()
            with (
                self.subTest(expected=expected),
                patch.dict(sys.modules, {"psycopg": SimpleNamespace(connect=connect)}),
            ):
                cursor = MagicMock()
                cursor.fetchone.return_value = row
                connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
                result = load_revision_quality(config, selected_id)
                self.assertEqual(expected, result["status"])
                if expected == "selected":
                    self.assertEqual("unknown", result["summary"]["quality_status"])
                    self.assertIsNone(result["summary"]["observation_count"])
                else:
                    self.assertIsNone(result["summary"])

    def test_live_graph_api_uses_only_report_views_and_report_role(self):
        implementation = Path("src/market_atlas/report_api.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("SET LOCAL ROLE marketatlas_report_reader", implementation)
        self.assertIn("atlas_report.current_macro_economic_graph_node", implementation)
        self.assertIn("atlas_report.current_macro_economic_graph_edge", implementation)
        self.assertIn("concept_neighborhood", implementation)
        self.assertIn("LIMIT %s OFFSET %s", implementation)
        self.assertIn("aggregate_navigation", implementation)
        self.assertNotIn("gold.", implementation)
        self.assertNotIn("meta.", implementation)


if __name__ == "__main__":
    unittest.main()
