"""Explicit snapshot boundaries and event reconciliation; no balance arithmetic."""

from market_atlas.securities_finance.contracts import TimestampEvidence, _require, _text
from market_atlas.securities_finance.records import EVENTS

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
