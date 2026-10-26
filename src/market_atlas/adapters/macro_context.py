"""Bounded read-only adapter for approved MacroMedallion context interfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from market_atlas.adapters.macro_medallion import _read_only_connection, _validate_iso_date
from market_atlas.config import MacroContextConfig, SourceDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.source_contracts import contracts_by_object, load_source_contract_registry

SERIES_DIMENSION_OBJECT = "gold.dim_series"
RELEASE_CALENDAR_OBJECT = "gold.release_calendar"
SOURCE_COVERAGE_OBJECT = "gold.v_source_coverage"
CONTEXT_OBJECTS = (
    SERIES_DIMENSION_OBJECT,
    RELEASE_CALENDAR_OBJECT,
    SOURCE_COVERAGE_OBJECT,
)
_CONTRACTS = contracts_by_object(load_source_contract_registry())
REQUIRED_COLUMNS = {
    object_name: set(_CONTRACTS[object_name]["required_columns"])
    for object_name in CONTEXT_OBJECTS
}


def verify_contract(database: SourceDatabaseConfig) -> dict[str, Any]:
    """Verify columns and read-only access for the approved context interfaces."""
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT table_schema || '.' || table_name AS object_name, column_name
                FROM information_schema.columns
                WHERE (table_schema, table_name) IN (
                    ('gold', 'dim_series'),
                    ('gold', 'release_calendar'),
                    ('gold', 'v_source_coverage')
                )
            """
        )
        found: dict[str, set[str]] = {name: set() for name in CONTEXT_OBJECTS}
        for object_name, column_name in cursor.fetchall():
            if object_name in found:
                found[object_name].add(column_name)
        cursor.execute("SHOW transaction_read_only")
        read_only = cursor.fetchone()[0] == "on"
        cursor.execute(
            """
                SELECT has_table_privilege(current_user, 'gold.dim_series', 'INSERT,UPDATE,DELETE')
                    OR has_table_privilege(current_user, 'gold.release_calendar', 'INSERT,UPDATE,DELETE')
                    OR has_table_privilege(current_user, 'gold.v_source_coverage', 'INSERT,UPDATE,DELETE')
            """
        )
        role_has_source_write_privileges = bool(cursor.fetchone()[0])

    missing = {
        object_name: sorted(required - found[object_name])
        for object_name, required in REQUIRED_COLUMNS.items()
        if required - found[object_name]
    }
    return {
        "status": "valid" if not missing and read_only else "invalid",
        "acceptance_ready": not role_has_source_write_privileges,
        "read_only_session": read_only,
        "role_has_source_write_privileges": role_has_source_write_privileges,
        "objects": {
            name: {
                "required_columns": sorted(columns),
                "missing_columns": missing.get(name, []),
            }
            for name, columns in REQUIRED_COLUMNS.items()
        },
    }


def extract(
    database: SourceDatabaseConfig,
    pilot: MacroContextConfig,
) -> dict[str, Any]:
    """Extract bounded current taxonomy, release events, and coverage records."""
    release_start = _validate_iso_date(pilot.release_start, "release_start")
    release_end = _validate_iso_date(pilot.release_end, "release_end")
    if release_end < release_start:
        raise ValueError("release_end must be on or after release_start")

    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT series_id, title, source, frequency, units, econ_category,
                       polarity, default_transform, scale, decimals, notes, geo, metric
                FROM gold.dim_series
                WHERE series_id = ANY(%s)
                ORDER BY series_id
            """,
            (list(pilot.series_ids),),
        )
        series_columns = [column.name for column in cursor.description]
        series_taxonomy = [
            dict(zip(series_columns, row, strict=True)) for row in cursor.fetchall()
        ]
        found_ids = {row["series_id"] for row in series_taxonomy}
        missing_ids = sorted(set(pilot.series_ids) - found_ids)
        if missing_ids:
            raise ValueError(
                f"configured MacroMedallion context series not found: {', '.join(missing_ids)}"
            )

        cursor.execute(
            """
                SELECT release_id, release_name, release_date, importance,
                       econ_category, representative_series_id, is_future, fetched_at
                FROM gold.release_calendar
                WHERE release_date >= %s AND release_date <= %s
                ORDER BY release_date, release_id
            """,
            (release_start.isoformat(), release_end.isoformat()),
        )
        release_columns = [column.name for column in cursor.description]
        releases = [
            dict(zip(release_columns, row, strict=True)) for row in cursor.fetchall()
        ]

        cursor.execute(
            """
                SELECT source, series_id, category, frequency,
                       latest_observation_date, observation_count, days_since_last, is_stale
                FROM gold.v_source_coverage
                WHERE series_id = ANY(%s)
                ORDER BY source, series_id
            """,
            (list(pilot.series_ids),),
        )
        coverage_columns = [column.name for column in cursor.description]
        coverage = [
            dict(zip(coverage_columns, row, strict=True)) for row in cursor.fetchall()
        ]

    input_selection = {
        "source": "macro_medallion_postgresql",
        "objects": list(CONTEXT_OBJECTS),
        "series_ids": list(pilot.series_ids),
        "release_start": pilot.release_start,
        "release_end": pilot.release_end,
    }
    return {
        "manifest": {
            **input_selection,
            "input_selection_sha256": sha256(input_selection),
            "source_rows_sha256": sha256(
                {
                    "series_taxonomy": series_taxonomy,
                    "release_events": releases,
                    "source_coverage": coverage,
                }
            ),
            "extracted_at": datetime.now(UTC).isoformat(),
            "redistribution_status": pilot.redistribution_status,
            "series_taxonomy_temporal_status": "current_only",
            "release_event_temporal_status": "scheduled_date_with_source_fetched_at",
            "coverage_temporal_status": "current_only",
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
        },
        "series_taxonomy": series_taxonomy,
        "release_events": releases,
        "source_coverage": coverage,
    }


def extract_series_catalog(
    database: SourceDatabaseConfig, page_size: int = 500, include_coverage: bool = False
) -> dict[str, Any]:
    """Extract every approved current taxonomy record in bounded source pages.

    Coverage is deliberately opt-in: the source coverage view is useful for a
    small, selected neighborhood, but a full-catalog scan can be materially
    more expensive than reading the approved taxonomy dimension.
    """
    if not 1 <= page_size <= 1_000:
        raise ValueError("series catalog page_size must be between 1 and 1000")
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT series_id, title, source, frequency, units, econ_category,
                   polarity, default_transform, scale, decimals, notes, geo, metric
            FROM gold.dim_series
            ORDER BY series_id
            """
        )
        series_columns = [column.name for column in cursor.description]
        series_taxonomy: list[dict[str, Any]] = []
        while rows := cursor.fetchmany(page_size):
            series_taxonomy.extend(
                dict(zip(series_columns, row, strict=True)) for row in rows
            )
        if not series_taxonomy:
            raise ValueError("approved series catalog returned no rows")

        coverage: list[dict[str, Any]] = []
        series_ids = [row["series_id"] for row in series_taxonomy]
        if include_coverage:
            for start in range(0, len(series_ids), page_size):
                cursor.execute(
                    """
                    SELECT source, series_id, category, frequency,
                           latest_observation_date, observation_count, days_since_last, is_stale
                    FROM gold.v_source_coverage
                    WHERE series_id = ANY(%s)
                    ORDER BY source, series_id
                    """,
                    (series_ids[start : start + page_size],),
                )
                coverage_columns = [column.name for column in cursor.description]
                coverage.extend(
                    dict(zip(coverage_columns, row, strict=True)) for row in cursor.fetchall()
                )

    input_selection = {
        "source": "macro_medallion_postgresql",
        "objects": [SERIES_DIMENSION_OBJECT]
        + ([SOURCE_COVERAGE_OBJECT] if include_coverage else []),
        "series_ids": series_ids,
        "release_start": None,
        "release_end": None,
        "selection_scope": "all_approved_dim_series",
        "page_size": page_size,
        "include_coverage": include_coverage,
    }
    return {
        "manifest": {
            **input_selection,
            "input_selection_sha256": sha256(input_selection),
            "source_rows_sha256": sha256(
                {
                    "series_taxonomy": series_taxonomy,
                    "release_events": [],
                    "source_coverage": coverage,
                }
            ),
            "extracted_at": datetime.now(UTC).isoformat(),
            "redistribution_status": "unresolved",
            "series_taxonomy_temporal_status": "current_only",
            "release_event_temporal_status": "not_selected",
            "coverage_temporal_status": "current_only" if include_coverage else "not_selected",
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
        },
        "series_taxonomy": series_taxonomy,
        "release_events": [],
        "source_coverage": coverage,
    }
