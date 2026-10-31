"""Check native report bindings against a real exported fixture contract."""

import json
import tempfile
import unittest
from pathlib import Path

from market_atlas.reporting.export import export_pack
from market_atlas.reporting.project import build_project


class ReportProjectTests(unittest.TestCase):
    def test_every_visual_and_relationship_binds_to_existing_model_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = Path(export_pack(root / "packs")["pack"])
            result = build_project(pack, root / "project")
            model = json.loads(
                (root / "project/MarketAtlas.SemanticModel/model.bim").read_text()
            )["model"]
            tables = {table["name"]: table for table in model["tables"]}
            self.assertEqual(result["pages"], 5)
            self.assertEqual(len(list((root / "project").rglob("page.json"))), 5)
            for path in (root / "project").rglob("visual.json"):
                query = json.loads(path.read_text())["visual"]["query"]["queryState"]
                for role in query.values():
                    for projection in role["projections"]:
                        kind, field = next(iter(projection["field"].items()))
                        table = tables[field["Expression"]["SourceRef"]["Entity"]]
                        collection = "measures" if kind == "Measure" else "columns"
                        self.assertIn(
                            field["Property"],
                            {item["name"] for item in table[collection]},
                            str(path),
                        )
            for rel in model["relationships"]:
                self.assertEqual(rel["crossFilteringBehavior"], "oneDirection")
                for end in ("from", "to"):
                    self.assertIn(
                        rel[end + "Column"],
                        {c["name"] for c in tables[rel[end + "Table"]]["columns"]},
                    )
            self.assertNotEqual(
                tables["SourceNode"]["name"], tables["TargetNode"]["name"]
            )
            self.assertIn(
                "HASONEVALUE",
                next(
                    m["expression"]
                    for m in tables["correlations"]["measures"]
                    if m["name"] == "Correlation"
                ),
            )
            self.assertEqual(list((root / "project").rglob("*.csv")), [])
            self.assertIn(
                "DateTimeZone.ToUtc",
                tables["provenance"]["partitions"][0]["source"]["expression"],
            )
            self.assertEqual(
                json.loads((root / "project/project-manifest.json").read_text())[
                    "validation"
                ],
                "source_only_powerbi_execution_required",
            )

    def test_tampered_pack_and_existing_project_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = Path(export_pack(root / "packs")["pack"])
            build_project(pack, root / "project")
            original = (root / "project/MarketAtlas.pbip").read_bytes()
            with self.assertRaises(FileExistsError):
                build_project(pack, root / "project")
            self.assertEqual((root / "project/MarketAtlas.pbip").read_bytes(), original)
            (pack / "nodes.csv").write_text("corrupt")
            with self.assertRaises(ValueError):
                build_project(pack, root / "bad-project")
            self.assertFalse((root / "bad-project").exists())
