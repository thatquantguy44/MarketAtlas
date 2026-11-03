import json
import tempfile
import unittest
from pathlib import Path

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.securities_finance.adapters import read_input_pack
from market_atlas.securities_finance.contracts import ContractError
from market_atlas.securities_finance.fixtures import write_fixture_inputs

SETTINGS = Path(__file__).resolve().parents[1] / "specs/001/settings.example.toml"


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.path = write_fixture_inputs(cls.temporary.name, settings_path=SETTINGS)
        cls.pack = read_input_pack(cls.path)

    def manifest(self, change):
        original = (self.path / "manifest.json").read_bytes()
        self.addCleanup((self.path / "manifest.json").write_bytes, original)
        manifest = json.loads(original)
        change(manifest)
        manifest["manifest_id"] = sha256(
            {k: v for k, v in manifest.items() if k != "manifest_id"}
        )
        (self.path / "manifest.json").write_bytes(canonical_bytes(manifest))
        return read_input_pack(self.path)

    def test_explicit_boundaries_and_legacy_packs(self):
        self.assertEqual(5, len(self.pack.manifest["event_boundaries"]))
        legacy = self.manifest(lambda m: m.pop("event_boundaries"))
        self.assertNotIn("event_boundaries", legacy.manifest)
        self.assertNotEqual(self.pack.semantic_identity, legacy.semantic_identity)

    def test_boundaries_reject_bad_identity_and_completeness(self):
        for field, value in (
            ("target_version_id", "missing"),
            ("state_component", "other"),
            ("complete", "true"),
            ("event_stream_id", "other"),
            ("snapshot_as_of", "2026-11-03"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ContractError):
                    self.manifest(
                        lambda m: m["event_boundaries"][0].update({field: value})
                    )
                # Each attempted rewrite must start with the original manifest.
                self.doCleanups()

    def test_duplicate_boundary_is_rejected(self):
        with self.assertRaises(ContractError) as error:
            self.manifest(
                lambda m: m["event_boundaries"].append(m["event_boundaries"][0])
            )
        self.assertEqual("duplicate_event_boundary", error.exception.code)


if __name__ == "__main__":
    unittest.main()
