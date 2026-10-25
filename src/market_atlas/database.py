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
                           GREATEST(c.reltuples::bigint, 0) AS estimated_rows,
                           has_table_privilege(current_user, c.oid, 'SELECT') AS can_select,
                           has_table_privilege(
                               current_user, c.oid, 'INSERT,UPDATE,DELETE'
                           ) AS can_write
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
                      AND n.nspname <> 'information_schema'
                      AND n.nspname NOT LIKE 'pg_%'
                    ORDER BY n.nspname, c.relname
                    """
                )
                objects = _dict_rows(cursor)
                for object_row in objects:
                    if not object_row["can_select"]:
                        object_row["read_probe_status"] = "not_authorized"
                        continue
                    try:
                        cursor.execute(
                            sql.SQL("SELECT 1 FROM {}.{} LIMIT 0").format(
                                sql.Identifier(object_row["schema_name"]),
                                sql.Identifier(object_row["object_name"]),
                            )
                        )
                    except psycopg.Error as error:
                        object_row["read_probe_status"] = (
                            f"failed:{type(error).__name__}"
                        )
                    else:
                        object_row["read_probe_status"] = "passed"

                cursor.execute(
                    """
                    SELECT n.nspname AS schema_name,
                           c.relname AS object_name,
                           i.relname AS index_name,
                           ix.indisprimary AS is_primary,
                           ix.indisunique AS is_unique,
                           array_agg(a.attname ORDER BY key_column.ordinality)
                               AS key_columns
                    FROM pg_index AS ix
                    JOIN pg_class AS c ON c.oid = ix.indrelid
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    JOIN pg_class AS i ON i.oid = ix.indexrelid
                    JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY
                        AS key_column(attnum, ordinality) ON key_column.attnum > 0
                    JOIN pg_attribute AS a
                      ON a.attrelid = c.oid AND a.attnum = key_column.attnum
                    WHERE c.relkind IN ('r', 'p', 'm', 'f')
                      AND n.nspname <> 'information_schema'
                      AND n.nspname NOT LIKE 'pg_%'
                    GROUP BY n.nspname, c.relname, i.relname, ix.indisprimary, ix.indisunique
                    ORDER BY n.nspname, c.relname, i.relname
                    """
                )
                indexes = _dict_rows(cursor)

                cursor.execute(
                    """
                    SELECT n.nspname AS schema_name,
                           c.relname AS object_name,
                           md5(pg_get_viewdef(c.oid, true)) AS definition_md5
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE c.relkind IN ('v', 'm')
                      AND n.nspname <> 'information_schema'
                      AND n.nspname NOT LIKE 'pg_%'
                    ORDER BY n.nspname, c.relname
                    """
                )
                view_definitions = _dict_rows(cursor)

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
        "indexes": indexes,
        "view_definitions": view_definitions,
        "privileges": privileges,
    }
