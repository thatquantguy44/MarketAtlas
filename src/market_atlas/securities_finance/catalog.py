"""Immutable file-first references; no database lookup, writes or publication."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from market_atlas.fixtures import build_fixture
from market_atlas.graph.fixture_loader import stable_id
from market_atlas.securities_finance.contracts import (
    InstrumentReference,
    QuantityConvention,
    QuantityValue,
    _require,
    _text,
)


@dataclass(frozen=True, slots=True)
class ReferenceCatalog:
    """One explicitly selected set of instrument/convention versions."""

    instruments: tuple[InstrumentReference, ...]
    conventions: tuple[QuantityConvention, ...]
    schema_version: int = 1
    classification: str = "synthetic"
    _instruments: Mapping[str, InstrumentReference] = field(
        init=False, repr=False, compare=False
    )
    _conventions: Mapping[str, QuantityConvention] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require(
            type(self.schema_version) is int and self.schema_version == 1,
            "unsupported_schema_version",
            "schema version 1 required",
        )
        _require(
            self.classification == "synthetic",
            "invalid_classification",
            "synthetic catalog required",
        )
        _require(
            isinstance(self.instruments, tuple) and isinstance(self.conventions, tuple),
            "invalid_catalog",
            "immutable typed tuples required",
        )
        instruments: dict[str, InstrumentReference] = {}
        keys: set[str] = set()
        for reference in self.instruments:
            _require(
                isinstance(reference, InstrumentReference),
                "invalid_reference",
                "typed instrument required",
            )
            _require(
                reference.instrument_node_id not in instruments
                and reference.canonical_key not in keys,
                "duplicate_instrument",
                "node IDs and canonical keys must be unique",
            )
            instruments[reference.instrument_node_id] = reference
            keys.add(reference.canonical_key)
        conventions: dict[str, QuantityConvention] = {}
        for convention in self.conventions:
            _require(
                isinstance(convention, QuantityConvention),
                "invalid_convention",
                "typed convention required",
            )
            _require(
                convention.convention_id not in conventions,
                "duplicate_convention",
                "convention IDs must be unique",
            )
            reference = instruments.get(convention.instrument_node_id)
            _require(
                reference is not None,
                "unknown_instrument",
                "convention references an absent instrument",
            )
            expected = "share" if reference.asset_class == "equity" else "nominal"
            _require(
                convention.quantity_unit == expected,
                "asset_unit_mismatch",
                "unit does not match asset class",
            )
            conventions[convention.convention_id] = convention
        object.__setattr__(self, "_instruments", MappingProxyType(instruments))
        object.__setattr__(self, "_conventions", MappingProxyType(conventions))

    def instrument(self, instrument_node_id: str) -> InstrumentReference:
        _text(instrument_node_id, "instrument_node_id")
        result = self._instruments.get(instrument_node_id)
        _require(
            result is not None, "unknown_instrument", "no declared instrument reference"
        )
        return result

    def convention(self, convention_id: str) -> QuantityConvention:
        _text(convention_id, "convention_id")
        result = self._conventions.get(convention_id)
        _require(
            result is not None, "unknown_convention", "no declared quantity convention"
        )
        return result

    def validate_quantity(
        self,
        instrument_node_id: str,
        convention_id: str,
        value: QuantityValue,
        *,
        for_allocation: bool = False,
    ) -> int | None:
        self.instrument(instrument_node_id)
        convention = self.convention(convention_id)
        _require(
            convention.instrument_node_id == instrument_node_id,
            "instrument_convention_mismatch",
            "convention belongs to another instrument",
        )
        return convention.validate_quantity(value, for_allocation=for_allocation)


def build_reference_catalog() -> ReferenceCatalog:
    """Build only the declared WP-02A references, independently of wall-clock time.

    Runtime TOML decoding and full JSON/CSV source fixtures belong to WP-02B.
    The equity convention setting is a template, bound to each instrument below.
    """
    entities = {row["id"]: row for row in build_fixture()["entities"]}
    instruments: list[InstrumentReference] = []
    conventions: list[QuantityConvention] = []
    for source_id in ("I-A", "I-B", "I-C"):
        row = entities.get(source_id)
        _require(
            row is not None, "missing_base_reference", "base fixture share is absent"
        )
        reference = InstrumentReference(
            str(stable_id("node", source_id)),
            f"fixture:{source_id}",
            row["type"],
            "equity",
            row["label"],
            f"synthetic-fixture:{source_id}",
        )
        instruments.append(reference)
        conventions.append(
            QuantityConvention(
                f"equity-whole-v1:{source_id}",
                reference.instrument_node_id,
                "share",
                None,
                0,
                "1",
                "1",
            )
        )
    for source_id, convention_id, minimum in (
        ("SF-BOND-A", "bond-a-v1", "2000"),
        ("SF-BOND-B", "bond-b-v1", "1500"),
    ):
        reference = InstrumentReference(
            str(stable_id("node", source_id)),
            f"fixture:{source_id}",
            "instrument",
            "fixed_income",
            f"Synthetic Bond {source_id[-1]}",
            f"secfin-reference-v1:{source_id}",
        )
        instruments.append(reference)
        conventions.append(
            QuantityConvention(
                convention_id,
                reference.instrument_node_id,
                "nominal",
                "USD",
                0,
                minimum,
                "1000",
            )
        )
    return ReferenceCatalog(tuple(instruments), tuple(conventions))
