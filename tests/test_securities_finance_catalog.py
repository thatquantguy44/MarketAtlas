import tomllib
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from market_atlas.contracts import sha256, validate_fixture
from market_atlas.fixtures import build_fixture
from market_atlas.graph.fixture_loader import stable_id
from market_atlas.securities_finance.catalog import (
    ReferenceCatalog,
    build_reference_catalog,
)
from market_atlas.securities_finance.contracts import ContractError, QuantityValue


class ReferenceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = build_reference_catalog()

    def test_catalog_is_deterministic_and_base_fixture_hash_and_meanings_are_unchanged(
        self,
    ):
        self.assertEqual(self.catalog, build_reference_catalog())
        self.assertEqual(5, len(self.catalog.instruments))
        fixture = build_fixture()
        self.assertEqual([], validate_fixture(fixture))
        self.assertEqual(
            "15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da",
            sha256(fixture),
        )
        rows = {row["id"]: row for row in fixture["entities"]}
        expected_ids = {
            "I-A": "a196d17b-6b6c-5444-a123-b8f1f77c43bb",
            "I-B": "0c976a19-fa42-50f0-91bb-2e9c6cbc88a4",
            "I-C": "dd0c6a9a-4b64-54f4-8308-8b77d3e455e7",
        }
        for source_id, expected_id in expected_ids.items():
            reference = self.catalog.instrument(expected_id)
            self.assertEqual(rows[source_id]["label"], reference.label)
            self.assertEqual("equity", reference.asset_class)
            self.assertEqual(rows[source_id]["type"], reference.node_type)
        for source_id in ("SF-BOND-A", "SF-BOND-B"):
            self.assertNotIn(source_id, rows)
            reference = self.catalog.instrument(str(stable_id("node", source_id)))
            self.assertEqual(f"fixture:{source_id}", reference.canonical_key)
            self.assertEqual("fixed_income", reference.asset_class)
            self.assertTrue(
                reference.provenance_reference.startswith("secfin-reference-v1:")
            )

    def test_fixture_conventions_match_the_design_settings(self):
        path = Path(__file__).resolve().parents[1] / "specs/001/settings.example.toml"
        cfg = tomllib.loads(path.read_text())
        for row in cfg["quantity"]["fixed_income"]:
            convention = self.catalog.convention(row["convention_id"])
            self.assertEqual(
                str(stable_id("node", row["source_instrument_id"])),
                convention.instrument_node_id,
            )
            for key in (
                "quantity_unit",
                "quantity_currency",
                "quantity_precision",
                "minimum_allocation",
                "allocation_increment",
                "increment_origin",
                "minimum_scope",
            ):
                self.assertEqual(row[key], getattr(convention, key))
        for convention in self.catalog.conventions[:3]:
            for key, value in cfg["quantity"]["equity"].items():
                if key == "convention_id":
                    self.assertTrue(convention.convention_id.startswith(value + ":"))
                else:
                    self.assertEqual(value, getattr(convention, key))

    def test_unknown_references_are_rejected_without_catalog_mutation(self):
        before = (self.catalog.instruments, self.catalog.conventions)
        for node, convention in [
            (str(stable_id("node", "MISSING")), "bond-a-v1"),
            (self.catalog.instruments[0].instrument_node_id, "missing"),
        ]:
            with (
                self.subTest(node=node, convention=convention),
                self.assertRaises(ContractError),
            ):
                self.catalog.validate_quantity(
                    node, convention, QuantityValue("2000", "nominal", "USD", 0)
                )
        self.assertEqual(before, (self.catalog.instruments, self.catalog.conventions))

    def test_quantity_binding_never_crosses_instrument_or_currency(self):
        bond = self.catalog.convention("bond-a-v1")
        value = QuantityValue("2000", "nominal", "USD", 0)
        self.assertEqual(
            2000,
            self.catalog.validate_quantity(
                bond.instrument_node_id, bond.convention_id, value, for_allocation=True
            ),
        )
        with self.assertRaisesRegex(ContractError, "instrument_convention_mismatch"):
            self.catalog.validate_quantity(bond.instrument_node_id, "bond-b-v1", value)
        with self.assertRaisesRegex(ContractError, "quantity_convention_mismatch"):
            self.catalog.validate_quantity(
                bond.instrument_node_id,
                bond.convention_id,
                replace(value, quantity_currency="EUR"),
            )

    def test_wrong_node_types_ids_and_missing_provenance_cannot_enter_catalog(self):
        reference = self.catalog.instruments[0]
        for changes in [
            {"node_type": "listing"},
            {"instrument_node_id": "I-A"},
            {"asset_class": "bond"},
            {"provenance_reference": ""},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(reference, **changes)

    def test_duplicate_ids_and_keys_and_unmapped_conventions_are_rejected(self):
        reference = self.catalog.instruments[0]
        for duplicate in [
            reference,
            replace(reference, canonical_key="other:key"),
            replace(reference, instrument_node_id=str(stable_id("node", "other"))),
        ]:
            with (
                self.subTest(duplicate=duplicate),
                self.assertRaisesRegex(ContractError, "duplicate_instrument"),
            ):
                replace(
                    self.catalog, instruments=self.catalog.instruments + (duplicate,)
                )
        with self.assertRaisesRegex(ContractError, "duplicate_convention"):
            replace(
                self.catalog,
                conventions=self.catalog.conventions + (self.catalog.conventions[0],),
            )
        with self.assertRaisesRegex(ContractError, "unknown_instrument"):
            replace(
                self.catalog,
                conventions=(
                    replace(self.catalog.conventions[0], instrument_node_id="missing"),
                ),
            )
        with self.assertRaisesRegex(ContractError, "asset_unit_mismatch"):
            replace(
                self.catalog,
                conventions=(
                    replace(
                        self.catalog.conventions[-1],
                        instrument_node_id=reference.instrument_node_id,
                    ),
                ),
            )

    def test_catalog_containers_are_immutable_and_schema_and_classification_are_explicit(
        self,
    ):
        with self.assertRaises(FrozenInstanceError):
            self.catalog.classification = "live"
        for changes in [
            {"schema_version": 2},
            {"schema_version": True},
            {"classification": "live"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.catalog, **changes)
        with self.assertRaisesRegex(ContractError, "invalid_catalog"):
            ReferenceCatalog(list(self.catalog.instruments), self.catalog.conventions)


if __name__ == "__main__":
    unittest.main()
