"""Bounded read-only adapter for approved MacroMedallion context interfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from numbers import Number
from typing import Any

from market_atlas.adapters.macro_medallion import (
    _read_only_connection,
    _validate_iso_date,
)
from market_atlas.config import MacroContextConfig, SourceDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.source_contracts import (
    contracts_by_object,
    load_source_contract_registry,
)

SERIES_DIMENSION_OBJECT = "gold.dim_series"
RELEASE_CALENDAR_OBJECT = "gold.release_calendar"
SOURCE_COVERAGE_OBJECT = "gold.v_source_coverage"
REVISION_SUMMARY_OBJECT = "gold.v_series_revision_summary"
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
REVISION_SUMMARY_COLUMNS = set(_CONTRACTS[REVISION_SUMMARY_OBJECT]["required_columns"])


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
            "redistribution_status": "restricted",
            "series_taxonomy_temporal_status": "current_only",
            "release_event_temporal_status": "not_selected",
            "coverage_temporal_status": "current_only" if include_coverage else "not_selected",
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
        },
        "series_taxonomy": series_taxonomy,
        "release_events": [],
        "source_coverage": coverage,
    }


def verify_revision_summary_contract(database: SourceDatabaseConfig) -> dict[str, Any]:
    """Verify the isolated current-only revision-quality source interface."""
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'gold'
                  AND table_name = 'v_series_revision_summary'
            """
        )
        found_columns = {row[0] for row in cursor.fetchall()}
        cursor.execute("SHOW transaction_read_only")
        read_only = cursor.fetchone()[0] == "on"
        cursor.execute(
            """
                SELECT has_table_privilege(
                    current_user,
                    'gold.v_series_revision_summary',
                    'INSERT,UPDATE,DELETE'
                )
            """
        )
        role_has_source_write_privileges = bool(cursor.fetchone()[0])

    missing_columns = sorted(REVISION_SUMMARY_COLUMNS - found_columns)
    return {
        "status": "valid" if not missing_columns and read_only else "invalid",
        "acceptance_ready": not role_has_source_write_privileges,
        "read_only_session": read_only,
        "role_has_source_write_privileges": role_has_source_write_privileges,
        "object": REVISION_SUMMARY_OBJECT,
        "required_columns": sorted(REVISION_SUMMARY_COLUMNS),
        "missing_columns": missing_columns,
    }


def extract_revision_summary(
    database: SourceDatabaseConfig, series_ids: list[str], page_size: int = 500
) -> dict[str, Any]:
    """Extract selected approved current revision-quality summaries in bounded pages."""
    if not 1 <= page_size <= 1_000:
        raise ValueError("revision summary page_size must be between 1 and 1000")
    if not series_ids or len(series_ids) != len(set(series_ids)):
        raise ValueError("revision summary requires unique selected series IDs")
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT series_id
                FROM gold.dim_series
                WHERE series_id = ANY(%s)
                ORDER BY series_id
            """,
            (series_ids,),
        )
        approved_series_ids = [row[0] for row in cursor.fetchall()]
        missing_approved_ids = sorted(set(series_ids) - set(approved_series_ids))
        if missing_approved_ids:
            raise ValueError(
                "revision summary series IDs are not approved in gold.dim_series: "
                + ", ".join(missing_approved_ids)
            )

        revision_summaries: list[dict[str, Any]] = []
        for start in range(0, len(approved_series_ids), page_size):
            cursor.execute(
                """
                    SELECT series_id, observation_count, avg_revision_count,
                           max_revision_count, avg_abs_revision_pct,
                           max_abs_revision_pct
                    FROM gold.v_series_revision_summary
                    WHERE series_id = ANY(%s)
                    ORDER BY series_id
                """,
                (approved_series_ids[start : start + page_size],),
            )
            columns = [column.name for column in cursor.description]
            revision_summaries.extend(
                dict(zip(columns, row, strict=True)) for row in cursor.fetchall()
            )
    return build_revision_summary_extract(approved_series_ids, revision_summaries, page_size)


def build_revision_summary_extract(
    series_ids: list[str], revision_summaries: list[dict[str, Any]], page_size: int = 500
) -> dict[str, Any]:
    """Build a checksum-backed, current-only revision-quality extract."""
    if not 1 <= page_size <= 1_000:
        raise ValueError("revision summary page_size must be between 1 and 1000")
    if not series_ids or any(not isinstance(series_id, str) or not series_id for series_id in series_ids):
        raise ValueError("revision summary requires nonempty selected series IDs")
    if len(series_ids) != len(set(series_ids)):
        raise ValueError("revision summary selected series IDs must not contain duplicates")

    selected = set(series_ids)
    required = (
        "series_id",
        "observation_count",
        "avg_revision_count",
        "max_revision_count",
        "avg_abs_revision_pct",
        "max_abs_revision_pct",
    )
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for row in revision_summaries:
        if not isinstance(row, dict) or any(field not in row for field in required):
            raise ValueError("revision summary rows require every declared field")
        series_id = row["series_id"]
        if not isinstance(series_id, str) or series_id not in selected:
            raise ValueError("revision summary row references an unselected series")
        if series_id in seen:
            raise ValueError(f"revision summary has duplicate series_id: {series_id}")
        if not isinstance(row["observation_count"], int) or row["observation_count"] < 0:
            raise ValueError("revision summary observation_count must be a nonnegative integer")
        if not isinstance(row["max_revision_count"], int) or row["max_revision_count"] < 0:
            raise ValueError("revision summary max_revision_count must be a nonnegative integer")
        for field in ("avg_revision_count", "avg_abs_revision_pct", "max_abs_revision_pct"):
            if (
                not isinstance(row[field], Number)
                or isinstance(row[field], bool)
                or not isfinite(row[field])
                or row[field] < 0
            ):
                raise ValueError(f"revision summary {field} must be nonnegative")
        seen.add(series_id)
        normalized.append(
            {
                "series_id": series_id,
                "observation_count": row["observation_count"],
                "avg_revision_count": float(row["avg_revision_count"]),
                "max_revision_count": row["max_revision_count"],
                "avg_abs_revision_pct": float(row["avg_abs_revision_pct"]),
                "max_abs_revision_pct": float(row["max_abs_revision_pct"]),
            }
        )
    normalized.sort(key=lambda row: row["series_id"])
    missing_series_ids = sorted(selected - seen)
    input_selection = {
        "source": "macro_medallion_postgresql",
        "objects": [SERIES_DIMENSION_OBJECT, REVISION_SUMMARY_OBJECT],
        "series_ids": list(series_ids),
        "selection_scope": "configured_approved_dim_series",
        "page_size": page_size,
    }
    source_rows = {
        "revision_summaries": normalized,
        "missing_series_ids": missing_series_ids,
    }
    return {
        "manifest": {
            **input_selection,
            "input_selection_sha256": sha256(input_selection),
            "source_rows_sha256": sha256(source_rows),
            "extracted_at": datetime.now(UTC).isoformat(),
            "redistribution_status": "restricted",
            "temporal_status": "current_only_revision_quality",
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
        },
        **source_rows,
    }
