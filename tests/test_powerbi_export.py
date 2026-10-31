"""Exercise export artifacts and failure boundaries, not only source strings."""

import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from market_atlas.cli import main
from market_atlas.config import ConfigError, load_report_database, load_target_database
from market_atlas.reporting.export import (
    _read_cursor,
    _validate_relations,
    export_pack,
    read_published,
    validate_pack,
)
from market_atlas.reporting.fixture import fixture_tables


class PowerBiExportTests(unittest.TestCase):
    def test_fixture_round_trip_numeric_nulls_grains_and_deterministic_rerun(self):
        with tempfile.TemporaryDirectory() as root:
            result = export_pack(Path(root))
            pack = Path(result["pack"])
            checked = validate_pack(pack)
            self.assertEqual(
                checked["counts"],
                {
                    "nodes": 15,
                    "relationships": 14,
                    "contexts": 3,
                    "correlations": 32,
                    "provenance": 49,
                    "pairs": 2,
                    "dates": 16,
                    "publications": 1,
                },
            )
            manifest = json.loads((pack / "manifest.json").read_text())
            self.assertEqual(manifest["source_kind"], "synthetic_fixture")
            self.assertEqual(len(manifest["generator"]["source_sha256"]), 64)
            self.assertTrue(manifest["generator"]["python_version"])
            correlations = list(
                csv.DictReader((pack / "correlations.csv").read_text().splitlines())
            )
            undefined = [
                r for r in correlations if r["estimate_status"] == "zero_variance"
            ]
            self.assertEqual(len(undefined), 16)
            self.assertTrue(all(r["correlation"] == "" for r in undefined))
            self.assertTrue(
                all(
                    -1 <= float(r["correlation"]) <= 1
                    for r in correlations
                    if r["estimate_status"] == "supported"
                )
            )
            relationships = list(
                csv.DictReader((pack / "relationships.csv").read_text().splitlines())
            )
            ids = {r["assertion_id"]: r for r in relationships}
            self.assertNotIn("A6", ids)
            self.assertEqual(ids["A15"]["assertion_status"], "retracted")
            self.assertEqual(export_pack(Path(root))["status"], "reused")
            self.assertEqual(len(list(Path(root).iterdir())), 1)

    def test_tampered_file_rejected_and_existing_pack_never_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            result = export_pack(Path(root))
            pack = Path(result["pack"])
            target = pack / "nodes.csv"
            target.write_bytes(target.read_bytes() + b"corrupt\n")
            with self.assertRaisesRegex(ValueError, "checksum"):
                validate_pack(pack)
            with self.assertRaises(ValueError):
                export_pack(Path(root))
            self.assertTrue(target.read_bytes().endswith(b"corrupt\n"))

    def test_orphan_duplicate_and_undefined_numeric_failure_leave_prior_pack(self):
        with tempfile.TemporaryDirectory() as root:
            baseline = export_pack(Path(root))
            for failure in ("orphan", "duplicate", "undefined"):
                metadata, tables = fixture_tables()
                if failure == "orphan":
                    tables["relationships"][0]["target_node_id"] = "MISSING"
                elif failure == "duplicate":
                    tables["relationships"].append(dict(tables["relationships"][0]))
                else:
                    next(
                        r
                        for r in tables["correlations"]
                        if r["estimate_status"] == "zero_variance"
                    )["correlation"] = 0.0
                with (
                    patch(
                        "market_atlas.reporting.export.fixture_tables",
                        return_value=(metadata, tables),
                    ),
                    self.assertRaises(ValueError),
                ):
                    export_pack(Path(root))
                self.assertEqual(list(Path(root).iterdir()), [Path(baseline["pack"])])
                self.assertEqual(
                    validate_pack(Path(baseline["pack"]))["status"], "valid"
                )

    def test_cli_needs_no_config_and_validates_written_pack(self):
        with tempfile.TemporaryDirectory() as root:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    ["powerbi", "export", "--output", root, "--config", "/missing"]
                )
            self.assertEqual(code, 0)
            pack = json.loads(stdout.getvalue())["pack"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["powerbi", "validate", "--input", pack]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "powerbi",
                            "export",
                            "--output",
                            root,
                            "--publications",
                            "macro_context",
                        ]
                    ),
                    1,
                )

    def test_multiline_csv_is_lossless_and_nulls_keep_numeric_types(self):
        metadata, tables = fixture_tables()
        text = 'Rationale, with "quotes" and\na second line'
        tables["relationships"][0]["rationale"] = text
        for row in tables["correlations"]:
            row["correlation"], row["estimate_status"] = None, "zero_variance"
        with (
            tempfile.TemporaryDirectory() as root,
            patch(
                "market_atlas.reporting.export.fixture_tables",
                return_value=(metadata, tables),
            ),
        ):
            pack = Path(export_pack(Path(root))["pack"])
            rows = list(
                csv.DictReader(io.StringIO((pack / "relationships.csv").read_text()))
            )
            self.assertIn(text, [r["rationale"] for r in rows])
            manifest = json.loads((pack / "manifest.json").read_text())
            types = {
                c["name"]: c["type"]
                for c in manifest["tables"]["correlations"]["columns"]
            }
            self.assertEqual(types["correlation"], "number")

    def test_mixed_snapshots_missing_provenance_and_unknown_quality_rejected(self):
        metadata, source = fixture_tables()
        tables = {
            name: [
                {k: "" if v is None else str(v) for k, v in row.items()} for row in rows
            ]
            for name, rows in source.items()
        }
        tables["publications"] = metadata
        tables["relationships"][0]["serving_snapshot_id"] = "different-snapshot"
        with self.assertRaisesRegex(ValueError, "mixed publication"):
            _validate_relations(tables)
        minimal = {
            "publications": [
                {"publication_name": "quality", "serving_snapshot_id": "q"}
            ],
            "revision_quality": [
                {
                    "publication_name": "quality",
                    "serving_snapshot_id": "q",
                    "details_quality_status": "unknown",
                    "details_avg_revision_count": "0",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "unknown quality"):
            _validate_relations(minimal)
        with tempfile.TemporaryDirectory() as root:
            metadata, source = fixture_tables()
            source["provenance"].pop()
            with (
                patch(
                    "market_atlas.reporting.export.fixture_tables",
                    return_value=(metadata, source),
                ),
                self.assertRaisesRegex(ValueError, "provenance"),
            ):
                export_pack(Path(root))

    def test_report_config_requires_report_role_and_secret_safe_errors(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.toml"
            path.write_text(
                '[report_database]\nhost="localhost"\nport=5432\ndatabase="example"\nusername="report"\npassword="test-only"\n'
            )
            self.assertEqual(
                load_report_database(path).role, "marketatlas_report_reader"
            )
            path.write_text(path.read_text() + 'role="marketatlas_writer"\n')
            with self.assertRaises(ConfigError) as caught:
                load_report_database(path)
            self.assertNotIn("test-only", str(caught.exception))

    def test_published_reads_pin_once_and_enforce_bound(self):
        class Cursor:
            def __init__(self):
                self.calls = []

            def execute(self, query, params):
                self.calls.append((query, params))
                if "current_snapshot_metadata" in query:
                    self.description = [
                        SimpleNamespace(name=k)
                        for k in ("publication_name", "serving_snapshot_id")
                    ]
                    self.rows = [("synthetic_fixture", "pinned-before-concurrent-publication")]
                else:
                    self.description = [SimpleNamespace(name="node_id")]
                    self.rows = [("node1",), ("node2",)]

            def fetchall(self):
                return self.rows

        cursor = Cursor()
        _, tables = _read_cursor(cursor, ["synthetic_fixture"], 2)
        self.assertEqual(len(tables), 5)
        self.assertEqual(
            sum("current_snapshot_metadata" in q for q, _ in cursor.calls), 1
        )
        for query, params in cursor.calls[1:]:
            self.assertIn("WHERE serving_snapshot_id = %s", query)
            self.assertEqual(params, ("pinned-before-concurrent-publication", 3))
            self.assertIn("atlas_report.", query)
        with self.assertRaisesRegex(ValueError, "max_rows"):
            _read_cursor(Cursor(), ["synthetic_fixture"], 1)
        with self.assertRaises(ValueError):
            read_published(None, ["not_an_allowed_table"])

    def test_database_transaction_is_read_only_and_repeatable(self):
        from unittest.mock import MagicMock

        module = MagicMock()
        config = MagicMock()
        config.connection_kwargs.return_value = {}
        connection = module.connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        with (
            patch.dict("sys.modules", psycopg=module),
            patch("market_atlas.reporting.export._read_cursor", return_value=([], {})),
        ):
            read_published(config, ["synthetic_fixture"])
        queries = [c.args[0] for c in cursor.execute.call_args_list]
        self.assertEqual(
            queries,
            [
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
                "SET LOCAL ROLE marketatlas_report_reader",
            ],
        )
        self.assertIn(
            "default_transaction_read_only=on",
            module.connect.call_args.kwargs["options"],
        )

    @unittest.skipUnless(
        os.environ.get("MARKETATLAS_TEST_DATABASE") == "1",
        "opt-in report-only database read",
    )
    def test_live_all_publications_are_exported_without_writes(self):
        with tempfile.TemporaryDirectory() as root:
            result = export_pack(
                Path(root),
                config=load_target_database(),
                publications=(
                    "synthetic_fixture",
                    "macro_economic_graph",
                    "macro_context",
                    "macro_revision_quality",
                ),
            )
            self.assertEqual(validate_pack(Path(result["pack"]))["status"], "valid")


if __name__ == "__main__":
    unittest.main()
