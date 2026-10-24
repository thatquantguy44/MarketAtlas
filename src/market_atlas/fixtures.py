"""Deterministic, wholly synthetic inputs for the MarketAtlas pilot."""

from __future__ import annotations

from datetime import date, timedelta

FIXTURE_VERSION = "synthetic-v1"


def _sessions(count: int = 75) -> list[str]:
    current = date(2024, 1, 2)
    days: list[str] = []
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def build_fixture() -> dict:
    """Return the same synthetic records on every call, independent of the clock."""
    sessions = _sessions()
    entities = [
        {"id": "I-A", "type": "instrument", "label": "Synthetic Alpha Share"},
        {"id": "I-B", "type": "instrument", "label": "Synthetic Beta Share"},
        {"id": "I-C", "type": "instrument", "label": "Synthetic Constant Share"},
        {"id": "L-A", "type": "listing", "label": "Alpha Demo Listing"},
        {"id": "L-B", "type": "listing", "label": "Beta Demo Listing"},
        {"id": "L-C", "type": "listing", "label": "Constant Demo Listing"},
        {"id": "O-A", "type": "issuer", "label": "Alpha Fictional Corp"},
        {"id": "O-B", "type": "issuer", "label": "Beta Fictional Corp"},
        {"id": "S-TECH", "type": "sector", "label": "Synthetic Technology"},
        {"id": "S-IND", "type": "sector", "label": "Synthetic Industrials"},
        {"id": "C-US", "type": "country", "label": "Synthetic US"},
        {"id": "CCY-USD", "type": "currency", "label": "Synthetic USD"},
        {"id": "IDX-DEMO", "type": "index", "label": "Synthetic Broad Index"},
        {"id": "EC-GROWTH", "type": "economic_concept", "label": "Growth"},
        {"id": "M-GROWTH", "type": "macro_series", "label": "Synthetic Growth Index"},
    ]
    identifiers = [
        {
            "entity_id": "L-A",
            "source": "fixture-exchange",
            "scheme": "ticker",
            "value": "OLDX",
            "valid_from": "2024-01-02",
            "valid_to": sessions[35],
        },
        {
            "entity_id": "L-A",
            "source": "fixture-exchange",
            "scheme": "ticker",
            "value": "NEWX",
            "valid_from": sessions[35],
            "valid_to": None,
        },
        {
            "entity_id": "L-B",
            "source": "fixture-exchange",
            "scheme": "ticker",
            "value": "BETA",
            "valid_from": "2024-01-02",
            "valid_to": None,
        },
        {
            "entity_id": "L-C",
            "source": "fixture-exchange",
            "scheme": "ticker",
            "value": "FLAT",
            "valid_from": "2024-01-02",
            "valid_to": None,
        },
    ]

    def assertion(
        key: str,
        source: str,
        target: str,
        predicate: str,
        *,
        available_at: str = "2024-01-02T12:00:00Z",
        recorded_at: str | None = None,
        status: str = "accepted",
        kind: str = "reference",
        rationale: str | None = None,
        assertion_key: str | None = None,
        supersedes_id: str | None = None,
    ) -> dict:
        return {
            "id": key,
            "source_id": source,
            "target_id": target,
            "predicate": predicate,
            "kind": kind,
            "status": status,
            "valid_from": "2024-01-02",
            "valid_to": None,
            "available_at": available_at,
            "recorded_at": recorded_at or available_at,
            "provenance": "synthetic-fixture",
            "rationale": rationale,
            "assertion_key": assertion_key or key,
            "supersedes_id": supersedes_id,
        }

    assertions = [
        assertion("A1", "L-A", "I-A", "lists"),
        assertion("A2", "L-B", "I-B", "lists"),
        assertion("A3", "L-C", "I-C", "lists"),
        assertion("A4", "I-A", "O-A", "issued_by"),
        assertion("A5", "I-B", "O-B", "issued_by"),
        assertion(
            "A6", "O-A", "S-TECH", "classified_as", assertion_key="REL-ALPHA-TECH"
        ),
        assertion("A7", "O-A", "IDX-DEMO", "member_of"),
        assertion(
            "A8",
            "O-A",
            "S-IND",
            "classified_as",
            status="disputed",
            available_at="2024-04-01T12:00:00Z",
        ),
        assertion("A9", "L-A", "C-US", "listed_in"),
        assertion("A10", "I-A", "CCY-USD", "denominated_in"),
        assertion("A11", "M-GROWTH", "EC-GROWTH", "measures"),
        assertion("A12", "M-GROWTH", "C-US", "covers"),
        assertion(
            "A13",
            "S-TECH",
            "M-GROWTH",
            "context_for",
            kind="curated_context",
            rationale="Illustrative mapping only; not a measured sensitivity.",
        ),
        assertion(
            "A14",
            "O-B",
            "S-IND",
            "classified_as",
            available_at="2024-04-15T12:00:00Z",
            recorded_at="2024-05-01T12:00:00Z",
            rationale="Late-arriving reference fact fixture",
        ),
        assertion(
            "A15",
            "O-A",
            "S-TECH",
            "classified_as",
            available_at="2024-04-02T12:00:00Z",
            recorded_at="2024-04-03T12:00:00Z",
            status="retracted",
            rationale="Synthetic correction retracting the original classification.",
            assertion_key="REL-ALPHA-TECH",
            supersedes_id="A6",
        ),
    ]

    prices: list[dict] = []
    price_a, price_b = 100.0, 80.0
    for index, session in enumerate(sessions):
        if index:
            price_a *= 1 + (0.0015 + (index % 7 - 3) * 0.001)
            price_b *= 1 + (0.001 + (index % 7 - 3) * 0.0008 + (index % 3 - 1) * 0.0002)
        for instrument, value in (("I-A", price_a), ("I-B", price_b), ("I-C", 50.0)):
            # A missing price must not be forward-filled into a daily return.
            if instrument == "I-B" and index in (12, 34, 51):
                continue
            prices.append(
                {
                    "instrument_id": instrument,
                    "session": session,
                    "value": round(value, 8),
                    "unit": "USD",
                    "measure": "adjusted_close",
                    "adjustment": "synthetic-none",
                    "available_at": session + "T22:00:00Z",
                    "source_record": f"synthetic-price-{instrument}-{index}",
                }
            )

    macro = [
        {
            "series_id": "M-GROWTH",
            "period": "2024-01",
            "value": 101.0,
            "unit": "index",
            "frequency": "monthly",
            "vintage": "initial",
            "available_at": "2024-02-05T13:00:00Z",
            "source_record": "synthetic-macro-initial",
        },
        {
            "series_id": "M-GROWTH",
            "period": "2024-01",
            "value": 101.4,
            "unit": "index",
            "frequency": "monthly",
            "vintage": "revision",
            "available_at": "2024-03-05T13:00:00Z",
            "source_record": "synthetic-macro-revision",
        },
    ]
    curated_contexts = [
        {
            "id": "CTX1",
            "macro_series_id": "M-GROWTH",
            "target_id": "C-US",
            "mapping_kind": "series_country",
            "evidence_basis": "source_backed",
            "rationale": "Synthetic coverage mapping for the series; context only, not measured sensitivity or causality.",
            "mapping_owner": "synthetic-mapping-owner",
            "source_reference": "synthetic-fixture:A12",
            "taxonomy_provider": "synthetic-geography",
            "taxonomy_version": "v1",
            "supporting_assertion_id": "A12",
            "valid_from": "2024-01-02",
            "valid_to": None,
            "available_at": "2024-01-02T12:00:00Z",
            "recorded_at": "2024-01-02T12:00:00Z",
            "provenance": "synthetic-fixture",
        },
        {
            "id": "CTX2",
            "macro_series_id": "M-GROWTH",
            "target_id": "EC-GROWTH",
            "mapping_kind": "series_concept",
            "evidence_basis": "source_backed",
            "rationale": "Synthetic measurement mapping for the series; context only, not measured sensitivity or causality.",
            "mapping_owner": "synthetic-mapping-owner",
            "source_reference": "synthetic-fixture:A11",
            "taxonomy_provider": "synthetic-economic-concepts",
            "taxonomy_version": "v1",
            "supporting_assertion_id": "A11",
            "valid_from": "2024-01-02",
            "valid_to": None,
            "available_at": "2024-01-02T12:00:00Z",
            "recorded_at": "2024-01-02T12:00:00Z",
            "provenance": "synthetic-fixture",
        },
        {
            "id": "CTX3",
            "macro_series_id": "M-GROWTH",
            "target_id": "S-TECH",
            "mapping_kind": "market_context",
            "evidence_basis": "curated",
            "rationale": "Illustrative sector context chosen by the mapping owner; not measured sensitivity or causality.",
            "mapping_owner": "synthetic-mapping-owner",
            "source_reference": "synthetic-fixture:A13",
            "taxonomy_provider": "synthetic-sector-taxonomy",
            "taxonomy_version": "v1",
            "supporting_assertion_id": "A13",
            "valid_from": "2024-01-02",
            "valid_to": None,
            "available_at": "2024-01-02T12:00:00Z",
            "recorded_at": "2024-01-02T12:00:00Z",
            "provenance": "synthetic-fixture",
        },
    ]
    return {
        "metadata": {
            "fixture_version": FIXTURE_VERSION,
            "synthetic": True,
            "license": "generated-synthetic",
            "calendar": "synthetic-weekdays-no-holidays",
            "source": "market-atlas-fixture",
        },
        "sessions": sessions,
        "entities": entities,
        "identifiers": identifiers,
        "assertions": assertions,
        "market_observations": prices,
        "macro_observations": macro,
        "curated_contexts": curated_contexts,
        "configured_pairs": [["I-A", "I-B"], ["I-A", "I-C"]],
    }
