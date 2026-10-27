import copy
import unittest
from decimal import Decimal

from market_atlas.adapters.macro_context import build_revision_summary_extract


def valid_rows() -> list[dict[str, object]]:
    return [
        {
            "series_id": "CPIAUCSL",
            "observation_count": 12,
            "avg_revision_count": 1.25,
            "max_revision_count": 3,
            "avg_abs_revision_pct": 0.4,
            "max_abs_revision_pct": 1.1,
        }
    ]


class RevisionSummaryContractTests(unittest.TestCase):
    def test_builds_a_current_only_restricted_extract_and_marks_missing_series(self):
        extract = build_revision_summary_extract(
            ["CPIAUCSL", "GDP"], valid_rows(), page_size=200
        )

        self.assertEqual(
            "source_contract_extracted; not_loaded_to_marketatlas_graph",
            extract["manifest"]["status"],
        )
        self.assertEqual("restricted", extract["manifest"]["redistribution_status"])
        self.assertEqual("current_only_revision_quality", extract["manifest"]["temporal_status"])
        self.assertEqual(["GDP"], extract["missing_series_ids"])
        self.assertEqual(["CPIAUCSL"], [row["series_id"] for row in extract["revision_summaries"]])

    def test_rejects_a_summary_for_an_unselected_series(self):
        with self.assertRaisesRegex(ValueError, "unselected series"):
            build_revision_summary_extract(["CPIAUCSL"], valid_rows() + [{**valid_rows()[0], "series_id": "GDP"}])

    def test_rejects_duplicate_summary_rows(self):
        rows = valid_rows()
        rows.append(copy.deepcopy(rows[0]))

        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_revision_summary_extract(["CPIAUCSL"], rows)

    def test_accepts_postgresql_decimal_summary_metrics(self):
        rows = valid_rows()
        rows[0]["avg_revision_count"] = Decimal("1.25")

        extract = build_revision_summary_extract(["CPIAUCSL"], rows)

        self.assertEqual(1.25, extract["revision_summaries"][0]["avg_revision_count"])


if __name__ == "__main__":
    unittest.main()
