"""Version-1 source table shapes and normalized records; no as-of selection."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from types import MappingProxyType

from market_atlas.securities_finance.catalog import ReferenceCatalog
from market_atlas.securities_finance.contracts import (
    InstrumentReference,
    QuantityConvention,
    QuantityValue,
    RecordEnvelope,
    RecordKey,
    TimestampEvidence,
    _decimal_text,
    _require,
    _scaled_quantity,
    _text,
)

Scalar = str | int | bool | None
Value = Scalar | TimestampEvidence
STATE_TIMES = (
    "effective_from",
    "effective_to",
    "source_available_at",
    "source_confirmed_at",
    "recorded_from",
    "recorded_to",
)
EVENT_TIMES = (
    "effective_at",
    "source_available_at",
    "source_confirmed_at",
    "recorded_from",
    "recorded_to",
)


def time_columns(name: str) -> tuple[str, ...]:
    return tuple(f"{name}_{part}" for part in ("value", "precision", "source_timezone"))


@dataclass(frozen=True)
class TableSchema:
    fields: Mapping[str, str]
    key_fields: tuple[str, ...]
    versioned: bool = True


def _schema(fields: str, keys: str, *, versioned: bool = True) -> TableSchema:
    return TableSchema(
        MappingProxyType(
            {
                name: kind or "text"
                for name, _, kind in (item.partition(":") for item in fields.split())
            }
        ),
        tuple(keys.split()),
        versioned,
    )


SCHEMAS: Mapping[str, TableSchema] = MappingProxyType(
    {
        "instrument_catalog": _schema(
            "instrument_node_id canonical_key node_type asset_class label provenance_reference",
            "instrument_node_id",
            versioned=False,
        ),
        "quantity_convention": _schema(
            "convention_id instrument_node_id quantity_unit quantity_currency:text? quantity_precision:int "
            "minimum_allocation allocation_increment increment_origin minimum_scope",
            "convention_id",
        ),
        "legal_entity": _schema("party_id label role:role", "party_id"),
        "account": _schema(
            "account_id owner_party_id lender_party_id custodian_party_id:text?",
            "account_id",
        ),
        "deduction_contract": _schema(
            "deduction_contract_id balance_basis:basis reservations_already_deducted:bool "
            "encumbrances_already_deducted:bool outstanding_loans_already_deducted:bool definition_reference",
            "deduction_contract_id",
        ),
        "agreement": _schema(
            "agreement_id status:agreement_status? business_valid_from:date? business_valid_to:date? "
            "permission_reference:text? snapshot_id",
            "agreement_id",
        ),
        "agreement_parties": _schema(
            "agreement_version_id party_id role:role permission_state:permission?",
            "agreement_version_id party_id role",
            versioned=False,
        ),
        "agreement_instruments": _schema(
            "agreement_version_id instrument_node_id permission_state:permission?",
            "agreement_version_id instrument_node_id",
            versioned=False,
        ),
        "agreement_locations": _schema(
            "agreement_version_id location_id permission_state:permission?",
            "agreement_version_id location_id",
            versioned=False,
        ),
        "inventory_position": _schema(
            "position_id account_id instrument_node_id location_id convention_id quantity:quantity? "
            "balance_basis:basis deduction_contract_id settlement_state:settlement? ready_date:date? snapshot_id",
            "position_id",
        ),
        "borrow_request": _schema(
            "request_id borrower_party_id instrument_node_id location_id convention_id open_quantity:quantity? "
            "required_date:date? request_order_at:evidence? priority_tier:int? agreement_id input_kind:request_kind snapshot_id",
            "request_id",
        ),
        "loan": _schema(
            "loan_id agreement_id instrument_node_id convention_id outstanding_quantity:quantity? "
            "status:loan_status input_kind:loan_kind snapshot_id",
            "loan_id",
        ),
        "loan_allocation": _schema(
            "allocation_id loan_id position_id outstanding_quantity:quantity? snapshot_id",
            "allocation_id",
        ),
        "capacity_component": _schema(
            "component_id position_id kind:component_kind quantity:quantity? status:component_status "
            "overlap_group_id:text? snapshot_id",
            "component_id",
        ),
        "lifecycle_event": _schema(
            "event_id event_stream_id event_type:event_type state_component target_record_id quantity:quantity? "
            "status:event_status supersedes_version_id:text? reverses_event_id:text?",
            "event_id",
        ),
        "snapshot_included_events": _schema(
            "snapshot_id state_component target_record_id source_name event_id event_version_id",
            "snapshot_id state_component target_record_id source_name event_id event_version_id",
            versioned=False,
        ),
        "net_benefit": _schema(
            "coefficient_id position_id request_id convention_id net_benefit_amount:money basis_quantity:positive_quantity "
            "currency horizon_id horizon_start:instant horizon_end:instant method_version assumption_reference",
            "coefficient_id",
        ),
    }
)

EVENTS = MappingProxyType(
    {
        "reservation_create": ("reservation", "capacity_component", "active"),
        "reservation_release": ("reservation", "capacity_component", "released"),
        "recall_issue": ("recall_instruction", "loan", "active"),
        "recall_cancel": ("recall_instruction", "loan", "cancelled"),
        "return_settle": ("loan_outstanding", "loan_allocation", "settled"),
        "return_reverse": ("loan_outstanding", "loan_allocation", "reversed"),
    }
)
ENUMS = {
    "role": ("lender", "borrower", "custodian"),
    "basis": ("gross", "net_available"),
    "agreement_status": ("active", "inactive"),
    "permission": ("permitted", "denied"),
    "settlement": ("settled", "pending", "failed"),
    "loan_status": ("open", "closed"),
    "component_kind": ("reservation", "encumbrance", "on_loan"),
    "component_status": ("active", "released"),
    "request_kind": ("open_request",),
    "loan_kind": ("outstanding_loan",),
    "event_type": tuple(EVENTS),
    "event_status": tuple({value[2] for value in EVENTS.values()}),
}


def columns(record_type: str) -> tuple[str, ...]:
    from market_atlas.securities_finance.contracts import ContractError

    if not isinstance(record_type, str) or record_type not in SCHEMAS:
        raise ContractError("unknown_record_type", "unsupported table")
    schema = SCHEMAS[record_type]
    result: list[str] = []
    if schema.versioned:
        result.extend(
            ("source_name", "record_id", "version_id", "source_record_reference")
        )
        for name in EVENT_TIMES if record_type == "lifecycle_event" else STATE_TIMES:
            result.extend(time_columns(name))
    for name, kind in schema.fields.items():
        result.extend(time_columns(name) if kind.rstrip("?") == "evidence" else (name,))
    return tuple(result)


@dataclass(frozen=True)
class SourceRecord:
    record_type: str
    source_name: str
    payload: Mapping[str, Value]
    envelope: RecordEnvelope | None

    def __post_init__(self) -> None:
        _require(
            self.record_type in SCHEMAS, "unknown_record_type", "unsupported table"
        )
        _text(self.source_name, "source_name")
        _require(
            set(self.payload) == set(SCHEMAS[self.record_type].fields),
            "invalid_fields",
            "normalized payload fields differ from schema",
        )
        _require(
            all(
                value is None
                or type(value) in (str, int, bool)
                or isinstance(value, TimestampEvidence)
                for value in self.payload.values()
            ),
            "invalid_field_type",
            "flat typed payload required",
        )
        _require(
            (self.envelope is not None) == SCHEMAS[self.record_type].versioned,
            "invalid_envelope",
            "table envelope applicability mismatch",
        )
        if self.envelope is not None:
            _require(
                isinstance(self.envelope, RecordEnvelope)
                and self.envelope.key.source_name == self.source_name
                and self.envelope.key.record_type == self.record_type,
                "invalid_envelope",
                "typed envelope source/table differs",
            )
        for name, kind in SCHEMAS[self.record_type].fields.items():
            if kind.rstrip("?") == "evidence":
                _require(
                    self.payload[name] is None
                    or isinstance(self.payload[name], TimestampEvidence),
                    "invalid_timestamp",
                    "typed evidence required",
                    name,
                )
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    def to_row(self, *, semantic: bool = False) -> dict[str, Scalar]:
        result: dict[str, Scalar] = {}

        def add_time(name: str, value: TimestampEvidence | None) -> None:
            result[f"{name}_value"] = (
                (value.normalized_value if semantic else value.value) if value else None
            )
            result[f"{name}_precision"] = value.precision if value else None
            result[f"{name}_source_timezone"] = value.source_timezone if value else None

        if self.envelope is not None:
            key = self.envelope.key
            result.update(
                source_name=key.source_name,
                record_id=key.record_id,
                version_id=key.version_id,
                source_record_reference=self.envelope.source_record_reference,
            )
            for name in (
                EVENT_TIMES if self.record_type == "lifecycle_event" else STATE_TIMES
            ):
                add_time(name, getattr(self.envelope, name))
        for name, kind in SCHEMAS[self.record_type].fields.items():
            value = self.payload[name]
            if kind.rstrip("?") == "evidence":
                add_time(name, value)
            else:
                result[name] = value
        return result


def evidence(row: Mapping[str, Scalar], name: str) -> TimestampEvidence | None:
    value, precision, zone = (row[column] for column in time_columns(name))
    if value is None:
        _require(
            precision is None and zone is None,
            "invalid_timestamp",
            "missing value has time metadata",
            name,
        )
        return None
    return TimestampEvidence(value, precision, zone)


def _field(value: Scalar, kind: str, name: str) -> Value:
    if value is None:
        _require(
            kind.endswith("?"), "missing_required_fact", "nonnull field required", name
        )
        return None
    kind = kind.rstrip("?")
    if kind == "int":
        _require(
            type(value) is int and 0 <= value <= 1000000000,
            "invalid_integer",
            "bounded nonnegative integer required",
            name,
        )
    elif kind == "bool":
        _require(type(value) is bool, "invalid_boolean", "boolean required", name)
    else:
        _text(value, name)
        if kind in ENUMS:
            _require(
                value in ENUMS[kind], "invalid_enum", "unsupported field value", name
            )
        elif kind == "date":
            _require(
                re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None,
                "invalid_date",
                "ISO business date required",
                name,
            )
            try:
                date.fromisoformat(value)
            except ValueError as error:
                from market_atlas.securities_finance.contracts import ContractError

                raise ContractError(
                    "invalid_date", "invalid business date", field=name
                ) from error
        elif kind == "instant":
            value = TimestampEvidence(value, "instant").normalized_value
        elif kind == "money":
            sign = -1 if value.startswith("-") else 1
            units = _scaled_quantity(value[1:] if sign == -1 else value, 6, name)
            value = ("-" if sign < 0 and units else "") + _decimal_text(units, 6)
    return value


def referenced(
    tables: Mapping[str, tuple[SourceRecord, ...]],
    table: str,
    source: str,
    identifier: str,
    *,
    version: bool = False,
    record_id: str | None = None,
) -> tuple[SourceRecord, ...]:
    key = "version_id" if version else SCHEMAS[table].key_fields[0]
    matches = tuple(
        row
        for row in tables.get(table, ())
        if row.source_name == source
        and (row.envelope.key.version_id if version else row.payload[key]) == identifier
        and (record_id is None or row.envelope.key.record_id == record_id)
    )
    _require(bool(matches), "unknown_reference", f"unmapped {table} reference")
    return matches


def _one_metadata(rows: tuple[SourceRecord, ...], field: str) -> Value:
    values = {row.payload[field] for row in rows}
    _require(
        len(values) == 1,
        "ambiguous_reference",
        "version-dependent metadata needs temporal selection",
        field,
    )
    return next(iter(values))


def _convention(
    record_type: str,
    payload: Mapping[str, Value],
    source: str,
    tables: Mapping[str, tuple[SourceRecord, ...]],
    catalog: ReferenceCatalog,
) -> QuantityConvention:
    if "convention_id" in payload:
        result = catalog.convention(payload["convention_id"])
        if "instrument_node_id" in payload:
            _require(
                result.instrument_node_id == payload["instrument_node_id"],
                "instrument_convention_mismatch",
                "instrument and convention differ",
            )
        return result
    if record_type in ("capacity_component", "loan_allocation"):
        rows = referenced(tables, "inventory_position", source, payload["position_id"])
        return catalog.convention(_one_metadata(rows, "convention_id"))
    target_table = EVENTS[payload["event_type"]][1]
    target = referenced(tables, target_table, source, payload["target_record_id"])
    if target_table in ("capacity_component", "loan_allocation"):
        position = _one_metadata(target, "position_id")
        target = referenced(tables, "inventory_position", source, position)
    return catalog.convention(_one_metadata(target, "convention_id"))


def normalize_rows(
    record_type: str,
    rows: tuple[Mapping[str, Scalar], ...],
    source_name: str,
    *,
    catalog: ReferenceCatalog | None = None,
    tables: Mapping[str, tuple[SourceRecord, ...]] | None = None,
) -> tuple[SourceRecord, ...]:
    """Validate decoded scalars using the same path for JSON and CSV."""
    columns(record_type)
    schema = SCHEMAS[record_type]
    context = tables if tables is not None else {}
    result = []
    seen = set()
    for row in rows:
        _require(
            set(row) == set(columns(record_type)),
            "invalid_columns",
            "missing or unknown record columns",
        )
        payload = {
            name: evidence(row, name)
            if kind.rstrip("?") == "evidence"
            else _field(row[name], kind, name)
            for name, kind in schema.fields.items()
        }
        envelope = None
        if schema.versioned:
            _require(
                row["source_name"] == source_name,
                "source_mismatch",
                "record and dataset source differ",
            )
            times = {
                name: evidence(row, name)
                for name in (
                    EVENT_TIMES if record_type == "lifecycle_event" else STATE_TIMES
                )
            }
            envelope = RecordEnvelope(
                key=RecordKey(
                    source_name, record_type, row["record_id"], row["version_id"]
                ),
                effective_from=times.get("effective_from"),
                effective_to=times.get("effective_to"),
                source_available_at=times["source_available_at"],
                source_confirmed_at=times["source_confirmed_at"],
                recorded_from=times["recorded_from"],
                recorded_to=times["recorded_to"],
                source_record_reference=row["source_record_reference"],
                effective_at=times.get("effective_at"),
            )
            _require(
                payload[schema.key_fields[0]] == envelope.key.record_id,
                "record_identity_mismatch",
                "business ID differs from envelope ID",
            )
        key = (
            envelope.key
            if envelope
            else (source_name, *(payload[name] for name in schema.key_fields))
        )
        _require(key not in seen, "duplicate_record_key", "table record key repeated")
        seen.add(key)
        if record_type == "instrument_catalog":
            reference = InstrumentReference.from_mapping(payload)
            payload = {name: getattr(reference, name) for name in schema.fields}
        elif record_type == "quantity_convention":
            convention = QuantityConvention.from_mapping(payload)
            payload = {name: getattr(convention, name) for name in schema.fields}
        elif any(
            kind.rstrip("?") in ("quantity", "positive_quantity")
            for kind in schema.fields.values()
        ):
            _require(
                catalog is not None,
                "missing_catalog",
                "quantity normalization needs a reference catalog",
            )
            convention = _convention(
                record_type, payload, source_name, context, catalog
            )
            for name, kind in schema.fields.items():
                if kind.rstrip("?") in ("quantity", "positive_quantity"):
                    value = QuantityValue(
                        payload[name],
                        convention.quantity_unit,
                        convention.quantity_currency,
                        convention.quantity_precision,
                    )
                    convention.validate_quantity(value)
                    if kind == "positive_quantity":
                        _require(
                            value.units is not None and value.units > 0,
                            "invalid_quantity",
                            "positive basis required",
                            name,
                        )
                    payload[name] = value.amount
        result.append(SourceRecord(record_type, source_name, payload, envelope))
    return tuple(result)


def validate_references(
    tables: Mapping[str, tuple[SourceRecord, ...]], catalog: ReferenceCatalog
) -> None:
    """Validate retained references without selecting versions or applying events."""
    links = {
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
    }
    snapshots = {
        row.payload["snapshot_id"]
        for rows in tables.values()
        for row in rows
        if "snapshot_id" in row.payload
        and row.record_type != "snapshot_included_events"
    }
    for table, rows in tables.items():
        for row in rows:
            p, source = row.payload, row.source_name
            for name, target in links.get(table, {}).items():
                if p[name] is not None:
                    referenced(tables, target, source, p[name])
            if "instrument_node_id" in p:
                catalog.instrument(p["instrument_node_id"])
            if table.startswith("agreement_"):
                parent = referenced(
                    tables, "agreement", source, p["agreement_version_id"], version=True
                )
                _require(
                    len(parent) == 1,
                    "ambiguous_reference",
                    "agreement version ID is not unique",
                )
                if table == "agreement_parties":
                    referenced(tables, "legal_entity", source, p["party_id"])
            if table == "inventory_position":
                definitions = referenced(
                    tables, "deduction_contract", source, p["deduction_contract_id"]
                )
                _require(
                    _one_metadata(definitions, "balance_basis") == p["balance_basis"],
                    "balance_basis_mismatch",
                    "position and source balance definition differ",
                )
            if table in ("loan_allocation", "net_benefit"):
                position = referenced(
                    tables, "inventory_position", source, p["position_id"]
                )
                other_table, key = (
                    ("loan", "loan_id")
                    if table == "loan_allocation"
                    else ("borrow_request", "request_id")
                )
                other = referenced(tables, other_table, source, p[key])
                for field in ("instrument_node_id", "convention_id"):
                    _require(
                        _one_metadata(position, field) == _one_metadata(other, field),
                        "reference_convention_mismatch",
                        "linked records have different instruments/conventions",
                    )
                if table == "net_benefit":
                    _require(
                        p["convention_id"] == _one_metadata(position, "convention_id"),
                        "reference_convention_mismatch",
                        "coefficient convention differs",
                    )
                    _require(
                        TimestampEvidence(p["horizon_start"], "instant").as_utc()
                        < TimestampEvidence(p["horizon_end"], "instant").as_utc(),
                        "invalid_horizon",
                        "horizon end must follow start",
                    )
                    coefficient = (
                        Fraction(p["net_benefit_amount"])
                        / Fraction(p["basis_quantity"])
                        * 1000000
                    )
                    _require(
                        coefficient.denominator == 1,
                        "unrepresentable_coefficient",
                        "per-unit benefit exceeds objective scale",
                    )
            if table == "lifecycle_event":
                component, target, status = EVENTS[p["event_type"]]
                _require(
                    (p["state_component"], p["status"]) == (component, status),
                    "invalid_event_transition",
                    "event component/status mismatch",
                )
                referenced(tables, target, source, p["target_record_id"])
                if p["event_type"] in ("return_reverse", "recall_cancel"):
                    _require(
                        p["reverses_event_id"] is not None,
                        "missing_reversal",
                        "original event required",
                    )
                if p["reverses_event_id"] is not None:
                    original = referenced(
                        tables, "lifecycle_event", source, p["reverses_event_id"]
                    )
                    _require(
                        p["reverses_event_id"] != p["event_id"]
                        and _one_metadata(original, "target_record_id")
                        == p["target_record_id"]
                        and _one_metadata(original, "state_component")
                        == p["state_component"],
                        "invalid_reversal",
                        "original effect target differs",
                    )
                    expected = {
                        "return_reverse": "return_settle",
                        "recall_cancel": "recall_issue",
                        "reservation_release": "reservation_create",
                    }
                    _require(
                        p["event_type"] in expected
                        and _one_metadata(original, "event_type")
                        == expected[p["event_type"]],
                        "invalid_reversal",
                        "unsupported reversal transition",
                    )
                if p["supersedes_version_id"] is not None:
                    original = referenced(
                        tables,
                        "lifecycle_event",
                        source,
                        p["supersedes_version_id"],
                        version=True,
                        record_id=p["event_id"],
                    )
                    _require(
                        p["supersedes_version_id"] != row.envelope.key.version_id
                        and all(
                            item.payload["event_id"] == p["event_id"]
                            for item in original
                        ),
                        "invalid_supersession",
                        "event correction must reference another version of itself",
                    )
            if table == "snapshot_included_events":
                original = referenced(
                    tables,
                    "lifecycle_event",
                    p["source_name"],
                    p["event_version_id"],
                    version=True,
                    record_id=p["event_id"],
                )
                _require(
                    p["snapshot_id"] in snapshots
                    and len(original) == 1
                    and all(
                        original[0].payload[name] == p[name]
                        for name in ("event_id", "state_component", "target_record_id")
                    ),
                    "invalid_event_inclusion",
                    "snapshot event identity/scope does not match",
                )


def normalize_tables(
    rows: Mapping[str, tuple[Mapping[str, Scalar], ...]], sources: Mapping[str, str]
) -> tuple[Mapping[str, tuple[SourceRecord, ...]], ReferenceCatalog]:
    _require(
        set(rows) == set(SCHEMAS) == set(sources),
        "invalid_tables",
        "every declared table is required (possibly empty)",
    )
    result: dict[str, tuple[SourceRecord, ...]] = {}
    for name in ("instrument_catalog", "quantity_convention"):
        result[name] = normalize_rows(name, rows[name], sources[name])
    catalog = ReferenceCatalog(
        tuple(
            InstrumentReference.from_mapping(row.payload)
            for row in result["instrument_catalog"]
        ),
        tuple(
            QuantityConvention.from_mapping(row.payload)
            for row in result["quantity_convention"]
        ),
    )
    for name in SCHEMAS:
        if name not in result:
            result[name] = normalize_rows(
                name, rows[name], sources[name], catalog=catalog, tables=result
            )
    validate_references(result, catalog)
    return MappingProxyType(result), catalog
