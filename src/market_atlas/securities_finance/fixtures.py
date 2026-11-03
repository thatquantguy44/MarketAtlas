"""Deterministic synthetic business input packs; never alter public fixtures."""

from __future__ import annotations

import hashlib
import tempfile
from datetime import timedelta
from pathlib import Path

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.securities_finance.adapters import (
    MAX_FILE_BYTES,
    encode_table,
    load_settings,
    read_input_pack,
    validate_settings_catalog,
)
from market_atlas.securities_finance.catalog import (
    ReferenceCatalog,
    build_reference_catalog,
)
from market_atlas.securities_finance.contracts import (
    QuantityConvention,
    TimestampEvidence,
    _require,
)
from market_atlas.securities_finance.records import (
    EVENT_TIMES,
    EVENTS,
    SCHEMAS,
    STATE_TIMES,
    columns,
    normalize_tables,
)

SOURCE = "sf"
SNAPSHOT = "sf:snapshot:v1"
EVENT_STREAM = "sf:events:v1"


def _fixture_rows(settings: dict, balance_basis: str):
    _require(
        balance_basis in ("gross", "net_available"),
        "invalid_balance_basis",
        "gross or net_available required",
    )
    instruments = build_reference_catalog().instruments
    by_key = {row.canonical_key.removeprefix("fixture:"): row for row in instruments}
    conventions = []
    template = settings["quantity"]["equity"]
    for source_id in ("I-A", "I-B", "I-C"):
        conventions.append(
            QuantityConvention.from_mapping(
                {
                    **template,
                    "convention_id": f"{template['convention_id']}:{source_id}",
                    "instrument_node_id": by_key[source_id].instrument_node_id,
                    "quantity_currency": None,
                }
            )
        )
    for row in settings["quantity"]["fixed_income"]:
        _require(
            row["source_instrument_id"] in by_key,
            "unknown_instrument",
            "fixture does not declare this bond",
        )
        conventions.append(
            QuantityConvention.from_mapping(
                {
                    **{
                        key: value
                        for key, value in row.items()
                        if key != "source_instrument_id"
                    },
                    "instrument_node_id": by_key[
                        row["source_instrument_id"]
                    ].instrument_node_id,
                }
            )
        )
    catalog = ReferenceCatalog(instruments, tuple(conventions))
    validate_settings_catalog(settings, catalog)
    by_instrument = {row.instrument_node_id: row for row in conventions}
    now = TimestampEvidence(settings["time"]["business_as_of"], "instant").as_utc()

    def iso(value):
        return value.isoformat().replace("+00:00", "Z")

    rows = {name: [] for name in SCHEMAS}

    def add(table, payload, *, version="v1", times=None):
        row = dict.fromkeys(columns(table))
        row.update(payload)
        if SCHEMAS[table].versioned:
            identifier = payload[SCHEMAS[table].key_fields[0]]
            row.update(
                source_name=SOURCE,
                record_id=identifier,
                version_id=f"{identifier}:{version}",
                source_record_reference=f"fixture:{table}:{identifier}:{version}",
            )
            defaults = {
                "effective_from": now - timedelta(days=2),
                "effective_to": None,
                "effective_at": now - timedelta(minutes=10),
                "source_available_at": now - timedelta(seconds=120),
                "source_confirmed_at": now - timedelta(seconds=60),
                "recorded_from": now - timedelta(seconds=30),
                "recorded_to": None,
            }
            defaults.update(times or {})
            for name in EVENT_TIMES if table == "lifecycle_event" else STATE_TIMES:
                value = defaults[name]
                if value is not None:
                    if isinstance(value, TimestampEvidence):
                        (
                            row[f"{name}_value"],
                            row[f"{name}_precision"],
                            row[f"{name}_source_timezone"],
                        ) = value.value, value.precision, value.source_timezone
                    else:
                        (
                            row[f"{name}_value"],
                            row[f"{name}_precision"],
                            row[f"{name}_source_timezone"],
                        ) = iso(value), "instant", "UTC"
        rows[table].append(row)
        return row

    for reference in instruments:
        add(
            "instrument_catalog",
            {
                name: getattr(reference, name)
                for name in SCHEMAS["instrument_catalog"].fields
            },
        )
    for convention in conventions:
        add(
            "quantity_convention",
            {
                name: getattr(convention, name)
                for name in SCHEMAS["quantity_convention"].fields
            },
        )
    for name, role in (
        ("owner-a", "lender"),
        ("owner-b", "lender"),
        ("owner-c", "lender"),
        ("borrower-one", "borrower"),
        ("borrower-two", "borrower"),
        ("custodian", "custodian"),
    ):
        add(
            "legal_entity",
            {
                "party_id": f"sf:party:{name}",
                "role": role,
                "label": 'Synthetic Custodian, "One"\nDesk — α'
                if name == "custodian"
                else f"Synthetic {name}",
            },
        )
    for suffix in ("a", "b", "c"):
        add(
            "account",
            {
                "account_id": f"sf:account:{suffix}",
                "owner_party_id": f"sf:party:owner-{suffix}",
                "lender_party_id": f"sf:party:owner-{suffix}",
                "custodian_party_id": None if suffix == "c" else "sf:party:custodian",
            },
        )
    add(
        "deduction_contract",
        {
            "deduction_contract_id": "sf:balance:v1",
            "balance_basis": balance_basis,
            "reservations_already_deducted": balance_basis == "net_available",
            "encumbrances_already_deducted": balance_basis == "net_available",
            "outstanding_loans_already_deducted": True,
            "definition_reference": "synthetic:free-inventory-before-or-after-reservations; loans already excluded",
        },
    )
    agreement_data = {
        "coverage": (["I-A"], ["a", "b", "c"], "one"),
        "joint-one": (["I-B"], ["a", "b"], "one"),
        "joint-two": (["I-B"], ["a"], "two"),
        "balance": (["I-C"], ["a"], "one"),
        "bonds": (["SF-BOND-A", "SF-BOND-B"], ["a", "b"], "one"),
    }
    for name, (ids, owners, borrower) in agreement_data.items():
        agreement_id = f"sf:agreement:{name}"
        add(
            "agreement",
            {
                "agreement_id": agreement_id,
                "status": "active",
                "business_valid_from": (now - timedelta(days=30)).date().isoformat(),
                "business_valid_to": None,
                "permission_reference": f"synthetic:permission:{name}",
                "snapshot_id": SNAPSHOT,
            },
            times={
                "source_available_at": TimestampEvidence(
                    (now - timedelta(days=1)).date().isoformat(), "date", "UTC"
                )
            },
        )
        version_id = f"{agreement_id}:v1"
        for owner in owners:
            add(
                "agreement_parties",
                {
                    "agreement_version_id": version_id,
                    "party_id": f"sf:party:owner-{owner}",
                    "role": "lender",
                    "permission_state": None if owner == "c" else "permitted",
                },
            )
        add(
            "agreement_parties",
            {
                "agreement_version_id": version_id,
                "party_id": f"sf:party:borrower-{borrower}",
                "role": "borrower",
                "permission_state": "permitted",
            },
        )
        for source_id in ids:
            add(
                "agreement_instruments",
                {
                    "agreement_version_id": version_id,
                    "instrument_node_id": by_key[source_id].instrument_node_id,
                    "permission_state": "permitted",
                },
            )
        add(
            "agreement_locations",
            {
                "agreement_version_id": version_id,
                "location_id": "NYC",
                "permission_state": "permitted",
            },
        )
    position_data = [
        ("coverage-a", "a", "I-A", "60000"),
        ("coverage-b", "b", "I-A", "80000" if balance_basis == "gross" else "30000"),
        ("coverage-c", "c", "I-A", "40000"),
        ("joint-a", "a", "I-B", "60000"),
        ("joint-b", "b", "I-B", "40000"),
        ("balance", "a", "I-C", "75000"),
        ("bond-a", "a", "SF-BOND-A", "2500"),
        ("bond-b", "b", "SF-BOND-B", "3500"),
        ("bond-zero", "b", "SF-BOND-A", "0"),
        ("bond-unknown", "a", "SF-BOND-B", None),
    ]
    for name, owner, source_id, quantity in position_data:
        instrument = by_key[source_id].instrument_node_id
        payload = {
            "position_id": f"sf:position:{name}",
            "account_id": f"sf:account:{owner}",
            "instrument_node_id": instrument,
            "location_id": "NYC",
            "convention_id": by_instrument[instrument].convention_id,
            "quantity": quantity,
            "balance_basis": balance_basis,
            "deduction_contract_id": "sf:balance:v1",
            "settlement_state": "settled",
            "ready_date": now.date().isoformat(),
            "snapshot_id": SNAPSHOT,
        }
        add(
            "inventory_position",
            payload,
            times={"effective_from": now - timedelta(hours=1)},
        )
        if name == "coverage-a":
            add(
                "inventory_position",
                {**payload, "quantity": "55000"},
                version="v0",
                times={
                    "effective_to": now - timedelta(hours=1),
                    "source_available_at": now - timedelta(days=2),
                    "source_confirmed_at": now - timedelta(days=2),
                    "recorded_from": now - timedelta(days=2),
                    "recorded_to": now - timedelta(seconds=30),
                },
            )
    request_data = [
        ("coverage", "I-A", "100000", "coverage", "one"),
        ("joint-one", "I-B", "60000", "joint-one", "one"),
        ("joint-two", "I-B", "40000", "joint-two", "two"),
        ("balance-one", "I-C", "100000", "balance", "one"),
        ("balance-two", "I-C", "50000", "balance", "one"),
        ("bond-a", "SF-BOND-A", "3000", "bonds", "one"),
        ("bond-b", "SF-BOND-B", "3500", "bonds", "one"),
    ]
    for index, (name, source_id, quantity, agreement, borrower) in enumerate(
        request_data
    ):
        instrument = by_key[source_id].instrument_node_id
        payload = {
            "request_id": f"sf:request:{name}",
            "borrower_party_id": f"sf:party:borrower-{borrower}",
            "instrument_node_id": instrument,
            "location_id": "NYC",
            "convention_id": by_instrument[instrument].convention_id,
            "open_quantity": quantity,
            "required_date": (now + timedelta(days=1)).date().isoformat(),
            "priority_tier": 1 if index % 2 == 0 else 2,
            "agreement_id": f"sf:agreement:{agreement}",
            "input_kind": "open_request",
            "snapshot_id": SNAPSHOT,
        }
        order = (
            TimestampEvidence(now.date().isoformat(), "date", "UTC")
            if name == "coverage"
            else TimestampEvidence(
                iso(now - timedelta(minutes=30 - index)), "instant", "UTC"
            )
        )
        payload.update(
            request_order_at_value=order.value,
            request_order_at_precision=order.precision,
            request_order_at_source_timezone=order.source_timezone,
        )
        add("borrow_request", payload)
    add(
        "capacity_component",
        {
            "component_id": "sf:component:reserved-b",
            "position_id": "sf:position:coverage-b",
            "kind": "reservation",
            "quantity": "50000",
            "status": "active",
            "overlap_group_id": None,
            "snapshot_id": SNAPSHOT,
        },
    )
    instrument = by_key["I-A"].instrument_node_id
    for name, quantity in (("covered", "20000"), ("unrelated", "8000")):
        add(
            "loan",
            {
                "loan_id": f"sf:loan:{name}",
                "agreement_id": "sf:agreement:coverage",
                "instrument_node_id": instrument,
                "convention_id": by_instrument[instrument].convention_id,
                "outstanding_quantity": quantity,
                "status": "open",
                "input_kind": "outstanding_loan",
                "snapshot_id": SNAPSHOT,
            },
        )
    for name, position, quantity in (
        ("one", "coverage-a", "15000"),
        ("two", "coverage-b", "5000"),
    ):
        add(
            "loan_allocation",
            {
                "allocation_id": f"sf:allocation:{name}",
                "loan_id": "sf:loan:covered",
                "position_id": f"sf:position:{position}",
                "outstanding_quantity": quantity,
                "snapshot_id": SNAPSHOT,
            },
        )
    event_data = [
        (
            "reserve",
            "reservation_create",
            "sf:component:reserved-b",
            "50000",
            -10,
            None,
        ),
        ("returned", "return_settle", "sf:allocation:one", "1000", -10, None),
        ("recall", "recall_issue", "sf:loan:covered", "20000", -5, None),
        ("future-return", "return_settle", "sf:allocation:two", "500", 5, None),
        (
            "reverse-return",
            "return_reverse",
            "sf:allocation:one",
            "1000",
            10,
            "sf:event:returned",
        ),
        (
            "cancel-recall",
            "recall_cancel",
            "sf:loan:covered",
            "20000",
            15,
            "sf:event:recall",
        ),
        (
            "release",
            "reservation_release",
            "sf:component:reserved-b",
            "50000",
            20,
            "sf:event:reserve",
        ),
    ]
    for name, kind, target, quantity, minutes, reverse in event_data:
        component, _, status = EVENTS[kind]
        times = {"effective_at": now + timedelta(minutes=minutes)}
        if minutes > 0:
            times.update(
                {
                    key: now + timedelta(minutes=minutes)
                    for key in (
                        "source_available_at",
                        "source_confirmed_at",
                        "recorded_from",
                    )
                }
            )
        event_id = f"sf:event:{name}"
        add(
            "lifecycle_event",
            {
                "event_id": event_id,
                "event_stream_id": EVENT_STREAM,
                "event_type": kind,
                "state_component": component,
                "target_record_id": target,
                "quantity": quantity,
                "status": status,
                "supersedes_version_id": None,
                "reverses_event_id": reverse,
            },
            times=times,
        )
        if name in ("reserve", "returned"):
            add(
                "snapshot_included_events",
                {
                    "snapshot_id": SNAPSHOT,
                    "state_component": component,
                    "target_record_id": target,
                    "source_name": SOURCE,
                    "event_id": event_id,
                    "event_version_id": f"{event_id}:v1",
                },
            )
    for position, _, source_id, _ in position_data:
        for request, request_instrument, _, _, _ in request_data:
            if source_id != request_instrument:
                continue
            convention = by_instrument[by_key[source_id].instrument_node_id]
            add(
                "net_benefit",
                {
                    "coefficient_id": f"sf:benefit:{position}:{request}",
                    "position_id": f"sf:position:{position}",
                    "request_id": f"sf:request:{request}",
                    "convention_id": convention.convention_id,
                    "net_benefit_amount": "-0.250000"
                    if position == "bond-unknown"
                    else "0.500000"
                    if convention.quantity_unit == "nominal"
                    else "0.050000",
                    "basis_quantity": "1000"
                    if convention.quantity_unit == "nominal"
                    else "1",
                    "currency": settings["earnings"]["currency"],
                    "horizon_id": settings["earnings"]["horizon_id"],
                    "horizon_start": settings["earnings"]["horizon_start"],
                    "horizon_end": settings["earnings"]["horizon_end"],
                    "method_version": "supplied-net-benefit-v1",
                    "assumption_reference": "synthetic:already-net-benefit-for-declared-horizon",
                },
            )
    return {name: tuple(values) for name, values in rows.items()}


def write_fixture_inputs(
    output: str | Path,
    *,
    settings_path: str | Path,
    selected_format: str = "json",
    balance_basis: str = "gross",
) -> Path:
    """Validate both encodings before installing an immutable input directory."""
    _require(
        selected_format in ("json", "csv"),
        "unsupported_format",
        "JSON or CSV authority required",
    )
    with Path(settings_path).open("rb") as stream:
        settings_bytes = stream.read(MAX_FILE_BYTES + 1)
    settings = load_settings(settings_bytes)
    tables, _ = normalize_tables(
        _fixture_rows(settings, balance_basis), {name: SOURCE for name in SCHEMAS}
    )
    files = {"settings.toml": settings_bytes}
    datasets = []
    for name in SCHEMAS:
        entries = []
        for format in ("json", "csv"):
            path = f"{format}/{name}.{format}"
            raw = encode_table(
                name, (record.to_row() for record in tables[name]), format
            )
            files[path] = raw
            entries.append(
                {
                    "path": path,
                    "format": format,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        datasets.append(
            {
                "dataset_id": f"sf:{name}:v1",
                "logical_dataset_id": f"sf:{name}",
                "record_type": name,
                "schema_version": 1,
                "source_name": SOURCE,
                "selected_format": selected_format,
                "files": entries,
                (
                    "event_stream_id" if name == "lifecycle_event" else "snapshot_id"
                ): EVENT_STREAM if name == "lifecycle_event" else SNAPSHOT,
            }
        )
    manifest = {
        "schema_version": 1,
        "classification": "synthetic",
        "datasets": datasets,
        "instrument_catalog": "sf:instrument_catalog:v1",
        "cutoffs": {
            name: settings["time"][name]
            for name in ("business_as_of", "knowledge_cutoff", "system_cutoff")
        },
        "settings_file": {
            "path": "settings.toml",
            "sha256": hashlib.sha256(settings_bytes).hexdigest(),
        },
    }
    manifest["manifest_id"] = sha256(manifest)
    files["manifest.json"] = canonical_bytes(manifest)
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / manifest["manifest_id"]
    _require(
        not destination.is_symlink(), "invalid_output", "output must not be a symlink"
    )
    with tempfile.TemporaryDirectory(prefix=".sf-input-", dir=root) as temporary:
        staging = Path(temporary)
        for path, raw in files.items():
            target = staging / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        read_input_pack(staging)
        if destination.exists():
            _require(
                not destination.is_symlink(),
                "invalid_output",
                "existing output must not be a symlink",
            )
            existing = read_input_pack(destination)
            _require(
                existing.manifest_id == manifest["manifest_id"],
                "output_conflict",
                "existing directory identity differs",
            )
        else:
            staging.rename(destination)
    return destination
