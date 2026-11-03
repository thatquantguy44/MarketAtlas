import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.securities_finance.adapters import (
    decode_table,
    encode_table,
    read_input_pack,
)
from market_atlas.securities_finance.contracts import ContractError, TimestampEvidence
from market_atlas.securities_finance.events import reconcile_events
from market_atlas.securities_finance.fixtures import write_fixture_inputs
from market_atlas.securities_finance.selection import select_input_pack
from market_atlas.securities_finance.temporal import Cutoffs

SETTINGS = Path(__file__).resolve().parents[1] / "specs/001/settings.example.toml"


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.path = write_fixture_inputs(cls.temporary.name, settings_path=SETTINGS)
        cls.pack = read_input_pack(cls.path)

    def changed_event(self, event_id, transform, *, append=False, pack=None):
        pack = self.pack if pack is None else pack
        tables = dict(pack.tables)
        rows = list(tables["lifecycle_event"])
        index = next(
            i
            for i, row in enumerate(rows)
            if row.payload["event_id"] == f"sf:event:{event_id}"
        )
        changed = transform(rows[index])
        if append:
            rows.append(changed)
        else:
            rows[index] = changed
        tables["lifecycle_event"] = tuple(rows)
        return replace(pack, tables=tables)

    def later(self):
        return Cutoffs.from_mapping(
            dict.fromkeys(
                ("business_as_of", "knowledge_cutoff", "system_cutoff"),
                "2026-11-03T12:30:00Z",
            )
        )

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
                        lambda m, field=field, value=value: m["event_boundaries"][
                            0
                        ].update({field: value})
                    )
                # Each attempted rewrite must start with the original manifest.
                self.doCleanups()

    def test_duplicate_boundary_is_rejected(self):
        with self.assertRaises(ContractError) as error:
            self.manifest(
                lambda m: m["event_boundaries"].append(m["event_boundaries"][0])
            )
        self.assertEqual("duplicate_event_boundary", error.exception.code)

    def test_current_facts_select_without_applying_events(self):
        selected = select_input_pack(self.pack)
        self.assertEqual(10, len(selected.tables["inventory_position"]))
        self.assertEqual(3, len(selected.tables["lifecycle_event"]))
        self.assertEqual(95, len(selected.decisions))
        old = next(
            d
            for d in selected.decisions
            if d.record.envelope
            and d.record.envelope.key.version_id == "sf:position:coverage-a:v0"
        )
        self.assertEqual("excluded", old.status)
        position = next(
            r
            for r in selected.tables["inventory_position"]
            if r.payload["position_id"] == "sf:position:coverage-a"
        )
        self.assertEqual("60000", position.payload["quantity"])
        self.assertEqual([-1, -1], [o.relation for o in selected.request_order])

    def test_snapshot_coverage_blocks_legacy_and_incomplete_scopes(self):
        selected = select_input_pack(self.pack)
        self.assertFalse(reconcile_events(self.pack, selected).blocked_targets)
        legacy = self.manifest(lambda m: m.pop("event_boundaries"))
        self.assertEqual(
            5, len(reconcile_events(legacy, select_input_pack(legacy)).blocked_targets)
        )
        self.doCleanups()
        incomplete = self.manifest(
            lambda m: m["event_boundaries"][0].update(complete=False)
        )
        reasons = reconcile_events(
            incomplete, select_input_pack(incomplete)
        ).blocked_targets
        self.assertEqual([("incomplete_event_inclusion",)], list(reasons.values()))

    def test_snapshot_after_business_cutoff_cannot_be_rewound(self):
        selected = select_input_pack(self.pack)
        historical = replace(
            selected,
            cutoffs=replace(
                selected.cutoffs,
                business_as_of=Cutoffs.from_mapping(
                    {
                        "business_as_of": "2026-11-03T11:49:59Z",
                        "knowledge_cutoff": "2026-11-03T12:00:00Z",
                        "system_cutoff": "2026-11-03T12:00:00Z",
                    }
                ).business_as_of,
            ),
        )
        blocked = reconcile_events(self.pack, historical).blocked_targets
        self.assertEqual(5, len(blocked))
        self.assertTrue(
            all(
                "snapshot_after_business_cutoff" in reasons
                for reasons in blocked.values()
            )
        )

    def test_included_events_are_skipped_and_replay_is_idempotent(self):
        selected = select_input_pack(self.pack)
        plan = selected.event_plan
        self.assertEqual(
            2, sum(a.status == "already_included" for a in plan.assessments)
        )
        self.assertEqual(4, sum(a.status == "excluded" for a in plan.assessments))
        self.assertEqual(
            ["sf:event:recall"], [a.after.payload["event_id"] for a in plan.actions]
        )
        self.assertEqual(selected, select_input_pack(self.pack))
        self.assertEqual(7, len(self.pack.tables["lifecycle_event"]))
        with self.assertRaises(TypeError):
            plan.blocked_targets[("sf", "x", "y")] = ("bad",)

    def test_supported_returns_and_reversals_plan_once_without_changing_capacity(self):
        selected = select_input_pack(self.pack, cutoffs=self.later())
        plan = selected.event_plan
        self.assertFalse(plan.blocked_targets)
        self.assertEqual(5, len(plan.actions))
        self.assertEqual(3, sum(a.kind == "reversal" for a in plan.actions))
        allocation = next(
            r
            for r in selected.tables["loan_allocation"]
            if r.payload["allocation_id"] == "sf:allocation:two"
        )
        self.assertEqual("5000", allocation.payload["outstanding_quantity"])

    def test_late_unincluded_effect_blocks_only_affected_scope(self):
        tables = dict(self.pack.tables)
        tables["snapshot_included_events"] = tuple(
            r
            for r in tables["snapshot_included_events"]
            if r.payload["event_id"] != "sf:event:returned"
        )
        selected = select_input_pack(replace(self.pack, tables=tables))
        self.assertEqual(
            {("sf", "loan_outstanding", "sf:allocation:one")},
            set(selected.event_plan.blocked_targets),
        )
        self.assertIn(
            "late_or_ambiguous_unincluded_effect",
            next(iter(selected.event_plan.blocked_targets.values())),
        )
        self.assertEqual(1, len(selected.event_plan.actions))

    def test_date_only_event_withholds_affected_reconciliation(self):
        pack = self.changed_event(
            "recall",
            lambda r: replace(
                r,
                envelope=replace(
                    r.envelope,
                    effective_at=TimestampEvidence("2026-11-03", "date", "UTC"),
                ),
            ),
        )
        plan = select_input_pack(pack).event_plan
        self.assertEqual((), plan.actions)
        self.assertIn(
            ("sf", "recall_instruction", "sf:loan:covered"), plan.blocked_targets
        )

    def test_included_correction_replaces_old_effect_instead_of_adding_twice(self):
        def correction(row):
            return replace(
                row,
                payload={
                    **row.payload,
                    "quantity": "1200",
                    "supersedes_version_id": row.envelope.key.version_id,
                },
                envelope=replace(
                    row.envelope,
                    key=replace(row.envelope.key, version_id="sf:event:returned:v2"),
                ),
            )

        pack = self.changed_event("returned", correction, append=True)
        plan = select_input_pack(pack).event_plan
        self.assertFalse(plan.blocked_targets)
        replacement = next(a for a in plan.actions if a.kind == "replacement")
        self.assertEqual("1000", replacement.before.payload["quantity"])
        self.assertEqual("1200", replacement.after.payload["quantity"])
        self.assertEqual(2, len(plan.actions))

    def test_future_correction_does_not_hide_included_original(self):
        def correction(row):
            return replace(
                row,
                payload={
                    **row.payload,
                    "quantity": "1200",
                    "supersedes_version_id": row.envelope.key.version_id,
                },
                envelope=replace(
                    row.envelope,
                    key=replace(row.envelope.key, version_id="v2"),
                    source_available_at=TimestampEvidence(
                        "2026-11-03T12:01:00Z", "instant"
                    ),
                ),
            )

        plan = select_input_pack(
            self.changed_event("returned", correction, append=True)
        ).event_plan
        self.assertFalse(plan.blocked_targets)
        self.assertEqual(1, len(plan.actions))
        self.assertEqual(
            2, sum(a.status == "already_included" for a in plan.assessments)
        )

    def test_multiple_reversals_cannot_release_the_same_effect_twice(self):
        def duplicate(row):
            return replace(
                row,
                payload={**row.payload, "event_id": "sf:event:reverse-again"},
                envelope=replace(
                    row.envelope,
                    key=replace(
                        row.envelope.key,
                        record_id="sf:event:reverse-again",
                        version_id="v1",
                    ),
                ),
            )

        pack = self.changed_event("reverse-return", duplicate, append=True)
        plan = select_input_pack(pack, cutoffs=self.later()).event_plan
        scope = ("sf", "loan_outstanding", "sf:allocation:one")
        self.assertIn("multiple_reversals_of_same_effect", plan.blocked_targets[scope])
        self.assertTrue(
            all(a.after.payload["target_record_id"] != scope[-1] for a in plan.actions)
        )

    def test_json_csv_and_gross_net_selection_agree_with_separate_provenance(self):
        csv_path = write_fixture_inputs(
            Path(self.temporary.name) / "csv",
            settings_path=SETTINGS,
            selected_format="csv",
        )
        csv = select_input_pack(read_input_pack(csv_path))
        json_selection = select_input_pack(self.pack)
        self.assertEqual(json_selection.semantic_identity, csv.semantic_identity)
        self.assertEqual(json_selection.event_plan, csv.event_plan)
        self.assertNotEqual(json_selection.input_manifest_id, csv.input_manifest_id)
        self.assertEqual({"json"}, {p.format for p in json_selection.provenance})
        self.assertEqual({"csv"}, {p.format for p in csv.provenance})
        net_path = write_fixture_inputs(
            Path(self.temporary.name) / "net",
            settings_path=SETTINGS,
            balance_basis="net_available",
        )
        net = select_input_pack(read_input_pack(net_path))
        self.assertEqual(json_selection.event_plan, net.event_plan)
        self.assertNotEqual(json_selection.semantic_identity, net.semantic_identity)

    def test_fifo_uncertainty_is_exposed_without_claiming_a_safe_allocation(self):
        tables = dict(self.pack.tables)
        tables["borrow_request"] = tuple(
            replace(
                r,
                payload={
                    **r.payload,
                    "request_order_at": TimestampEvidence("2026-11-03", "date", "UTC"),
                },
            )
            if r.payload["request_id"] == "sf:request:balance-one"
            else r
            for r in tables["borrow_request"]
        )
        selected = select_input_pack(replace(self.pack, tables=tables))
        self.assertEqual(7, len(selected.tables["borrow_request"]))
        self.assertEqual(1, sum(o.relation is None for o in selected.request_order))

    def test_file_loaded_correction_retains_exact_original_effect(self):
        def change(manifest):
            dataset = next(
                d for d in manifest["datasets"] if d["record_type"] == "lifecycle_event"
            )
            for entry in dataset["files"]:
                path = self.path / entry["path"]
                original = path.read_bytes()
                self.addCleanup(path.write_bytes, original)
                rows = list(decode_table("lifecycle_event", original, entry["format"]))
                old = next(r for r in rows if r["event_id"] == "sf:event:returned")
                rows.append(
                    {
                        **old,
                        "version_id": "sf:event:returned:v2",
                        "supersedes_version_id": old["version_id"],
                        "quantity": "1200",
                    }
                )
                raw = encode_table("lifecycle_event", rows, entry["format"])
                path.write_bytes(raw)
                entry["sha256"] = hashlib.sha256(raw).hexdigest()

        selected = select_input_pack(self.manifest(change))
        replacement = next(
            a for a in selected.event_plan.actions if a.kind == "replacement"
        )
        self.assertEqual("1000", replacement.before.payload["quantity"])
        self.assertEqual("1200", replacement.after.payload["quantity"])

    def test_unproved_reversal_and_unknown_quantity_withhold_actions(self):
        for field, value in (("quantity", None), ("quantity", "999")):
            with self.subTest(value=value):
                pack = self.changed_event(
                    "reverse-return",
                    lambda r, field=field, value=value: replace(
                        r, payload={**r.payload, field: value}
                    ),
                )
                plan = select_input_pack(pack, cutoffs=self.later()).event_plan
                self.assertIn(
                    ("sf", "loan_outstanding", "sf:allocation:one"),
                    plan.blocked_targets,
                )
                self.assertTrue(
                    all(
                        a.after.payload["target_record_id"] != "sf:allocation:one"
                        for a in plan.actions
                    )
                )

    def test_correction_cannot_move_an_included_effect_to_a_different_target(self):
        def correction(row):
            return replace(
                row,
                payload={
                    **row.payload,
                    "target_record_id": "sf:allocation:two",
                    "supersedes_version_id": row.envelope.key.version_id,
                },
                envelope=replace(
                    row.envelope, key=replace(row.envelope.key, version_id="v2")
                ),
            )

        plan = select_input_pack(
            self.changed_event("returned", correction, append=True)
        ).event_plan
        self.assertIn(
            ("sf", "loan_outstanding", "sf:allocation:two"), plan.blocked_targets
        )
        self.assertIn(
            ("sf", "loan_outstanding", "sf:allocation:one"), plan.blocked_targets
        )
        self.assertFalse(any(a.kind == "replacement" for a in plan.actions))

    def test_snapshot_baseline_must_fit_the_exact_target_version(self):
        pack = self.manifest(
            lambda m: m["event_boundaries"][0].update(
                snapshot_as_of="2026-10-01T00:00:00Z"
            )
        )
        plan = select_input_pack(pack).event_plan
        self.assertTrue(
            any(
                "snapshot_outside_target_validity" in reasons
                for reasons in plan.blocked_targets.values()
            )
        )

    def test_selected_parent_availability_propagates(self):
        tables = dict(self.pack.tables)
        parent = tables["account"][0]
        tables["account"] = (
            replace(
                parent, envelope=replace(parent.envelope, source_available_at=None)
            ),
            *tables["account"][1:],
        )
        selected = select_input_pack(replace(self.pack, tables=tables))
        affected = [
            d
            for d in selected.decisions
            if d.record.payload.get("account_id") == parent.payload["account_id"]
        ]
        self.assertTrue(affected)
        self.assertTrue(all(d.status != "selected" for d in affected))
        self.assertTrue(
            any(
                "selected_reference_unavailable:account_id" in d.reasons
                for d in affected
            )
        )

    def test_historical_cutoff_keeps_original_version_and_unavailable_references(self):
        cutoffs = Cutoffs.from_mapping(
            {
                "business_as_of": "2026-11-03T10:30:00Z",
                "knowledge_cutoff": "2026-11-03T10:30:00Z",
                "system_cutoff": "2026-11-03T10:30:00Z",
            }
        )
        selected = select_input_pack(self.pack, cutoffs=cutoffs)
        old = next(
            d
            for d in selected.decisions
            if d.record.envelope
            and d.record.envelope.key.version_id == "sf:position:coverage-a:v0"
        )
        # Its own clocks pass, but retained parents are not yet known.
        self.assertEqual("unknown", old.status)
        self.assertIn("selected_reference_unavailable:account_id", old.reasons)
        self.assertEqual((), selected.tables["lifecycle_event"])


if __name__ == "__main__":
    unittest.main()
