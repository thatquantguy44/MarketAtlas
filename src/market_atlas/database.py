"""Read-only PostgreSQL source discovery."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from .config import SourceDatabaseConfig


class DatabaseUnavailable(RuntimeError):
    """Raised with a secret-safe message when PostgreSQL cannot be inspected."""


def _dict_rows(cursor: Any) -> list[dict[str, Any]]:
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def inspect_source(config: SourceDatabaseConfig) -> dict[str, Any]:
    """Inspect schemas, objects, and columns without reading source rows."""
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error

    try:
        with closing(psycopg.connect(**config.connection_kwargs())) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                if config.role:
                    cursor.execute(
                        sql.SQL("SET ROLE {}").format(sql.Identifier(config.role))
                    )
                cursor.execute("SET default_transaction_read_only = on")
                cursor.execute("SET statement_timeout = '10s'")
                cursor.execute(
                    """
                    SELECT current_database() AS database,
                           current_user AS database_user,
                           current_setting('server_version') AS server_version,
                           current_setting('transaction_read_only')::boolean AS transaction_read_only
                    """
                )
                server = _dict_rows(cursor)[0]

                cursor.execute(
                    """
                    SELECT n.nspname AS schema_name,
                           has_schema_privilege(current_user, n.oid, 'USAGE') AS can_use,
                           has_schema_privilege(current_user, n.oid, 'CREATE') AS can_create
                    FROM pg_namespace AS n
                    WHERE n.nspname <> 'information_schema'
                      AND n.nspname NOT LIKE 'pg_%'
                    ORDER BY n.nspname
                    """
                )
                schemas = _dict_rows(cursor)

                cursor.execute(
                    """
                    SELECT n.nspname AS schema_name,
                           c.relname AS object_name,
                           CASE c.relkind
                             WHEN 'r' THEN 'table'
                             WHEN 'p' THEN 'partitioned_table'
                             WHEN 'v' THEN 'view'
                             WHEN 'm' THEN 'materialized_view'
                             WHEN 'f' THEN 'foreign_table'
                           END AS object_type,
                           GREATEST(c.reltuples::bigint, 0) AS estimated_rows
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
                      AND n.nspname <> 'information_schema'
                      AND n.nspname NOT LIKE 'pg_%'
                    ORDER BY n.nspname, c.relname
                    """
                )
                objects = _dict_rows(cursor)

                cursor.execute(
                    """
                    SELECT table_schema AS schema_name,
                           table_name AS object_name,
                           ordinal_position,
                           column_name,
                           data_type,
                           udt_name,
                           is_nullable = 'YES' AS is_nullable
                    FROM information_schema.columns
                    WHERE table_schema <> 'information_schema'
                      AND table_schema NOT LIKE 'pg_%'
                    ORDER BY table_schema, table_name, ordinal_position
                    """
                )
                columns = _dict_rows(cursor)

                cursor.execute(
                    """
                    SELECT table_schema AS schema_name,
                           table_name AS object_name,
                           privilege_type
                    FROM information_schema.table_privileges
                    WHERE grantee = current_user
                      AND table_schema <> 'information_schema'
                      AND table_schema NOT LIKE 'pg_%'
                    ORDER BY table_schema, table_name, privilege_type
                    """
                )
                privileges = _dict_rows(cursor)
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or type(error).__name__
        raise DatabaseUnavailable(
            f"PostgreSQL source inspection failed: {message}"
        ) from error

    return {
        "status": "connected_read_only",
        "server": server,
        "schemas": schemas,
        "objects": objects,
        "columns": columns,
        "privileges": privileges,
    }
