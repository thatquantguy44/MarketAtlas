"""Typed normalized contracts for the file-first securities-finance pilot.

These checks establish structural validity, never eligibility or available supply.
Format adapters and temporal selection are separate implementation slices.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import MISSING, dataclass, field, fields
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

QuantityUnit = Literal["share", "nominal"]
MAX_QUANTITY_PRECISION = 18
MAX_DECIMAL_TEXT_LENGTH = 128
RECORD_TYPES = frozenset(
    {
        "instrument_catalog",
        "quantity_convention",
        "legal_entity",
        "account",
        "inventory_position",
        "deduction_contract",
        "capacity_component",
        "borrow_request",
        "agreement",
        "agreement_parties",
        "agreement_instruments",
        "agreement_locations",
        "loan",
        "loan_allocation",
        "lifecycle_event",
        "snapshot_included_events",
        "net_benefit",
    }
)


class ContractError(ValueError):
    """Inspectable failure without silently repairing an invalid input."""

    def __init__(self, code: str, message: str, *, field: str = "") -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field + ': ' if field else ''}{message}")


def _require(condition: bool, code: str, message: str, field: str = "") -> None:
    if not condition:
        raise ContractError(code, message, field=field)


def _text(value: object, name: str) -> None:
    _require(
        isinstance(value, str) and bool(value) and value == value.strip(),
        "invalid_identifier",
        "expected nonempty text without surrounding whitespace",
        name,
    )


def _constructor_fields(model: type, values: Mapping[str, object]) -> dict[str, object]:
    _require(isinstance(values, Mapping), "invalid_fields", "expected a field mapping")
    _require(
        all(isinstance(key, str) for key in values),
        "invalid_fields",
        "text keys required",
    )
    definitions = {item.name: item for item in fields(model) if item.init}
    unknown = set(values) - definitions.keys()
    missing = {
        name
        for name, item in definitions.items()
        if item.default is MISSING
        and item.default_factory is MISSING
        and name not in values
    }
    _require(not unknown, "unexpected_fields", ", ".join(sorted(unknown)))
    _require(not missing, "missing_fields", ", ".join(sorted(missing)))
    return dict(values)


@dataclass(frozen=True, slots=True)
class TimestampEvidence:
    """Retained source precision; date evidence is never a fabricated instant."""

    value: str
    precision: Literal["instant", "date"]
    source_timezone: str | None = None

    def __post_init__(self) -> None:
        _text(self.value, "value")
        _require(
            self.precision in ("instant", "date"),
            "invalid_time_precision",
            "instant or date required",
        )
        if self.source_timezone is not None:
            _text(self.source_timezone, "source_timezone")
            try:
                if self.source_timezone != "UTC":
                    ZoneInfo(self.source_timezone)
            except (ValueError, ZoneInfoNotFoundError) as error:
                raise ContractError(
                    "invalid_timezone", "unknown source timezone"
                ) from error
        try:
            if self.precision == "date":
                _require(
                    re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", self.value) is not None,
                    "invalid_timestamp",
                    "ISO date required",
                )
                date.fromisoformat(self.value)
            else:
                _require(
                    re.fullmatch(
                        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                        r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
                        self.value,
                    )
                    is not None,
                    "invalid_timestamp",
                    "offset-aware ISO time (up to microseconds) required",
                )
                datetime.fromisoformat(self.value).astimezone(UTC)
        except ContractError:
            raise
        except (ValueError, OverflowError) as error:
            raise ContractError(
                "invalid_timestamp", "invalid calendar date or time"
            ) from error

    def as_utc(self) -> datetime | None:
        if self.precision == "date":
            return None
        return datetime.fromisoformat(self.value).astimezone(UTC)

    @property
    def normalized_value(self) -> str:
        instant = self.as_utc()
        return (
            self.value
            if instant is None
            else instant.isoformat().replace("+00:00", "Z")
        )


@dataclass(frozen=True, slots=True)
class RecordKey:
    source_name: str
    record_type: str
    record_id: str
    version_id: str

    def __post_init__(self) -> None:
        for name in ("source_name", "record_type", "record_id", "version_id"):
            _text(getattr(self, name), name)
        _require(
            self.record_type in RECORD_TYPES,
            "unknown_record_type",
            "unsupported record type",
        )


@dataclass(frozen=True, slots=True)
class RecordEnvelope:
    """One version's three independent clocks; no cutoff selection is implied."""

    key: RecordKey
    effective_from: TimestampEvidence | None
    effective_to: TimestampEvidence | None
    source_available_at: TimestampEvidence | None
    source_confirmed_at: TimestampEvidence | None
    recorded_from: TimestampEvidence
    recorded_to: TimestampEvidence | None
    source_record_reference: str
    effective_at: TimestampEvidence | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        _require(
            type(self.schema_version) is int and self.schema_version == 1,
            "unsupported_schema_version",
            "schema version 1 required",
        )
        _require(
            isinstance(self.key, RecordKey),
            "invalid_record_key",
            "typed record key required",
        )
        _text(self.source_record_reference, "source_record_reference")
        for name in (
            "effective_from",
            "effective_to",
            "source_available_at",
            "source_confirmed_at",
            "recorded_from",
            "recorded_to",
            "effective_at",
        ):
            value = getattr(self, name)
            _require(
                value is None or isinstance(value, TimestampEvidence),
                "invalid_timestamp",
                "typed timestamp evidence required",
                name,
            )
        for name in ("recorded_from", "recorded_to"):
            value = getattr(self, name)
            _require(
                (value is not None or name == "recorded_to")
                and (value is None or value.precision == "instant"),
                "invalid_record_time",
                "system record times must be precise instants",
                name,
            )
        if self.key.record_type == "lifecycle_event":
            _require(
                self.effective_from is None and self.effective_to is None,
                "invalid_event_envelope",
                "events use effective_at, not state intervals",
            )
        else:
            _require(
                self.effective_at is None,
                "invalid_state_envelope",
                "state records use effective intervals",
            )
        for start, end in (
            (self.effective_from, self.effective_to),
            (self.recorded_from, self.recorded_to),
        ):
            if start is not None and end is not None:
                left, right = start.as_utc(), end.as_utc()
                if left is not None and right is not None:
                    _require(left < right, "invalid_interval", "end must follow start")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> RecordEnvelope:
        """Validate normalized fields; this does not decode JSON/CSV columns."""
        return cls(**_constructor_fields(cls, values))


def validate_unique_envelopes(
    records: Iterable[RecordEnvelope],
) -> tuple[RecordEnvelope, ...]:
    """Reject repeated version keys; active-version selection belongs to WP-02C."""
    result = tuple(records)
    seen: set[RecordKey] = set()
    for record in result:
        _require(
            isinstance(record, RecordEnvelope),
            "invalid_envelope",
            "typed envelope required",
        )
        _require(
            record.key not in seen,
            "duplicate_record_key",
            "source/version key repeated",
        )
        seen.add(record.key)
    return result


@dataclass(frozen=True, slots=True)
class InstrumentReference:
    """Declared catalog identity, not an assertion that a database row exists."""

    instrument_node_id: str
    canonical_key: str
    node_type: Literal["instrument"]
    asset_class: Literal["equity", "fixed_income"]
    label: str
    provenance_reference: str

    def __post_init__(self) -> None:
        for name in (
            "instrument_node_id",
            "canonical_key",
            "label",
            "provenance_reference",
        ):
            _text(getattr(self, name), name)
        try:
            canonical_id = str(UUID(self.instrument_node_id))
        except ValueError as error:
            raise ContractError("invalid_node_id", "canonical UUID required") from error
        _require(
            canonical_id == self.instrument_node_id,
            "invalid_node_id",
            "canonical UUID text required",
        )
        _require(
            self.node_type == "instrument",
            "invalid_node_type",
            "instrument node required",
        )
        _require(
            self.asset_class in ("equity", "fixed_income"),
            "invalid_asset_class",
            "unsupported asset class",
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> InstrumentReference:
        return cls(**_constructor_fields(cls, values))


def _quantity_metadata(unit: object, currency: object, precision: object) -> None:
    _require(unit in ("share", "nominal"), "invalid_unit", "share or nominal required")
    _require(
        type(precision) is int and 0 <= precision <= MAX_QUANTITY_PRECISION,
        "invalid_precision",
        f"integer precision from 0 to {MAX_QUANTITY_PRECISION} required",
    )
    if unit == "share":
        _require(
            currency is None, "invalid_currency", "shares have no nominal currency"
        )
        _require(precision == 0, "invalid_precision", "fractional equities unsupported")
    else:
        _require(
            isinstance(currency, str)
            and re.fullmatch(r"[A-Z]{3}", currency) is not None,
            "invalid_currency",
            "explicit three-letter nominal currency required",
        )


def _scaled_quantity(value: object, precision: int, name: str) -> int:
    _require(
        isinstance(value, str)
        and len(value) <= MAX_DECIMAL_TEXT_LENGTH
        and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is not None,
        "invalid_quantity",
        "expected finite nonnegative plain decimal text",
        name,
    )
    numerator, denominator = Decimal(value).as_integer_ratio()
    units, remainder = divmod(numerator * 10**precision, denominator)
    _require(
        remainder == 0,
        "quantity_precision_mismatch",
        "quantity cannot be represented at the declared precision",
        name,
    )
    return units


def _decimal_text(units: int, precision: int) -> str:
    if precision == 0:
        return str(units)
    whole, fraction = divmod(units, 10**precision)
    return f"{whole}.{fraction:0{precision}d}"


@dataclass(frozen=True, slots=True)
class QuantityValue:
    """Exact normalized amount; None remains unavailable, distinct from zero."""

    amount: str | None
    quantity_unit: QuantityUnit
    quantity_currency: str | None
    quantity_precision: int
    units: int | None = field(init=False)

    def __post_init__(self) -> None:
        _quantity_metadata(
            self.quantity_unit, self.quantity_currency, self.quantity_precision
        )
        units = (
            None
            if self.amount is None
            else _scaled_quantity(self.amount, self.quantity_precision, "amount")
        )
        object.__setattr__(self, "units", units)
        if units is not None:
            object.__setattr__(
                self, "amount", _decimal_text(units, self.quantity_precision)
            )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> QuantityValue:
        return cls(**_constructor_fields(cls, values))


@dataclass(frozen=True, slots=True)
class QuantityConvention:
    """One selected convention; minimums constrain new proposals, not balances."""

    convention_id: str
    instrument_node_id: str
    quantity_unit: QuantityUnit
    quantity_currency: str | None
    quantity_precision: int
    minimum_allocation: str
    allocation_increment: str
    increment_origin: Literal["minimum"] = "minimum"
    minimum_scope: Literal["proposal_edge"] = "proposal_edge"
    minimum_units: int = field(init=False)
    increment_units: int = field(init=False)

    def __post_init__(self) -> None:
        _text(self.convention_id, "convention_id")
        _text(self.instrument_node_id, "instrument_node_id")
        _quantity_metadata(
            self.quantity_unit, self.quantity_currency, self.quantity_precision
        )
        _require(
            self.increment_origin == "minimum"
            and self.minimum_scope == "proposal_edge",
            "unsupported_convention",
            "version 1 requires minimum-origin proposal-edge increments",
        )
        for name, target in (
            ("minimum_allocation", "minimum_units"),
            ("allocation_increment", "increment_units"),
        ):
            units = _scaled_quantity(getattr(self, name), self.quantity_precision, name)
            _require(units > 0, "invalid_convention", "must be positive", name)
            object.__setattr__(self, target, units)
            object.__setattr__(
                self, name, _decimal_text(units, self.quantity_precision)
            )
        if self.quantity_unit == "share":
            _require(
                self.minimum_units == self.increment_units == 1,
                "unsupported_convention",
                "equity fixtures require a one-share minimum and increment",
            )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> QuantityConvention:
        return cls(**_constructor_fields(cls, values))

    def validate_quantity(
        self, value: QuantityValue, *, for_allocation: bool = False
    ) -> int | None:
        _require(
            type(for_allocation) is bool,
            "invalid_validation_mode",
            "boolean allocation mode required",
        )
        _require(
            isinstance(value, QuantityValue), "invalid_quantity", "typed value required"
        )
        _require(
            (value.quantity_unit, value.quantity_currency, value.quantity_precision)
            == (self.quantity_unit, self.quantity_currency, self.quantity_precision),
            "quantity_convention_mismatch",
            "unit, nominal currency and precision must match the convention",
        )
        if value.units is None:
            _require(
                not for_allocation,
                "unknown_quantity",
                "unavailable quantity cannot allocate",
            )
            return None
        if for_allocation and value.units:
            _require(
                value.units >= self.minimum_units
                and (value.units - self.minimum_units) % self.increment_units == 0,
                "invalid_allocation_quantity",
                "positive proposal must satisfy its minimum and increment",
            )
        return value.units
