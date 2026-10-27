"""Guard the source-controlled Power BI fixture model contract."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "powerbi" / "MarketAtlas.model.template.tmdl"
README = ROOT / "powerbi" / "README.md"


class PowerBiContractTests(unittest.TestCase):
    def test_model_uses_one_explicit_snapshot_parameter_for_all_imports(self) -> None:
        model = MODEL.read_text()
        self.assertEqual(model.count("expression pSnapshotId"), 1)
        self.assertEqual(model.count("Text.From(pSnapshotId)"), 6)
        self.assertNotIn("FROM atlas_report.current_relationship_fact", model)
        self.assertNotIn("FROM atlas_report.current_macro_context_fact", model)
        self.assertNotIn("FROM atlas_report.current_rolling_correlation_estimate", model)

    def test_model_stays_on_report_snapshot_tables_without_secrets(self) -> None:
        model = MODEL.read_text().lower()
        for table in (
            "atlas_report.node_snapshot",
            "atlas_report.relationship_snapshot",
            "atlas_report.macro_context_snapshot",
            "atlas_report.rolling_correlation_estimate_snapshot",
            "atlas_report.provenance_snapshot",
        ):
            self.assertIn(table, model)
        self.assertNotIn("password", model)
        self.assertNotIn("macro_medallion", model)
        self.assertIn("pinned snapshot status", model)

    def test_handoff_requires_real_power_bi_reconciliation_before_acceptance(self) -> None:
        readme = README.read_text()
        self.assertIn("real Power BI Desktop", readme)
        self.assertIn("14 distinct assertion IDs", readme)
        self.assertIn("32 distinct estimate version IDs", readme)


if __name__ == "__main__":
    unittest.main()
