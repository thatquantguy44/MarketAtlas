import unittest

from market_atlas.graph.macro_economic import _concept_key, _concept_label


class MacroEconomicGraphTests(unittest.TestCase):
    def test_normalizes_source_taxonomy_category_to_a_stable_concept_identity(self):
        self.assertEqual("inflation", _concept_key(" INFLATION "))
        self.assertEqual("Labor Market", _concept_label("labor market"))

    def test_rejects_an_empty_taxonomy_category(self):
        with self.assertRaisesRegex(ValueError, "econ_category"):
            _concept_key(" -- ")


if __name__ == "__main__":
    unittest.main()
