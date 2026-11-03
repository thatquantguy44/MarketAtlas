import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.fixtures import build_fixture
from market_atlas.securities_finance.adapters import (
    decode_table,
    encode_table,
    read_input_pack,
)
from market_atlas.securities_finance.contracts import ContractError
from market_atlas.securities_finance.fixtures import write_fixture_inputs
from market_atlas.securities_finance.records import normalize_rows

SETTINGS = Path(__file__).resolve().parents[1] / "specs/001/settings.example.toml"


class FixtureInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.json_path = write_fixture_inputs(cls.root / "json", settings_path=SETTINGS)
        cls.csv_path = write_fixture_inputs(
            cls.root / "csv", settings_path=SETTINGS, selected_format="csv"
        )
        cls.net_path = write_fixture_inputs(
            cls.root / "net", settings_path=SETTINGS, balance_basis="net_available"
        )

    def setUp(self):
        self.case = tempfile.TemporaryDirectory()
        self.addCleanup(self.case.cleanup)
        self.path = Path(self.case.name) / "pack"
        shutil.copytree(self.json_path, self.path)
        self.manifest = json.loads((self.path / "manifest.json").read_bytes())

    def save(self):
        self.manifest["manifest_id"] = sha256(
            {k: v for k, v in self.manifest.items() if k != "manifest_id"}
        )
        (self.path / "manifest.json").write_bytes(canonical_bytes(self.manifest))

    def dataset(self, name):
        return next(
            item for item in self.manifest["datasets"] if item["record_type"] == name
        )

    def reset_case(self):
        shutil.rmtree(self.path)
        shutil.copytree(self.json_path, self.path)
        self.manifest = json.loads((self.path / "manifest.json").read_bytes())

    def rewrite_settings(self, transform):
        entry = self.manifest["settings_file"]
        raw = transform((self.path / entry["path"]).read_bytes())
        (self.path / entry["path"]).write_bytes(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        self.save()

    def rewrite(self, name, change, formats=("json", "csv")):
        for entry in self.dataset(name)["files"]:
            if entry["format"] not in formats:
                continue
            rows = list(
                decode_table(
                    name, (self.path / entry["path"]).read_bytes(), entry["format"]
                )
            )
            change(rows)
            raw = encode_table(name, rows, entry["format"])
            (self.path / entry["path"]).write_bytes(raw)
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
        self.save()

    def test_deterministic_bytes_reuse_and_no_public_fixture_changes(self):
        before = {
            path.relative_to(self.json_path): path.read_bytes()
            for path in self.json_path.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            self.json_path,
            write_fixture_inputs(self.root / "json", settings_path=SETTINGS),
        )
        self.assertEqual(
            before,
            {
                path.relative_to(self.json_path): path.read_bytes()
                for path in self.json_path.rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(
            "15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da",
            sha256(build_fixture()),
        )
        self.assertFalse(list((self.root / "json").glob(".sf-input-*")))

    def test_both_authorities_have_equal_business_identity_and_distinct_provenance(
        self,
    ):
        json_pack, csv_pack = (
            read_input_pack(self.json_path),
            read_input_pack(self.csv_path),
        )
        self.assertNotEqual(json_pack.manifest_id, csv_pack.manifest_id)
        self.assertEqual(json_pack.semantic_identity, csv_pack.semantic_identity)
        self.assertEqual(17, len(json_pack.tables))
        count = sum(len(rows) for rows in json_pack.tables.values())
        self.assertEqual(95, count)
        self.assertEqual(count, len(json_pack.provenance))
        self.assertEqual(count, len(csv_pack.provenance))
        self.assertEqual({"json"}, {row.format for row in json_pack.provenance})
        self.assertEqual({"csv"}, {row.format for row in csv_pack.provenance})
        for name in json_pack.tables:
            self.assertEqual(
                [row.to_row(semantic=True) for row in json_pack.tables[name]],
                [row.to_row(semantic=True) for row in csv_pack.tables[name]],
            )

    def test_gross_net_and_unknown_zero_are_explicit_source_facts(self):
        gross, net = read_input_pack(self.json_path), read_input_pack(self.net_path)
        self.assertNotEqual(gross.semantic_identity, net.semantic_identity)

        def positions(pack):
            return {
                row.payload["position_id"]: row
                for row in pack.tables["inventory_position"]
                if row.envelope.key.version_id.endswith(":v1")
            }

        g, n = positions(gross), positions(net)
        self.assertEqual("80000", g["sf:position:coverage-b"].payload["quantity"])
        self.assertEqual("30000", n["sf:position:coverage-b"].payload["quantity"])
        self.assertEqual("0", g["sf:position:bond-zero"].payload["quantity"])
        self.assertIsNone(g["sf:position:bond-unknown"].payload["quantity"])
        self.assertFalse(
            gross.tables["deduction_contract"][0].payload[
                "reservations_already_deducted"
            ]
        )
        self.assertTrue(
            net.tables["deduction_contract"][0].payload["reservations_already_deducted"]
        )
        self.assertEqual(
            "50000", net.tables["capacity_component"][0].payload["quantity"]
        )

    def test_versions_date_precision_quotes_and_events_are_retained_not_applied(self):
        pack = read_input_pack(self.json_path)
        old = [
            row
            for row in pack.tables["inventory_position"]
            if row.payload["position_id"] == "sf:position:coverage-a"
        ]
        self.assertEqual({"55000", "60000"}, {row.payload["quantity"] for row in old})
        self.assertEqual(7, len(pack.tables["lifecycle_event"]))
        self.assertEqual(2, len(pack.tables["snapshot_included_events"]))
        self.assertEqual(
            "20000", pack.tables["loan"][0].payload["outstanding_quantity"]
        )
        self.assertEqual(
            "date", pack.tables["agreement"][0].envelope.source_available_at.precision
        )
        self.assertIsNone(
            pack.tables["agreement"][0].envelope.source_available_at.as_utc()
        )
        self.assertEqual(
            "date",
            pack.tables["borrow_request"][0].payload["request_order_at"].precision,
        )
        self.assertIn(
            '"One"\nDesk — α', pack.tables["legal_entity"][-1].payload["label"]
        )
        self.assertTrue(
            any(
                row.payload["permission_state"] is None
                for row in pack.tables["agreement_parties"]
            )
        )

        future = next(
            row
            for row in pack.tables["lifecycle_event"]
            if row.payload["event_id"] == "sf:event:future-return"
        )
        from market_atlas.securities_finance.contracts import TimestampEvidence

        self.assertGreater(
            future.envelope.source_available_at.as_utc(),
            TimestampEvidence(
                pack.manifest["cutoffs"]["knowledge_cutoff"], "instant"
            ).as_utc(),
        )

    def test_input_objects_are_deeply_immutable(self):
        pack = read_input_pack(self.json_path)
        with self.assertRaises(TypeError):
            pack.settings["solver"]["adapter"] = "other"
        with self.assertRaises(TypeError):
            pack.tables["inventory_position"][0].payload["quantity"] = "0"
        with self.assertRaises(TypeError):
            pack.manifest["datasets"][0]["selected_format"] = "csv"

    def test_valid_but_different_alternative_representation_is_rejected(self):
        self.rewrite(
            "inventory_position",
            lambda rows: rows[0].update(quantity="61000"),
            formats=("csv",),
        )
        with self.assertRaisesRegex(ContractError, "representation_mismatch"):
            read_input_pack(self.path)

    def test_hash_and_manifest_tampering_are_rejected(self):
        (self.path / self.dataset("legal_entity")["files"][1]["path"]).write_bytes(
            b"tampered"
        )
        with self.assertRaisesRegex(ContractError, "hash_mismatch"):
            read_input_pack(self.path)
        self.manifest["classification"] = "changed-without-rehash"
        (self.path / "manifest.json").write_bytes(canonical_bytes(self.manifest))
        with self.assertRaises(ContractError):
            read_input_pack(self.path)

    def test_duplicate_logical_datasets_and_physical_representations_are_rejected(self):
        self.manifest["datasets"][1]["logical_dataset_id"] = self.manifest["datasets"][
            0
        ]["logical_dataset_id"]
        self.save()
        with self.assertRaisesRegex(ContractError, "duplicate_dataset"):
            read_input_pack(self.path)
        self.manifest["datasets"][1]["logical_dataset_id"] = "restored"
        self.manifest["datasets"][0]["files"][1]["format"] = "json"
        self.save()
        with self.assertRaisesRegex(ContractError, "duplicate_representation"):
            read_input_pack(self.path)

    def test_unknown_schema_fields_and_unsafe_paths_are_rejected(self):
        for path in (
            "../outside.json",
            "/outside.json",
            "C:\\outside.json",
            "json//instrument_catalog.json",
        ):
            with self.subTest(path=path):
                self.dataset("instrument_catalog")["files"][0]["path"] = path
                self.save()
                with self.assertRaisesRegex(ContractError, "invalid_path"):
                    read_input_pack(self.path)

    def test_duplicate_conflicting_versions_are_not_added_as_supply(self):
        self.rewrite(
            "inventory_position", lambda rows: rows.append({**rows[0], "quantity": "1"})
        )
        with self.assertRaisesRegex(ContractError, "duplicate_record_key"):
            read_input_pack(self.path)

    def test_broken_foreign_keys_and_included_event_scope_fail(self):
        self.rewrite(
            "agreement_parties",
            lambda rows: rows[0].update(agreement_version_id="sf:missing:v1"),
        )
        with self.assertRaisesRegex(ContractError, "unknown_reference"):
            read_input_pack(self.path)

    def test_unknown_quantity_conventions_and_instrument_mismatches_fail(self):
        self.rewrite(
            "inventory_position", lambda rows: rows[0].update(convention_id="bond-a-v1")
        )
        with self.assertRaisesRegex(ContractError, "instrument_convention_mismatch"):
            read_input_pack(self.path)

    def test_comments_and_record_order_change_physical_identity_not_business_identity(
        self,
    ):
        before = read_input_pack(self.path)
        for name in ("inventory_position", "legal_entity"):
            self.rewrite(name, lambda rows: rows.reverse())
        entry = self.manifest["settings_file"]
        raw = (
            self.path / entry["path"]
        ).read_bytes() + b"\n# physically different, same settings\n"
        (self.path / entry["path"]).write_bytes(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        self.manifest["datasets"].reverse()
        self.save()
        after = read_input_pack(self.path)
        self.assertNotEqual(before.manifest_id, after.manifest_id)
        self.assertEqual(before.semantic_identity, after.semantic_identity)

    def test_workload_and_settings_policy_fail_before_pack_is_returned(self):
        entry = self.manifest["settings_file"]
        raw = (
            (self.path / entry["path"])
            .read_bytes()
            .replace(b"max_positions = 100", b"max_positions = 1")
        )
        (self.path / entry["path"]).write_bytes(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        self.save()
        with self.assertRaisesRegex(ContractError, "workload_exceeded"):
            read_input_pack(self.path)

    def test_failed_staging_preserves_existing_pack(self):
        before = {
            p.relative_to(self.json_path): p.read_bytes()
            for p in self.json_path.rglob("*")
            if p.is_file()
        }
        with patch(
            "market_atlas.securities_finance.fixtures.read_input_pack",
            side_effect=ContractError("injected", "failure"),
        ):
            with self.assertRaisesRegex(ContractError, "injected"):
                write_fixture_inputs(self.root / "json", settings_path=SETTINGS)
        self.assertEqual(
            before,
            {
                p.relative_to(self.json_path): p.read_bytes()
                for p in self.json_path.rglob("*")
                if p.is_file()
            },
        )
        self.assertFalse(list((self.root / "json").glob(".sf-input-*")))

    def test_domain_invalid_values_fail_through_each_format_independently(self):
        pack = read_input_pack(self.json_path)
        mutations = [
            ("quantity", "1.5"),
            ("quantity", "-1"),
            ("quantity", "NaN"),
            ("quantity", ""),
            ("balance_basis", "unknown"),
            ("ready_date", "2026-02-30"),
            ("recorded_from_value", None),
            ("source_available_at_value", "2026-11-03T12:00:00"),
        ]
        for field, value in mutations:
            codes = []
            for format in ("json", "csv"):
                with self.subTest(field=field, value=value, format=format):
                    entry = next(
                        item
                        for item in self.dataset("inventory_position")["files"]
                        if item["format"] == format
                    )
                    rows = list(
                        decode_table(
                            "inventory_position",
                            (self.path / entry["path"]).read_bytes(),
                            format,
                        )
                    )
                    rows[0][field] = value
                    decoded = decode_table(
                        "inventory_position",
                        encode_table("inventory_position", rows, format),
                        format,
                    )
                    with self.assertRaises(ContractError) as raised:
                        normalize_rows(
                            "inventory_position", decoded, "sf", catalog=pack.catalog
                        )
                    codes.append(raised.exception.code)
            self.assertEqual(codes[0], codes[1])

    def test_broken_payload_links_scopes_and_event_transitions_fail(self):
        cases = [
            ("snapshot_included_events", "event_id", "sf:event:missing"),
            ("lifecycle_event", "state_component", "loan_outstanding"),
            ("loan_allocation", "loan_id", "sf:loan:missing"),
            ("borrow_request", "input_kind", "outstanding_loan"),
            ("inventory_position", "snapshot_id", "sf:snapshot:other"),
            ("inventory_position", "source_name", "different-source"),
            ("instrument_catalog", "node_type", "listing"),
            ("quantity_convention", "quantity_precision", 1),
        ]
        for table, field, value in cases:
            with self.subTest(table=table, field=field):
                self.reset_case()
                self.rewrite(
                    table,
                    lambda rows, field=field, value=value: rows[0].update(
                        {field: value}
                    ),
                )
                with self.assertRaises(ContractError):
                    read_input_pack(self.path)

    def test_provided_coefficients_preserve_signed_values_and_reject_invalid_basis_or_horizon(
        self,
    ):
        pack = read_input_pack(self.json_path)
        self.assertTrue(
            any(
                row.payload["net_benefit_amount"] == "-0.250000"
                for row in pack.tables["net_benefit"]
            )
        )
        cases = [
            ("basis_quantity", "0"),
            ("basis_quantity", "3"),
            ("currency", "EUR"),
            ("horizon_id", "different"),
            ("horizon_end", "2026-11-01T12:00:00Z"),
            ("net_benefit_amount", "NaN"),
            ("net_benefit_amount", None),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.reset_case()
                self.rewrite(
                    "net_benefit",
                    lambda rows, field=field, value=value: rows[0].update(
                        {field: value}
                    ),
                )
                with self.assertRaises(ContractError):
                    read_input_pack(self.path)

    def test_toml_settings_are_consumed_and_not_just_copied(self):
        settings = Path(self.case.name) / "custom.toml"
        settings.write_bytes(
            SETTINGS.read_bytes().replace(
                b'minimum_allocation = "1500"', b'minimum_allocation = "2500"'
            )
        )
        path = write_fixture_inputs(
            Path(self.case.name) / "custom", settings_path=settings
        )
        custom = read_input_pack(path)
        self.assertEqual(2500, custom.catalog.convention("bond-b-v1").minimum_units)
        self.assertNotEqual(
            read_input_pack(self.json_path).semantic_identity, custom.semantic_identity
        )

    def test_bad_settings_and_unknown_profile_terms_fail_explicitly(self):
        for old, new in [
            (b"schema_version = 1", b"schema_version = true"),
            (b'"source_fresh"', b'"execute_python"'),
            (b'adapter = "scipy_highs_milp"', b'adapter = "unreviewed"'),
            (b'weight = "0.75"', b'weight = "NaN"'),
            (b'scale_amount = "100.000000"', b'scale_amount = "0"'),
            (b"source_confirmed_at", b"file_modification_time"),
        ]:
            with self.subTest(new=new):
                self.reset_case()
                self.rewrite_settings(
                    lambda raw, old=old, new=new: raw.replace(old, new)
                )
                with self.assertRaises(ContractError):
                    read_input_pack(self.path)

    def test_unknown_and_missing_manifest_fields_and_wrong_cutoff_fail(self):
        for change in [
            lambda m: m.update(schema_version=True),
            lambda m: m.update(extra="ignored?"),
            lambda m: m.pop("instrument_catalog"),
            lambda m: m["cutoffs"].update(knowledge_cutoff="2026-11-03T11:00:00Z"),
        ]:
            with self.subTest(change=change):
                self.reset_case()
                change(self.manifest)
                self.save()
                with self.assertRaises(ContractError):
                    read_input_pack(self.path)

    def test_symlinks_cannot_escape_input_pack_and_missing_files_fail(self):
        entry = self.dataset("instrument_catalog")["files"][0]
        target = self.path / entry["path"]
        outside = Path(self.case.name) / "outside.json"
        target.rename(outside)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ContractError, "invalid_path"):
            read_input_pack(self.path)
        target.unlink()
        with self.assertRaisesRegex(ContractError, "missing_input_file"):
            read_input_pack(self.path)

    def test_common_event_version_labels_are_source_and_event_scoped(self):
        self.rewrite(
            "lifecycle_event",
            lambda rows: [row.update(version_id="v1") for row in rows],
        )
        self.rewrite(
            "snapshot_included_events",
            lambda rows: [row.update(event_version_id="v1") for row in rows],
        )
        pack = read_input_pack(self.path)
        self.assertEqual(7, len(pack.tables["lifecycle_event"]))
        self.assertEqual(2, len(pack.tables["snapshot_included_events"]))

    def test_empty_optional_fact_tables_are_retained_without_invented_values(self):
        self.rewrite("net_benefit", lambda rows: rows.clear())
        self.rewrite("agreement_parties", lambda rows: rows.clear())
        pack = read_input_pack(self.path)
        self.assertEqual((), pack.tables["net_benefit"])
        self.assertEqual((), pack.tables["agreement_parties"])
        self.assertEqual(11, len(pack.tables["inventory_position"]))

    def test_existing_tampered_directory_is_never_overwritten_as_a_repair(self):
        output = Path(self.case.name) / "repeat"
        path = write_fixture_inputs(output, settings_path=SETTINGS)
        manifest = json.loads((path / "manifest.json").read_bytes())
        file = path / manifest["datasets"][0]["files"][0]["path"]
        file.write_bytes(b"tampered")
        with self.assertRaisesRegex(ContractError, "hash_mismatch"):
            write_fixture_inputs(output, settings_path=SETTINGS)
        self.assertEqual(b"tampered", file.read_bytes())
        self.assertFalse(list(output.glob(".sf-input-*")))

    def test_mixed_table_authorities_still_load_each_record_once(self):
        before = read_input_pack(self.path)
        self.dataset("inventory_position")["selected_format"] = "csv"
        self.save()
        after = read_input_pack(self.path)
        self.assertEqual(before.semantic_identity, after.semantic_identity)
        self.assertEqual(95, len(after.provenance))
        self.assertEqual(
            {"csv"},
            {
                item.format
                for item in after.provenance
                if item.record_type == "inventory_position"
            },
        )

    def test_record_provenance_resolves_to_selected_hashed_physical_records(self):
        pack = read_input_pack(self.path)
        for location in pack.provenance:
            rows = decode_table(
                location.record_type,
                (self.path / location.path).read_bytes(),
                location.format,
            )
            raw = rows[location.record_number - 1]
            normalized = pack.tables[location.record_type][location.record_number - 1]
            self.assertEqual(raw, normalized.to_row())
            self.assertEqual(
                hashlib.sha256((self.path / location.path).read_bytes()).hexdigest(),
                location.sha256,
            )


if __name__ == "__main__":
    unittest.main()
