"""Explicit snapshot boundaries and event reconciliation; no balance arithmetic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from market_atlas.securities_finance.contracts import TimestampEvidence, _require, _text
from market_atlas.securities_finance.records import EVENTS, SourceRecord
from market_atlas.securities_finance.temporal import after, at_or_before, compare

TARGETS = {component: table for component, table, _ in EVENTS.values()}
BOUNDARY_FIELDS = frozenset(
    "snapshot_id source_name event_stream_id state_component target_record_id "
    "target_version_id snapshot_as_of complete".split()
)


def validate_event_boundaries(boundaries, tables, dataset_metadata):
    """Validate declarations against retained facts, without asserting selection."""
    _require(
        isinstance(boundaries, list) and len(boundaries) <= 10000,
        "invalid_event_boundaries",
        "bounded boundary list required",
    )
    seen = set()
    for item in boundaries:
        _require(
            isinstance(item, dict) and set(item) == BOUNDARY_FIELDS,
            "invalid_event_boundary",
            "exact boundary fields required",
        )
        for field in BOUNDARY_FIELDS - {"complete"}:
            _text(item[field], field)
        _require(
            type(item["complete"]) is bool,
            "invalid_event_boundary",
            "explicit completeness boolean required",
        )
        TimestampEvidence(item["snapshot_as_of"], "instant")
        component = item["state_component"]
        _require(
            component in TARGETS, "invalid_event_boundary", "unknown state component"
        )
        target_table = TARGETS[component]
        target = [
            row
            for row in tables[target_table]
            if row.source_name == item["source_name"]
            and row.envelope.key.record_id == item["target_record_id"]
            and row.envelope.key.version_id == item["target_version_id"]
            and row.payload["snapshot_id"] == item["snapshot_id"]
        ]
        event_source = dataset_metadata["lifecycle_event"]
        _require(
            len(target) == 1
            and event_source["source_name"] == item["source_name"]
            and event_source["event_stream_id"] == item["event_stream_id"],
            "invalid_event_boundary",
            "retained target version/stream does not match",
        )
        scope = tuple(
            item[name]
            for name in (
                "snapshot_id",
                "source_name",
                "event_stream_id",
                "state_component",
                "target_record_id",
            )
        )
        _require(
            scope not in seen,
            "duplicate_event_boundary",
            "one boundary per snapshot/component/target required",
        )
        seen.add(scope)


def event_scope(row):
    return (
        row.source_name,
        row.payload["state_component"],
        row.payload["target_record_id"],
    )


@dataclass(frozen=True)
class EventAssessment:
    event: SourceRecord
    status: str
    reasons: tuple[str, ...] = ()
    included_before: SourceRecord | None = None


@dataclass(frozen=True)
class EventAction:
    kind: str
    before: SourceRecord | None
    after: SourceRecord


@dataclass(frozen=True)
class EventPlan:
    assessments: tuple[EventAssessment, ...]
    actions: tuple[EventAction, ...]
    blocked_targets: Mapping[tuple[str, str, str], tuple[str, ...]]


def reconcile_events(pack, selection) -> EventPlan:
    """Plan effects once per identity; withhold an entire scope on uncertainty.

    Actions describe replacements/reversals, not signed capacity deltas. Callers
    must honor blocked_targets and use the later component-specific arithmetic.
    """
    boundaries, included, blocked = {}, {}, {}
    retained = {row.envelope.key: row for row in pack.tables["lifecycle_event"]}

    def block(scope, reason):
        blocked.setdefault(scope, set()).add(reason)

    for component, table in sorted(TARGETS.items()):
        for target in selection.tables[table]:
            if table == "capacity_component" and target.payload["kind"] != component:
                continue
            scope = target.source_name, component, target.envelope.key.record_id
            matches = [
                b
                for b in pack.manifest.get("event_boundaries", ())
                if (b["source_name"], b["state_component"], b["target_record_id"])
                == scope
                and b["snapshot_id"] == target.payload["snapshot_id"]
                and b["target_version_id"] == target.envelope.key.version_id
            ]
            if len(matches) != 1:
                block(scope, "snapshot_boundary_unavailable")
                continue
            boundary = matches[0]
            boundaries[scope] = boundary
            baseline = TimestampEvidence(boundary["snapshot_as_of"], "instant")
            if at_or_before(
                target.envelope.effective_from, baseline.as_utc()
            ) is not True or (
                target.envelope.effective_to is not None
                and after(target.envelope.effective_to, baseline.as_utc()) is not True
            ):
                block(scope, "snapshot_outside_target_validity")
            if not boundary["complete"]:
                block(scope, "incomplete_event_inclusion")
            if at_or_before(baseline, selection.cutoffs.business_as_of) is not True:
                block(scope, "snapshot_after_business_cutoff")
            receipts = [
                r
                for r in pack.tables["snapshot_included_events"]
                if (
                    r.payload["source_name"],
                    r.payload["state_component"],
                    r.payload["target_record_id"],
                )
                == scope
                and r.payload["snapshot_id"] == boundary["snapshot_id"]
            ]
            effects = {}
            for receipt in receipts:
                p = receipt.payload
                originals = [
                    r
                    for key, r in retained.items()
                    if key.source_name == p["source_name"]
                    and key.record_id == p["event_id"]
                    and key.version_id == p["event_version_id"]
                ]
                original = originals[0]  # retained identity verified by input loader
                env = original.envelope
                if (
                    original.payload["event_stream_id"] != boundary["event_stream_id"]
                    or at_or_before(env.effective_at, baseline.as_utc()) is not True
                    or at_or_before(
                        env.source_available_at, selection.cutoffs.knowledge_cutoff
                    )
                    is not True
                    or at_or_before(env.recorded_from, selection.cutoffs.system_cutoff)
                    is not True
                    or original.payload["quantity"] is None
                ):
                    block(scope, "included_event_evidence_unavailable")
                if p["event_id"] in effects:
                    block(scope, "multiple_included_event_versions")
                effects[p["event_id"]] = original
            included[scope] = effects
    assessments = []
    for decision in selection.decisions:
        row = decision.record
        if row.record_type != "lifecycle_event":
            continue
        scope = event_scope(row)
        if decision.status == "excluded":
            assessment = EventAssessment(row, "excluded", decision.reasons)
        elif decision.status == "unknown":
            assessment = EventAssessment(row, "unknown", decision.reasons)
        elif scope not in boundaries:
            assessment = EventAssessment(
                row, "unknown", ("selected_target_boundary_unavailable",)
            )
        else:
            assessment = _assess_event(
                row, boundaries[scope], included[scope], retained, selection.cutoffs
            )
        if assessment.status == "unknown":
            for reason in assessment.reasons:
                block(scope, reason)
            # A correction/ambiguous version must not leave its previous target
            # apparently reconciled after moving or losing the original effect.
            for key, version in retained.items():
                if (key.source_name, key.record_id) == (
                    row.source_name,
                    row.envelope.key.record_id,
                ):
                    block(event_scope(version), "event_identity_unreconciled")
        assessments.append(assessment)
    current = {
        (a.event.source_name, a.event.envelope.key.record_id): a
        for a in assessments
        if a.status not in ("excluded", "unknown")
    }
    reversals = {}
    for assessment in current.values():
        row = assessment.event
        original_id = row.payload["reverses_event_id"]
        if original_id is None:
            if row.payload["event_type"] == "reservation_release":
                block(event_scope(row), "release_original_unavailable")
            continue
        original = current.get((row.source_name, original_id))
        if (
            original is None
            or original.event.payload["quantity"] != row.payload["quantity"]
            or compare(original.event.envelope.effective_at, row.envelope.effective_at)
            != -1
        ):
            block(event_scope(row), "reversal_evidence_unavailable")
        key = row.source_name, original_id
        if key in reversals:
            block(event_scope(row), "multiple_reversals_of_same_effect")
        reversals[key] = row
    assessments = tuple(
        EventAssessment(
            a.event,
            "unknown",
            tuple(sorted(set(a.reasons) | blocked[event_scope(a.event)])),
            a.included_before,
        )
        if a.status != "excluded" and event_scope(a.event) in blocked
        else a
        for a in assessments
    )
    actions = tuple(
        EventAction(
            "replacement"
            if a.status == "replacement"
            else "reversal"
            if a.event.payload["reverses_event_id"]
            else "new_effect",
            a.included_before,
            a.event,
        )
        for a in assessments
        if a.status in ("pending", "replacement")
    )
    return EventPlan(
        assessments,
        actions,
        MappingProxyType({k: tuple(sorted(v)) for k, v in sorted(blocked.items())}),
    )


def _assess_event(row, boundary, included, retained, cutoffs):
    """Resolve a selected correction against an exact included ancestor."""

    def unknown(reason):
        return EventAssessment(row, "unknown", (reason,))

    if row.payload["event_stream_id"] != boundary["event_stream_id"]:
        return unknown("event_stream_mismatch")
    baseline = TimestampEvidence(boundary["snapshot_as_of"], "instant").as_utc()
    prior = included.get(row.envelope.key.record_id)
    if prior is not None and prior.envelope.key == row.envelope.key:
        return EventAssessment(row, "already_included")
    cursor, visited = row, set()
    chain = []
    while cursor.envelope.key not in visited:
        visited.add(cursor.envelope.key)
        chain.append(cursor)
        parent = cursor.payload["supersedes_version_id"]
        if parent is None:
            break
        key = cursor.envelope.key
        matches = [
            r
            for k, r in retained.items()
            if k.source_name == key.source_name
            and k.record_id == key.record_id
            and k.version_id == parent
        ]
        if len(matches) != 1:
            return unknown("correction_lineage_unavailable")
        cursor = matches[0]
    else:
        return unknown("cyclic_event_corrections")
    fields = (
        "event_type",
        "state_component",
        "target_record_id",
        "event_stream_id",
        "reverses_event_id",
    )
    if any(
        any(item.payload[f] != row.payload[f] for f in fields)
        or item.payload["quantity"] is None
        or at_or_before(item.envelope.source_available_at, cutoffs.knowledge_cutoff)
        is not True
        or at_or_before(item.envelope.recorded_from, cutoffs.system_cutoff) is not True
        for item in chain
    ):
        return unknown("correction_effect_unavailable")
    if prior is not None:
        if prior.envelope.key not in {r.envelope.key for r in chain}:
            return unknown("included_version_not_correction_ancestor")
        return EventAssessment(row, "replacement", included_before=prior)
    if any(after(item.envelope.effective_at, baseline) is not True for item in chain):
        return unknown("late_or_ambiguous_unincluded_effect")
    return EventAssessment(row, "pending")
