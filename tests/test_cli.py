import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from market_atlas.cli import main
from market_atlas.source_contracts import load_source_contract_registry


class CliTests(unittest.TestCase):
    def test_fixture_inspect_exercises_the_documented_cutoff_workflow(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                ["fixture", "inspect", "--knowledge-cutoff", "2024-02-10T00:00:00Z"]
            )
        self.assertEqual(0, status)
        view = json.loads(output.getvalue())
        self.assertEqual("2024-02-10T00:00:00Z", view["knowledge_cutoff"])
        self.assertTrue(view["synthetic"])

    def test_database_verify_contracts_reports_a_valid_registry_match(self):
        registry = load_source_contract_registry()
        catalog = {
            "catalog_version": "source-catalog-v2",
            "catalog_fingerprint_sha256": "a" * 64,
            "objects": [
                {
                    "schema_name": contract["schema_name"],
                    "object_name": contract["object_name"],
                    "object_type": contract["object_type"],
                    "can_select": True,
                    "can_write": False,
                    "read_probe_status": "passed",
                    "columns": [
                        {"column_name": column}
                        for column in contract["required_columns"]
                    ],
                    "column_fingerprint_sha256": contract[
                        "expected_column_fingerprint_sha256"
                    ],
                    "view_definition_md5": contract.get(
                        "expected_view_definition_md5"
                    ),
                }
                for contract in registry["contracts"]
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            catalog_path = Path(temporary_directory) / "catalog.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    ["database", "verify-contracts", "--catalog", str(catalog_path)]
                )

        self.assertEqual(0, status)
        result = json.loads(output.getvalue())
        self.assertEqual("valid", result["status"])
        self.assertEqual(5, result["supported_live_count"])


if __name__ == "__main__":
    unittest.main()
