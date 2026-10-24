import copy
import json
import tempfile
import unittest
from pathlib import Path

from market_atlas.cli import main
from market_atlas.contracts import available_view, canonical_bytes, validate_fixture
from market_atlas.fixtures import build_fixture


class FixtureContractTests(unittest.TestCase):
    def test_fixture_is_deterministic_and_covers_required_edge_cases(self):
        first = build_fixture()
        self.assertEqual(canonical_bytes(first), canonical_bytes(build_fixture()))
        self.assertEqual([], validate_fixture(first))
        self.assertEqual(
            {"OLDX", "NEWX"},
            {row["value"] for row in first["identifiers"] if row["entity_id"] == "L-A"},
        )
        self.assertEqual(
            2,
            len(
                [
                    row
                    for row in first["macro_observations"]
                    if row["period"] == "2024-01"
                ]
            ),
        )
        self.assertTrue(any(row["status"] == "disputed" for row in first["assertions"]))
        correction = next(row for row in first["assertions"] if row["id"] == "A15")
        self.assertEqual("A6", correction["supersedes_id"])
        self.assertEqual("REL-ALPHA-TECH", correction["assertion_key"])
        self.assertEqual(
            75,
            len(
                [
                    row
                    for row in first["market_observations"]
                    if row["instrument_id"] == "I-C"
                ]
            ),
        )
        self.assertLess(
            len(
                [
                    row
                    for row in first["market_observations"]
                    if row["instrument_id"] == "I-B"
                ]
            ),
            75,
        )

    def test_knowledge_cutoff_excludes_later_macro_revision_and_reference_fact(self):
        fixture = build_fixture()
        early = available_view(fixture, "2024-02-10T00:00:00Z")
        late = available_view(fixture, "2024-04-20T00:00:00Z")
        self.assertEqual("initial", early["macro_vintages"][0]["vintage"])
        self.assertEqual("revision", late["macro_vintages"][0]["vintage"])
        self.assertNotIn("A14", early["assertion_ids"])
        self.assertIn("A14", late["assertion_ids"])

    def test_invalid_endpoint_and_tampered_file_are_rejected(self):
        fixture = copy.deepcopy(build_fixture())
        fixture["assertions"][0]["target_id"] = "missing"
        self.assertTrue(
            any(
                "invalid predicate or endpoint types" in error
                for error in validate_fixture(fixture)
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(0, main(["fixture", "build", "--output", directory]))
            self.assertEqual(0, main(["fixture", "validate", "--input", directory]))
            payload = json.loads((path / "fixture.json").read_text())
            payload["entities"][0]["label"] = "tampered"
            (path / "fixture.json").write_bytes(canonical_bytes(payload))
            self.assertEqual(1, main(["fixture", "validate", "--input", directory]))


if __name__ == "__main__":
    unittest.main()
