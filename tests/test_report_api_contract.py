import unittest
from pathlib import Path


class ReportApiContractTests(unittest.TestCase):
    def test_live_graph_api_uses_only_report_views_and_report_role(self):
        implementation = Path("src/market_atlas/report_api.py").read_text(encoding="utf-8")
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
