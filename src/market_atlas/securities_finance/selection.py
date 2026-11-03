"""As-of source facts and FIFO evidence; no eligibility or capacity claims."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from itertools import combinations
from types import MappingProxyType
from typing import TYPE_CHECKING

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.securities_finance.contracts import RecordKey, _require
from market_atlas.securities_finance.events import EventPlan, reconcile_events
from market_atlas.securities_finance.records import SCHEMAS, SourceRecord
from market_atlas.securities_finance.temporal import (
    Cutoffs,
    Decision,
    compare,
    select_versions,
)

if TYPE_CHECKING:
    from market_atlas.securities_finance.adapters import InputPack, SourceLocation

LINKS = {
    "account": {
        "owner_party_id": "legal_entity",
        "lender_party_id": "legal_entity",
        "custodian_party_id": "legal_entity",
    },
    "inventory_position": {
        "account_id": "account",
        "deduction_contract_id": "deduction_contract",
    },
    "borrow_request": {
        "borrower_party_id": "legal_entity",
        "agreement_id": "agreement",
    },
    "loan": {"agreement_id": "agreement"},
    "loan_allocation": {"loan_id": "loan", "position_id": "inventory_position"},
    "capacity_component": {"position_id": "inventory_position"},
    "net_benefit": {
        "position_id": "inventory_position",
        "request_id": "borrow_request",
    },
    "agreement_parties": {"party_id": "legal_entity"},
}


def _selected_tables(decisions):
    return MappingProxyType(
        {
            name: tuple(
                d.record
                for d in decisions
                if d.status == "selected" and d.record.record_type == name
            )
            for name in SCHEMAS
        }
    )


def _resolve_references(decisions):
    """Propagate unavailable parents; retained FK existence is insufficient."""
    while True:
        tables = _selected_tables(decisions)
        changed, result = False, []
        for decision in decisions:
            row, reasons = decision.record, []
            if decision.status == "selected":
                links = dict(LINKS.get(row.record_type, {}))
                if (
                    "convention_id" in row.payload
                    and row.record_type != "quantity_convention"
                ):
                    links["convention_id"] = "quantity_convention"
                for field, table in links.items():
                    value = row.payload[field]
                    if value is not None and not any(
                        parent.source_name == row.source_name
                        and parent.envelope.key.record_id == value
                        for parent in tables[table]
                    ):
                        reasons.append(f"selected_reference_unavailable:{field}")
                if row.record_type.startswith("agreement_") and not any(
                    parent.source_name == row.source_name
                    and parent.envelope.key.version_id
                    == row.payload["agreement_version_id"]
                    for parent in tables["agreement"]
                ):
                    reasons.append("selected_agreement_version_unavailable")
            if reasons:
                decision = replace(decision, status="unknown", reasons=tuple(reasons))
                changed = True
            result.append(decision)
        decisions = tuple(result)
        if not changed:
            return decisions


@dataclass(frozen=True)
class RequestOrder:
    left: RecordKey
    right: RecordKey
    relation: int | None


@dataclass(frozen=True)
class Selection:
    cutoffs: Cutoffs
    decisions: tuple[Decision, ...]
    tables: Mapping[str, tuple[SourceRecord, ...]]
    request_order: tuple[RequestOrder, ...]
    semantic_identity: str
    input_manifest_id: str
    provenance: tuple[SourceLocation, ...]
    event_plan: EventPlan | None = None


def select_input_pack(pack: InputPack, *, cutoffs: Cutoffs | None = None) -> Selection:
    """Select one supported version per identity, preserving all diagnostics."""
    cutoffs = (
        Cutoffs.from_mapping(pack.manifest["cutoffs"]) if cutoffs is None else cutoffs
    )
    _require(isinstance(cutoffs, Cutoffs), "invalid_cutoff", "typed cutoffs required")
    decisions = select_versions(
        tuple(row for rows in pack.tables.values() for row in rows), cutoffs
    )
    decisions = _resolve_references(decisions)
    tables = _selected_tables(decisions)
    order = tuple(
        RequestOrder(
            left.envelope.key,
            right.envelope.key,
            compare(
                left.payload["request_order_at"], right.payload["request_order_at"]
            ),
        )
        for left, right in combinations(tables["borrow_request"], 2)
        if (left.payload["instrument_node_id"], left.payload["convention_id"])
        == (right.payload["instrument_node_id"], right.payload["convention_id"])
    )
    identity = sha256(
        {
            "method": "sf-selection-v1",
            "input_semantic_identity": pack.semantic_identity,
            "cutoffs": {
                name: getattr(cutoffs, name).isoformat()
                for name in ("business_as_of", "knowledge_cutoff", "system_cutoff")
            },
            "decisions": sorted(
                (
                    {
                        "record": d.record.to_row(semantic=True),
                        "table": d.record.record_type,
                        "status": d.status,
                        "reasons": d.reasons,
                    }
                    for d in decisions
                ),
                key=canonical_bytes,
            ),
        }
    )
    result = Selection(
        cutoffs, decisions, tables, order, identity, pack.manifest_id, pack.provenance
    )
    return replace(result, event_plan=reconcile_events(pack, result))
