"""Idempotent PostgreSQL migration runner for dedicated MarketAtlas schemas."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .config import TargetDatabaseConfig
from .database import DatabaseUnavailable

DEFAULT_MIGRATION_DIRECTORY = Path("sql/migrations")


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_migrations(
    config: TargetDatabaseConfig,
    directory: Path = DEFAULT_MIGRATION_DIRECTORY,
) -> dict[str, Any]:
    migration_paths = sorted(directory.glob("*.sql"))
    if not migration_paths:
        raise DatabaseUnavailable(f"no SQL migrations found in {directory}")
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error

    applied: list[str] = []
    skipped: list[str] = []
    try:
        with psycopg.connect(**config.connection_kwargs()) as connection:
            for path in migration_paths:
                version = path.name
                checksum = _checksum(path)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT to_regclass('atlas.schema_migration')")
                    migration_table_exists = cursor.fetchone()[0] is not None
                    if migration_table_exists:
                        cursor.execute(
                            "SELECT checksum_sha256 FROM atlas.schema_migration WHERE version = %s",
                            (version,),
                        )
                        existing = cursor.fetchone()
                        if existing:
                            if existing[0] != checksum:
                                raise DatabaseUnavailable(
                                    f"applied migration checksum changed: {version}"
                                )
                            skipped.append(version)
                            connection.commit()
                            continue

                try:
                    with connection.transaction(), connection.cursor() as cursor:
                        cursor.execute(path.read_text(encoding="utf-8"))
                        cursor.execute(
                            sql.SQL("SET LOCAL ROLE {}").format(
                                sql.Identifier(config.role)
                            )
                        )
                        cursor.execute(
                            """
                            INSERT INTO atlas.schema_migration (version, checksum_sha256)
                            VALUES (%s, %s)
                            """,
                            (version, checksum),
                        )
                    applied.append(version)
                except Exception:
                    connection.rollback()
                    raise

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM atlas.node_type) AS node_types,
                        (SELECT count(*) FROM atlas.edge_type) AS edge_types,
                        (SELECT count(*) FROM atlas.edge_endpoint_rule) AS endpoint_rules,
                        (SELECT count(*) FROM atlas.schema_migration) AS migration_count
                    """
                )
                row = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT rolname, rolcanlogin
                    FROM pg_roles
                    WHERE rolname IN (
                        'marketatlas_source_reader',
                        'marketatlas_writer',
                        'marketatlas_report_reader'
                    )
                    ORDER BY rolname
                    """
                )
                roles = [
                    {"role": role, "can_login": can_login}
                    for role, can_login in cursor.fetchall()
                ]
    except DatabaseUnavailable:
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"MarketAtlas migration failed: {message}") from error

    return {
        "status": "migrations_current",
        "applied": applied,
        "skipped": skipped,
        "node_type_count": row[0],
        "edge_type_count": row[1],
        "endpoint_rule_count": row[2],
        "migration_count": row[3],
        "roles": roles,
    }


def validate_role_boundaries(config: TargetDatabaseConfig) -> dict[str, Any]:
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error

    checks: dict[str, bool] = {}
    try:
        with (
            psycopg.connect(
                **config.connection_kwargs(), autocommit=True
            ) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """
                SELECT
                    'meta.fred_series'::regclass::oid,
                    'gold.fred_point_in_time'::regclass::oid,
                    'atlas.node'::regclass::oid,
                    'atlas'::regnamespace::oid,
                    'atlas_report'::regnamespace::oid
                """
            )
            (
                meta_series_oid,
                gold_pit_oid,
                atlas_node_oid,
                atlas_schema_oid,
                report_schema_oid,
            ) = cursor.fetchone()
            for role in (
                "marketatlas_source_reader",
                "marketatlas_writer",
                "marketatlas_report_reader",
            ):
                cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
                if role == "marketatlas_source_reader":
                    cursor.execute(
                        """
                        SELECT
                            has_table_privilege(current_user, %s, 'SELECT'),
                            has_table_privilege(current_user, %s, 'SELECT'),
                            has_table_privilege(current_user, %s, 'INSERT,UPDATE,DELETE'),
                            has_schema_privilege(current_user, %s, 'CREATE')
                        """,
                        (
                            meta_series_oid,
                            gold_pit_oid,
                            meta_series_oid,
                            atlas_schema_oid,
                        ),
                    )
                    meta_select, gold_select, source_write, atlas_create = (
                        cursor.fetchone()
                    )
                    checks["source_can_read_approved_objects"] = (
                        meta_select and gold_select
                    )
                    checks["source_cannot_write_upstream"] = not source_write
                    checks["source_cannot_create_in_atlas"] = not atlas_create
                elif role == "marketatlas_writer":
                    cursor.execute(
                        """
                        SELECT
                            has_schema_privilege(current_user, %s, 'CREATE'),
                            has_table_privilege(current_user, %s, 'INSERT,UPDATE,DELETE'),
                            has_table_privilege(current_user, %s, 'SELECT,INSERT,UPDATE,DELETE')
                        """,
                        (atlas_schema_oid, atlas_node_oid, meta_series_oid),
                    )
                    atlas_create, atlas_write, upstream_access = cursor.fetchone()
                    checks["writer_can_write_atlas"] = atlas_create and atlas_write
                    checks["writer_cannot_access_upstream"] = not upstream_access
                else:
                    cursor.execute(
                        """
                        SELECT
                            has_table_privilege(current_user, %s, 'SELECT'),
                            has_table_privilege(current_user, %s, 'INSERT,UPDATE,DELETE'),
                            has_schema_privilege(current_user, %s, 'CREATE')
                        """,
                        (atlas_node_oid, atlas_node_oid, report_schema_oid),
                    )
                    atlas_select, atlas_write, report_create = cursor.fetchone()
                    checks["report_can_read_atlas"] = atlas_select
                    checks["report_cannot_write_atlas"] = not atlas_write
                    checks["report_cannot_create_serving_objects"] = not report_create
                cursor.execute("RESET ROLE")
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"role-boundary validation failed: {message}"
        ) from error

    return {
        "status": "valid" if all(checks.values()) else "invalid",
        "checks": checks,
    }
