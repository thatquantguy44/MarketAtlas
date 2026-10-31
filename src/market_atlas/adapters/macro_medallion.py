"""Bounded, read-only adapter for the verified MacroMedallion PostgreSQL objects."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any

from market_atlas.config import MacroMedallionConfig, SourceDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable

SERIES_OBJECT = "meta.fred_series"
OBSERVATION_OBJECT = "gold.fred_point_in_time"
REQUIRED_COLUMNS = {
    SERIES_OBJECT: {
        "series_id",
        "title",
        "category",
        "frequency",
        "units",
        "active",
        "vintage_enabled",
        "load_type",
        "updated_at",
    },
    OBSERVATION_OBJECT: {
        "series_id",
        "observation_date",
        "realtime_start",
        "realtime_end",
        "value",
        "revision_number",
        "is_missing",
        "ingested_at",
    },
}


def _validate_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO date") from error


@contextmanager
def _read_only_connection(config: SourceDatabaseConfig) -> Iterator[Any]:
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error
    try:
        with psycopg.connect(
            **config.connection_kwargs(), autocommit=True
        ) as connection:
            with connection.cursor() as cursor:
                if config.role:
                    cursor.execute(
                        sql.SQL("SET ROLE {}").format(sql.Identifier(config.role))
                    )
                cursor.execute("SET default_transaction_read_only = on")
                cursor.execute("SET statement_timeout = '30s'")
            yield connection
    except DatabaseUnavailable:
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or type(error).__name__
        raise DatabaseUnavailable(
            f"MacroMedallion adapter failed: {message}"
        ) from error


def verify_contract(database: SourceDatabaseConfig) -> dict[str, Any]:
    """Verify required object columns and the enforced read-only session."""
    from psycopg.errors import ReadOnlySqlTransaction

    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT table_schema || '.' || table_name AS object_name, column_name
                FROM information_schema.columns
                WHERE (table_schema, table_name) IN (('meta', 'fred_series'),
                                                     ('gold', 'fred_point_in_time'))
                """
        )
        found: dict[str, set[str]] = {name: set() for name in REQUIRED_COLUMNS}
        for object_name, column_name in cursor.fetchall():
            if object_name in found:
                found[object_name].add(column_name)
        cursor.execute("SHOW transaction_read_only")
        read_only = cursor.fetchone()[0] == "on"
        cursor.execute(
            """
                SELECT has_table_privilege(current_user, 'meta.fred_series', 'INSERT,UPDATE,DELETE')
                    OR has_table_privilege(current_user, 'gold.fred_point_in_time', 'INSERT,UPDATE,DELETE')
                """
        )
        role_has_source_write_privileges = bool(cursor.fetchone()[0])
        try:
            cursor.execute("CREATE TEMP TABLE marketatlas_read_only_probe (id integer)")
            write_blocked = False
            cursor.execute("DROP TABLE marketatlas_read_only_probe")
        except ReadOnlySqlTransaction:
            write_blocked = True

    missing = {
        object_name: sorted(required - found[object_name])
        for object_name, required in REQUIRED_COLUMNS.items()
        if required - found[object_name]
    }
    return {
        "status": "valid" if not missing and read_only and write_blocked else "invalid",
        "acceptance_ready": not role_has_source_write_privileges,
        "read_only_session": read_only,
        "negative_write_test": "blocked" if write_blocked else "failed",
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
    pilot: MacroMedallionConfig,
    *,
    max_rows: int = 250000,
    batch_size: int = 25,
    page_size: int = 500,
) -> dict[str, Any]:
    """Extract configured series and their eligible point-in-time observation versions."""
    start = _validate_iso_date(pilot.observation_start, "observation_start")
    end = _validate_iso_date(pilot.observation_end, "observation_end")
    cutoff = _validate_iso_date(pilot.knowledge_cutoff, "knowledge_cutoff")
    if end < start:
        raise ValueError("observation_end must be on or after observation_start")

    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT series_id, title, category, frequency, units, active,
                       vintage_enabled, load_type, updated_at
                FROM meta.fred_series
                WHERE series_id = ANY(%s)
                ORDER BY series_id
                """,
            (list(pilot.series_ids),),
        )
        series_columns = [column.name for column in cursor.description]
        series_rows = [
            dict(zip(series_columns, row, strict=True)) for row in cursor.fetchall()
        ]
        found_ids = {row["series_id"] for row in series_rows}
        missing_ids = sorted(set(pilot.series_ids) - found_ids)
        if missing_ids:
            raise ValueError(
                f"configured MacroMedallion series not found: {', '.join(missing_ids)}"
            )

        if (
            not 1 <= batch_size <= 1000
            or not 1 <= page_size <= 1000
            or not 1 <= max_rows <= 1000000
        ):
            raise ValueError("invalid observation extraction limits")
        observation_rows = []
        for batch_start in range(0, len(pilot.series_ids), batch_size):
            cursor.execute(
                """
                    SELECT series_id, observation_date, realtime_start, realtime_end,
                           value, revision_number, is_missing, ingested_at
                    FROM gold.fred_point_in_time
                    WHERE series_id = ANY(%s) AND observation_date >= %s
                      AND observation_date <= %s AND realtime_start <= %s
                    ORDER BY series_id, observation_date, realtime_start
                    LIMIT %s
                """,
                (
                    list(pilot.series_ids[batch_start : batch_start + batch_size]),
                    start.isoformat(),
                    min(end, cutoff).isoformat(),
                    cutoff.isoformat(),
                    max_rows - len(observation_rows) + 1,
                ),
            )
            observation_columns = [column.name for column in cursor.description]
            while rows := cursor.fetchmany(page_size):
                if len(observation_rows) + len(rows) > max_rows:
                    raise ValueError("observation extract exceeds configured row limit")
                observation_rows.extend(
                    dict(zip(observation_columns, row, strict=True)) for row in rows
                )

    entities = [
        {
            "canonical_key": f"macro:fred:{row['series_id']}",
            "type": "macro_series",
            "source": "fred",
            "source_identifier": row["series_id"],
            "label": row["title"],
            "category": row["category"],
            "frequency": row["frequency"],
            "unit": row["units"],
            "active": bool(row["active"]),
            "vintage_enabled": bool(row["vintage_enabled"]),
            "load_type": row["load_type"],
            "source_metadata_updated_at": row["updated_at"],
        }
        for row in series_rows
    ]
    observations = [
        {
            "series_canonical_key": f"macro:fred:{row['series_id']}",
            "reference_period": row["observation_date"],
            "value": row["value"],
            "available_on": row["realtime_start"],
            "availability_precision": "date",
            "source_valid_through_inclusive": row["realtime_end"],
            "revision_number": row["revision_number"],
            "is_missing": bool(row["is_missing"]),
            "source_ingested_at": row["ingested_at"],
            "source_record": (
                f"{OBSERVATION_OBJECT}:{row['series_id']}:"
                f"{row['observation_date']}:{row['realtime_start']}:"
                f"{row['revision_number']}"
            ),
        }
        for row in observation_rows
    ]
    input_selection = {
        "source": "macro_medallion_postgresql",
        "objects": [SERIES_OBJECT, OBSERVATION_OBJECT],
        "series_ids": list(pilot.series_ids),
        "observation_start": pilot.observation_start,
        "observation_end": pilot.observation_end,
        "knowledge_cutoff": pilot.knowledge_cutoff,
    }
    return {
        "manifest": {
            **input_selection,
            "input_selection_sha256": sha256(input_selection),
            "source_rows_sha256": sha256(
                {
                    "entities": entities,
                    "macro_observations": observations,
                }
            ),
            "extracted_at": datetime.now(UTC).isoformat(),
            "series_metadata_context": "current_not_point_in_time",
            "source_snapshot_status": "retained_in_generated_extract_only",
            "redistribution_status": pilot.redistribution_status,
            "availability_semantics": (
                "FRED real-time dates; date precision only. Source realtime_end is inclusive."
            ),
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
        },
        "entities": entities,
        "macro_observations": observations,
    }
