import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from market_atlas.securities_finance.contracts import (
    ContractError,
    RecordEnvelope,
    RecordKey,
    TimestampEvidence,
)
from market_atlas.securities_finance.records import SourceRecord
from market_atlas.securities_finance.temporal import (
    Cutoffs,
    after,
    at_or_before,
    compare,
    evidence_bounds,
    select_versions,
)


class TemporalTests(unittest.TestCase):
    def row(self, version="v1", *, source="sf", event=False, **times):
        def instant(value):
            return TimestampEvidence(value, "instant")

        env = RecordEnvelope(
            RecordKey(
                source, "lifecycle_event" if event else "legal_entity", "id", version
            ),
            None if event else instant("2026-11-01T00:00:00Z"),
            None,
            instant("2026-11-02T00:00:00Z"),
            None,
            instant("2026-11-03T00:00:00Z"),
            None,
            "synthetic:test",
            effective_at=instant("2026-11-01T00:00:00Z") if event else None,
        )
        env = replace(env, **times)
        payload = (
            {
                "event_id": "id",
                "event_stream_id": "stream",
                "event_type": "return_settle",
                "state_component": "loan_outstanding",
                "target_record_id": "target",
                "quantity": "1",
                "status": "settled",
                "supersedes_version_id": None,
                "reverses_event_id": None,
            }
            if event
            else {"party_id": "id", "label": "Synthetic", "role": "lender"}
        )
        return SourceRecord(env.key.record_type, source, payload, env)

    def cutoff(self, **changes):
        noon = datetime(2026, 11, 3, 12, tzinfo=UTC)
        return replace(Cutoffs(noon, noon, noon), **changes)

    def test_three_independent_clocks_and_half_open_ends(self):
        row = self.row()
        self.assertEqual("selected", select_versions((row,), self.cutoff())[0].status)
        for field, value, reason in (
            ("business_as_of", datetime(2026, 10, 31, tzinfo=UTC), "business_start"),
            (
                "knowledge_cutoff",
                datetime(2026, 11, 1, tzinfo=UTC),
                "source_availability",
            ),
            ("system_cutoff", datetime(2026, 11, 2, tzinfo=UTC), "system_start"),
        ):
            decision = select_versions((row,), self.cutoff(**{field: value}))[0]
            self.assertEqual("excluded", decision.status)
            self.assertIn(f"{reason}_outside_cutoff", decision.reasons)
        for end in ("effective_to", "recorded_to"):
            ended = replace(
                row,
                envelope=replace(
                    row.envelope,
                    **{end: TimestampEvidence("2026-11-03T12:00:00Z", "instant")},
                ),
            )
            self.assertEqual(
                "excluded", select_versions((ended,), self.cutoff())[0].status
            )

    def test_uncertain_competitor_withholds_known_version(self):
        known = self.row()
        unknown = self.row(
            "v2", source_available_at=TimestampEvidence("2026-11-03", "date", "UTC")
        )
        decisions = select_versions((known, unknown), self.cutoff())
        self.assertEqual({"unknown"}, {item.status for item in decisions})
        self.assertTrue(
            any("ambiguous_active_versions" in d.reasons for d in decisions)
        )
        overlap = select_versions((known, self.row("v3")), self.cutoff())
        self.assertEqual({"unknown"}, {item.status for item in overlap})
        missing = select_versions((self.row(source_available_at=None),), self.cutoff())[
            0
        ]
        self.assertEqual("unknown", missing.status)

    def test_visible_correction_chain_and_future_correction(self):
        old = self.row(event=True)
        new = self.row("v2", event=True)
        new = replace(new, payload={**new.payload, "supersedes_version_id": "v1"})
        decisions = select_versions((new, old), self.cutoff())
        self.assertEqual(
            ["v2"],
            [
                d.record.envelope.key.version_id
                for d in decisions
                if d.status == "selected"
            ],
        )
        future = replace(
            new,
            envelope=replace(
                new.envelope,
                source_available_at=TimestampEvidence(
                    "2026-11-04T00:00:00Z", "instant"
                ),
            ),
        )
        self.assertEqual(
            ["v1"],
            [
                d.record.envelope.key.version_id
                for d in select_versions((old, future), self.cutoff())
                if d.status == "selected"
            ],
        )
        fork = replace(
            new,
            envelope=replace(
                new.envelope, key=replace(new.envelope.key, version_id="v3")
            ),
        )
        self.assertEqual(
            {"unknown"},
            {d.status for d in select_versions((old, new, fork), self.cutoff())},
        )

    def test_version_identity_is_scoped_and_order_is_deterministic(self):
        rows = (self.row(source="a"), self.row(source="b"))
        self.assertEqual(
            select_versions(rows, self.cutoff()),
            select_versions(rows[::-1], self.cutoff()),
        )
        self.assertEqual(
            ["selected", "selected"],
            [d.status for d in select_versions(rows, self.cutoff())],
        )

    def test_adjacent_versions_select_original_then_replacement(self):
        boundary = TimestampEvidence("2026-11-03T12:00:00Z", "instant")
        old = self.row("v0", effective_to=boundary, recorded_to=boundary)
        new = self.row("v1", effective_from=boundary, recorded_from=boundary)
        current = self.cutoff()
        earlier = replace(
            current,
            business_as_of=current.business_as_of - timedelta(microseconds=1),
            system_cutoff=current.system_cutoff - timedelta(microseconds=1),
        )
        for cutoffs, expected in ((earlier, "v0"), (current, "v1")):
            selected = [
                d.record.envelope.key.version_id
                for d in select_versions((new, old), cutoffs)
                if d.status == "selected"
            ]
            self.assertEqual([expected], selected)

    def test_date_only_end_and_missing_start_withhold_but_known_failures_remain(self):
        for row in (
            self.row(effective_to=TimestampEvidence("2026-11-03", "date", "UTC")),
            self.row(effective_from=None),
        ):
            self.assertEqual(
                "unknown", select_versions((row,), self.cutoff())[0].status
            )
        unavailable = self.row(
            source_available_at=None,
            effective_from=TimestampEvidence("2026-11-04T00:00:00Z", "instant"),
        )
        decision = select_versions((unavailable,), self.cutoff())[0]
        self.assertEqual("excluded", decision.status)
        self.assertIn("source_availability_unknown", decision.reasons)
        self.assertIn("business_start_outside_cutoff", decision.reasons)

    def test_correction_cycle_is_not_an_active_winner(self):
        a, b = self.row("v1", event=True), self.row("v2", event=True)
        a = replace(a, payload={**a.payload, "supersedes_version_id": "v2"})
        b = replace(b, payload={**b.payload, "supersedes_version_id": "v1"})
        self.assertEqual(
            {"unknown"}, {d.status for d in select_versions((a, b), self.cutoff())}
        )

    def test_exact_offsets_and_cutoffs(self):
        point = TimestampEvidence("2026-11-03T07:00:00-05:00", "instant")
        noon = datetime(2026, 11, 3, 12, tzinfo=UTC)
        self.assertTrue(at_or_before(point, noon))
        self.assertFalse(after(point, noon))
        self.assertFalse(at_or_before(point, noon - timedelta(microseconds=1)))
        self.assertEqual(
            0, compare(point, TimestampEvidence(noon.isoformat(), "instant"))
        )
        self.assertEqual(noon, Cutoffs(noon, noon, noon).business_as_of)
        with self.assertRaises(ContractError):
            Cutoffs(noon.replace(tzinfo=None), noon, noon)

    def test_day_boundaries_are_conservative(self):
        day = TimestampEvidence("2026-11-03", "date", "UTC")
        start = datetime(2026, 11, 3, tzinfo=UTC)
        end = start + timedelta(days=1)
        self.assertIsNone(at_or_before(day, start))
        self.assertIsNone(after(day, start))
        self.assertFalse(at_or_before(day, start - timedelta(microseconds=1)))
        self.assertTrue(at_or_before(day, end))
        self.assertIsNone(compare(day, day))
        self.assertEqual(
            -1, compare(day, TimestampEvidence(end.isoformat(), "instant"))
        )
        self.assertEqual(1, compare(TimestampEvidence(end.isoformat(), "instant"), day))

    def test_timezone_days_follow_dst(self):
        spring = evidence_bounds(
            TimestampEvidence("2026-03-08", "date", "America/New_York")
        )
        fall = evidence_bounds(
            TimestampEvidence("2026-11-01", "date", "America/New_York")
        )
        self.assertEqual(timedelta(hours=23), spring[1] - spring[0])
        self.assertEqual(timedelta(hours=25), fall[1] - fall[0])

    def test_missing_or_unsupported_day_is_unknown(self):
        for value in (
            None,
            TimestampEvidence("2026-11-03", "date"),
            TimestampEvidence("9999-12-31", "date", "UTC"),
            TimestampEvidence("2011-12-30", "date", "Pacific/Apia"),
        ):
            with self.subTest(value=value):
                self.assertIsNone(evidence_bounds(value))
                self.assertIsNone(
                    at_or_before(value, datetime(2026, 11, 3, tzinfo=UTC))
                )


if __name__ == "__main__":
    unittest.main()
