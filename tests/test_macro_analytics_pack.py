import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_macro_analytics_series import capture, settings

from market_atlas.analytics.macro_pack import build_pack, validate_pack, write_prepared
from market_atlas.analytics.macro_series import prepare_series
from market_atlas.cli import main


class MacroPackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        config = settings()
        self.prepared = prepare_series(capture(config), config, "2024-06-30")

    def test_build_reuse_csv_grains_and_independent_validation(self):
        source = write_prepared(self.prepared, self.root / "prepared")
        first = build_pack(source, self.root / "packs")
        directory = Path(first["pack_directory"])
        manifest = (directory / "manifest.json").read_bytes()
        second = build_pack(source, self.root / "packs")
        self.assertEqual(first, second)
        self.assertEqual(manifest, (directory / "manifest.json").read_bytes())
        self.assertEqual("valid", validate_pack(directory)["status"])
        import csv

        with (directory / "relationships.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        keys = [
            (
                r["group_id"],
                r["knowledge_date"],
                r["series_low_id"],
                r["series_high_id"],
            )
            for r in rows
        ]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(18, len(rows))
        schema = json.loads((directory / "schema.json").read_text())
        self.assertEqual(
            "number", schema["tables"]["relationships"]["columns"]["distance"]
        )
        self.assertIn("prepared_sha256", rows[0])

    def test_tampered_pack_is_rejected_and_not_replaced(self):
        source = write_prepared(self.prepared, self.root / "prepared")
        result = build_pack(source, self.root / "packs")
        directory = Path(result["pack_directory"])
        (directory / "relationships.csv").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            validate_pack(directory)
        with self.assertRaises(ValueError):
            build_pack(source, self.root / "packs")
        self.assertEqual("tampered", (directory / "relationships.csv").read_text())

    def test_failed_new_pack_preserves_existing_pack(self):
        source = write_prepared(self.prepared, self.root / "prepared")
        first = build_pack(source, self.root / "packs")
        original = Path(first["pack_directory"]) / "manifest.json"
        before = original.read_bytes()
        self.prepared["capture"]["manifest"]["extracted_at"] = (
            "2024-07-02T00:00:00+00:00"
        )
        config = settings()
        other = prepare_series(self.prepared["capture"], config, "2024-06-30")
        second_source = write_prepared(other, self.root / "prepared")
        with (
            patch(
                "market_atlas.analytics.macro_pack._artifact_files",
                side_effect=OSError("injected"),
            ),
            self.assertRaises(OSError),
        ):
            build_pack(second_source, self.root / "packs")
        self.assertEqual(before, original.read_bytes())
        self.assertEqual(1, len(list((self.root / "packs").iterdir())))

    def test_cli_offline_prepare_build_and_validate(self):
        from market_atlas.contracts import canonical_bytes

        raw = self.root / "capture.json"
        raw.write_bytes(canonical_bytes(self.prepared["capture"]))
        config = self.root / "settings.toml"
        config.write_text("""
version = "test-v1"
observation_start = "2023-01-01"
output_start = "2024-01-01"
max_rows = 1000
redistribution_status = "synthetic"
[[groups]]
id = "test"
frequency = "m"
window = 3
minimum_pairs = 3
baseline = 3
minimum_baseline = 3
change_lag_evaluations = 1
members = [
 {series_id="A", unit="Percent", transform="difference", orientation=1},
 {series_id="B", unit="Percent", transform="difference", orientation=1},
 {series_id="C", unit="Percent", transform="difference", orientation=1},
]
""")
        preparation_output = io.StringIO()
        with contextlib.redirect_stdout(preparation_output):
            self.assertEqual(
                0,
                main(
                    [
                        "analytics",
                        "prepare-macro",
                        "--capture",
                        str(raw),
                        "--settings",
                        str(config),
                        "--config",
                        str(self.root / "no-credentials"),
                        "--as-of",
                        "2024-06-30",
                        "--output",
                        str(self.root / "prepared"),
                    ]
                ),
            )
        prepared = Path(json.loads(preparation_output.getvalue())["prepared_file"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                0,
                main(
                    [
                        "analytics",
                        "build-macro",
                        "--input",
                        str(prepared),
                        "--output",
                        str(self.root / "packs"),
                    ]
                ),
            )
        result = json.loads(output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0,
                main(
                    ["analytics", "validate-macro", "--input", result["pack_directory"]]
                ),
            )
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(
                1,
                main(
                    [
                        "analytics",
                        "validate-macro",
                        "--input",
                        str(self.root / "missing"),
                    ]
                ),
            )


if __name__ == "__main__":
    unittest.main()
