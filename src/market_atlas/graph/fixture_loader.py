"""Idempotent loader and integrity validation for the synthetic graph fixture."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256, validate_fixture
from market_atlas.database import DatabaseUnavailable

FIXTURE_NAMESPACE = UUID("d0d14d99-68c4-4e4b-a92c-e2afec7ea7b6")
FIXTURE_RECORDED_AT = datetime(2024, 1, 2, 12, tzinfo=UTC)
FIXTURE_EXTRACTED_AT = datetime(2024, 5, 2, 12, tzinfo=UTC)


def stable_id(record_type: str, source_id: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, f"{record_type}:{source_id}")


def _reference_period_date(value: str) -> date:
    return date.fromisoformat(f"{value}-01" if len(value) == 7 else value)


def _connect(config: TargetDatabaseConfig) -> Any:
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise DatabaseUnavailable(
            "PostgreSQL support is not installed; install the project's postgres extra"
        ) from error
    connection = psycopg.connect(**config.connection_kwargs())
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(config.role)))
    return connection


def load_fixture(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    errors = validate_fixture(fixture)
    if errors:
        raise ValueError("fixture contract is invalid: " + "; ".join(errors))
    try:
        from psycopg.types.json import Jsonb

        with _connect(config) as connection, connection.cursor() as cursor:
            fixture_hash = sha256(fixture)
            input_manifest_id = stable_id("input-manifest", fixture_hash)
            cursor.execute(
                """
                INSERT INTO atlas.input_manifest (
                    input_manifest_id, source_name, source_object,
                    source_snapshot_reference, manifest_sha256, extracted_at,
                    redistribution_status, manifest
                ) VALUES (%s, 'synthetic-fixture', 'market-atlas-fixture', %s, %s, %s,
                          'synthetic', %s)
                ON CONFLICT (source_name, source_object, manifest_sha256) DO UPDATE
                SET manifest = EXCLUDED.manifest
                RETURNING input_manifest_id
                """,
                (
                    input_manifest_id,
                    fixture["metadata"]["fixture_version"],
                    fixture_hash,
                    FIXTURE_EXTRACTED_AT,
                    Jsonb(fixture["metadata"]),
                ),
            )
            input_manifest_id = cursor.fetchone()[0]

            node_ids: dict[str, UUID] = {}
            for entity in fixture["entities"]:
                proposed_id = stable_id("node", entity["id"])
                cursor.execute(
                    """
                    INSERT INTO atlas.node (
                        node_id, node_type, canonical_key, display_label,
                        entity_status, provenance
                    ) VALUES (%s, %s, %s, %s, 'active', %s)
                    ON CONFLICT (node_type, canonical_key) DO UPDATE
                    SET display_label = EXCLUDED.display_label,
                        provenance = EXCLUDED.provenance
                    RETURNING node_id
                    """,
                    (
                        proposed_id,
                        entity["type"],
                        f"fixture:{entity['id']}",
                        entity["label"],
                        Jsonb(
                            {"source": "synthetic-fixture", "source_id": entity["id"]}
                        ),
                    ),
                )
                node_ids[entity["id"]] = cursor.fetchone()[0]

            for identifier in fixture["identifiers"]:
                source_key = ":".join(
                    (
                        identifier["entity_id"],
                        identifier["source"],
                        identifier["scheme"],
                        identifier["value"],
                        identifier["valid_from"],
                    )
                )
                cursor.execute(
                    """
                    INSERT INTO atlas.node_identifier (
                        node_identifier_id, node_id, node_type, source_name,
                        identifier_scheme, identifier_value, valid_from, valid_to,
                        availability_status, recorded_from, mapping_status, provenance
                    ) VALUES (
                        %s, %s, 'listing', %s, %s, %s, %s, %s,
                        'unknown', %s, 'accepted', %s
                    )
                    ON CONFLICT (node_identifier_id) DO UPDATE
                    SET valid_to = EXCLUDED.valid_to,
                        provenance = EXCLUDED.provenance
                    """,
                    (
                        stable_id("identifier", source_key),
                        node_ids[identifier["entity_id"]],
                        identifier["source"],
                        identifier["scheme"],
                        identifier["value"],
                        identifier["valid_from"],
                        identifier["valid_to"],
                        FIXTURE_RECORDED_AT,
                        Jsonb({"source": "synthetic-fixture"}),
                    ),
                )

            entity_types = {row["id"]: row["type"] for row in fixture["entities"]}
            for assertion in fixture["assertions"]:
                assertion_id = stable_id("assertion", assertion["id"])
                if assertion["supersedes_id"]:
                    cursor.execute(
                        "SELECT 1 FROM atlas.reference_assertion WHERE assertion_id = %s",
                        (assertion_id,),
                    )
                    if cursor.fetchone():
                        continue
                    cursor.execute(
                        """
                        SELECT atlas.supersede_reference_assertion(
                            %s, %s, %s, %s, 'known', %s, %s, %s, %s
                        )
                        """,
                        (
                            stable_id("assertion", assertion["supersedes_id"]),
                            assertion_id,
                            assertion["status"],
                            assertion["available_at"],
                            assertion["recorded_at"],
                            assertion["rationale"],
                            f"synthetic-fixture:{assertion['id']}",
                            Jsonb({"source": assertion["provenance"]}),
                        ),
                    )
                    continue
                cursor.execute(
                    """
                    INSERT INTO atlas.reference_assertion (
                        assertion_id, assertion_key, edge_type,
                        source_node_id, source_node_type,
                        target_node_id, target_node_type,
                        relationship_kind, assertion_status, rationale,
                        valid_from, valid_to, available_at, availability_status,
                        recorded_from, source_record, provenance
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, 'known', %s, %s, %s
                    )
                    ON CONFLICT (assertion_id) DO UPDATE
                    SET assertion_key = EXCLUDED.assertion_key,
                        assertion_status = EXCLUDED.assertion_status,
                        rationale = EXCLUDED.rationale,
                        valid_from = EXCLUDED.valid_from,
                        valid_to = EXCLUDED.valid_to,
                        available_at = EXCLUDED.available_at,
                        availability_status = EXCLUDED.availability_status,
                        recorded_from = EXCLUDED.recorded_from,
                        source_record = EXCLUDED.source_record,
                        provenance = EXCLUDED.provenance
                    """,
                    (
                        assertion_id,
                        stable_id("assertion-key", assertion["assertion_key"]),
                        assertion["predicate"],
                        node_ids[assertion["source_id"]],
                        entity_types[assertion["source_id"]],
                        node_ids[assertion["target_id"]],
                        entity_types[assertion["target_id"]],
                        assertion["kind"],
                        assertion["status"],
                        assertion["rationale"],
                        assertion["valid_from"],
                        assertion["valid_to"],
                        assertion["available_at"],
                        assertion["recorded_at"],
                        f"synthetic-fixture:{assertion['id']}",
                        Jsonb({"source": assertion["provenance"]}),
                    ),
                )

            calendar_name = fixture["metadata"]["calendar"]
            for session in fixture["sessions"]:
                cursor.execute(
                    """
                    INSERT INTO atlas.market_calendar_session (
                        calendar_name, session_date, is_business_day,
                        calendar_version, input_manifest_id
                    ) VALUES (%s, %s, true, %s, %s)
                    ON CONFLICT (calendar_name, session_date, calendar_version) DO UPDATE
                    SET input_manifest_id = EXCLUDED.input_manifest_id
                    """,
                    (
                        calendar_name,
                        session,
                        fixture["metadata"]["fixture_version"],
                        input_manifest_id,
                    ),
                )

            for observation in fixture["market_observations"]:
                observation_key = stable_id(
                    "market-observation-key",
                    ":".join(
                        (
                            observation["instrument_id"],
                            observation["session"],
                            observation["measure"],
                        )
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO atlas.market_observation_version (
                        market_observation_version_id, observation_key,
                        instrument_node_id, session_date, measure, value, unit,
                        calendar_name, adjustment_basis, adjustment_history_status,
                        available_at, availability_status, source_record,
                        input_manifest_id, recorded_from
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, 'supported',
                        %s, 'known', %s, %s, %s
                    )
                    ON CONFLICT (market_observation_version_id) DO UPDATE
                    SET value = EXCLUDED.value,
                        unit = EXCLUDED.unit,
                        available_at = EXCLUDED.available_at,
                        input_manifest_id = EXCLUDED.input_manifest_id
                    """,
                    (
                        stable_id("market-observation", observation["source_record"]),
                        observation_key,
                        node_ids[observation["instrument_id"]],
                        observation["session"],
                        observation["measure"],
                        observation["value"],
                        observation["unit"],
                        calendar_name,
                        observation["adjustment"],
                        observation["available_at"],
                        observation["source_record"],
                        input_manifest_id,
                        observation["available_at"],
                    ),
                )

            for observation in fixture["macro_observations"]:
                cursor.execute(
                    """
                    INSERT INTO atlas.macro_observation_version (
                        macro_observation_version_id, series_node_id,
                        reference_period, reference_period_label, frequency, value,
                        unit, is_missing, vintage, available_at, availability_status,
                        source_ingested_at, source_record, input_manifest_id, recorded_from
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, false, %s, %s, 'known',
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (macro_observation_version_id) DO UPDATE
                    SET value = EXCLUDED.value,
                        available_at = EXCLUDED.available_at,
                        input_manifest_id = EXCLUDED.input_manifest_id
                    """,
                    (
                        stable_id("macro-observation", observation["source_record"]),
                        node_ids[observation["series_id"]],
                        _reference_period_date(observation["period"]),
                        observation["period"],
                        observation["frequency"],
                        observation["value"],
                        observation["unit"],
                        observation["vintage"],
                        observation["available_at"],
                        observation["available_at"],
                        observation["source_record"],
                        input_manifest_id,
                        observation["available_at"],
                    ),
                )

            counts = _fixture_counts(cursor)
        return {"status": "fixture_graph_loaded", **counts}
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(f"fixture graph load failed: {message}") from error


def _fixture_counts(cursor: Any) -> dict[str, int]:
    cursor.execute(
        """
        SELECT
            (SELECT count(*) FROM atlas.node
             WHERE canonical_key LIKE 'fixture:%') AS nodes,
            (SELECT count(*) FROM atlas.node_identifier
             WHERE provenance->>'source' = 'synthetic-fixture') AS identifiers,
            (SELECT count(*) FROM atlas.reference_assertion
             WHERE source_record LIKE 'synthetic-fixture:%') AS assertions,
            (SELECT count(*) FROM atlas.market_observation_version
             WHERE source_record LIKE 'synthetic-price-%') AS market_observations,
            (SELECT count(*) FROM atlas.macro_observation_version
             WHERE source_record LIKE 'synthetic-macro-%') AS macro_observations
        """
    )
    row = cursor.fetchone()
    return {
        "node_count": row[0],
        "identifier_count": row[1],
        "assertion_count": row[2],
        "market_observation_count": row[3],
        "macro_observation_count": row[4],
    }


def validate_fixture_graph(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Exercise database constraints without retaining the deliberately invalid rows."""
    try:
        from psycopg.errors import ForeignKeyViolation, UniqueViolation
        from psycopg.types.json import Jsonb

        first = load_fixture(config, fixture)
        first_ids = {
            row["id"]: str(stable_id("node", row["id"])) for row in fixture["entities"]
        }
        second = load_fixture(config, fixture)

        with _connect(config) as connection, connection.cursor() as cursor:
            counts = _fixture_counts(cursor)
            stable_reload = (
                first == second == {"status": "fixture_graph_loaded", **counts}
            )
            cursor.execute(
                """
                SELECT count(DISTINCT node_id), count(*)
                FROM atlas.node_identifier
                WHERE identifier_value IN ('OLDX', 'NEWX')
                  AND source_name = 'fixture-exchange'
                """
            )
            distinct_nodes, ticker_rows = cursor.fetchone()

            cursor.execute("SAVEPOINT invalid_endpoint")
            try:
                cursor.execute(
                    """
                    INSERT INTO atlas.reference_assertion (
                        assertion_id, assertion_key, edge_type, source_node_id, source_node_type,
                        target_node_id, target_node_type, relationship_kind,
                        valid_from, available_at, provenance
                    ) VALUES (%s, %s, 'lists', %s, 'instrument', %s, 'issuer',
                              'reference', '2024-01-02', %s, %s)
                    """,
                    (
                        stable_id("validation", "invalid-endpoint"),
                        stable_id("validation-key", "invalid-endpoint"),
                        stable_id("node", "I-A"),
                        stable_id("node", "O-A"),
                        FIXTURE_RECORDED_AT,
                        Jsonb({"source": "validation"}),
                    ),
                )
                invalid_endpoint_rejected = False
            except ForeignKeyViolation:
                invalid_endpoint_rejected = True
                cursor.execute("ROLLBACK TO SAVEPOINT invalid_endpoint")

            cursor.execute("SAVEPOINT overlapping_identifier")
            try:
                cursor.execute(
                    """
                    INSERT INTO atlas.node_identifier (
                        node_identifier_id, node_id, node_type, source_name,
                        identifier_scheme, identifier_value, valid_from,
                        availability_status, recorded_from, mapping_status, provenance
                    ) VALUES (%s, %s, 'listing', 'fixture-exchange', 'ticker',
                              'OLDX', '2024-01-03', 'unknown', %s, 'accepted', %s)
                    """,
                    (
                        stable_id("validation", "overlap"),
                        stable_id("node", "L-B"),
                        FIXTURE_RECORDED_AT,
                        Jsonb({"source": "validation"}),
                    ),
                )
                overlap_rejected = False
            except UniqueViolation:
                overlap_rejected = True
                cursor.execute("ROLLBACK TO SAVEPOINT overlapping_identifier")

            connection.rollback()

        passed = all(
            (
                stable_reload,
                distinct_nodes == 1,
                ticker_rows == 2,
                invalid_endpoint_rejected,
                overlap_rejected,
            )
        )
        return {
            "status": "valid" if passed else "invalid",
            "stable_reload": stable_reload,
            "ticker_history_one_node": distinct_nodes == 1 and ticker_rows == 2,
            "invalid_endpoint_rejected": invalid_endpoint_rejected,
            "overlapping_identifier_rejected": overlap_rejected,
            "expected_node_ids": first_ids,
            **counts,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"fixture graph validation failed: {message}"
        ) from error


def validate_temporal_fixture(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Exercise effective, source-knowledge, and system-record temporal cutoffs."""
    try:
        from psycopg.types.json import Jsonb

        load_fixture(config, fixture)
        with _connect(config) as connection, connection.cursor() as cursor:
            alpha_issuer = stable_id("node", "O-A")
            beta_issuer = stable_id("node", "O-B")
            alpha_listing = stable_id("node", "L-A")
            tech_sector = stable_id("node", "S-TECH")
            industrial_sector = stable_id("node", "S-IND")

            def source_records(
                effective_as_of: str, knowledge_cutoff: str, system_cutoff: str | None
            ) -> set[str]:
                cursor.execute(
                    """
                    SELECT source_record
                    FROM atlas.relationships_as_of(%s, %s, %s)
                    WHERE source_node_id IN (%s, %s)
                    """,
                    (
                        effective_as_of,
                        knowledge_cutoff,
                        system_cutoff,
                        alpha_issuer,
                        beta_issuer,
                    ),
                )
                return {row[0] for row in cursor.fetchall()}

            current_source_context = source_records(
                "2024-04-20", "2024-04-20T23:59:59Z", None
            )
            system_replay = source_records(
                "2024-04-20", "2024-04-20T23:59:59Z", "2024-04-20T23:59:59Z"
            )
            before_correction = source_records(
                "2024-03-01", "2024-03-01T23:59:59Z", "2024-03-01T23:59:59Z"
            )
            current_correction = source_records(
                "2024-04-04", "2024-04-04T23:59:59Z", None
            )

            cursor.execute(
                """
                SELECT count(*)
                FROM atlas.bounded_paths(%s, %s, %s, %s, 4)
                WHERE endpoint_node_id = %s
                """,
                (
                    alpha_listing,
                    "2024-03-01",
                    "2024-03-01T23:59:59Z",
                    "2024-03-01T23:59:59Z",
                    tech_sector,
                ),
            )
            path_before_retraction = cursor.fetchone()[0] == 1
            cursor.execute(
                """
                SELECT count(*)
                FROM atlas.bounded_paths(%s, %s, %s, NULL, 4)
                WHERE endpoint_node_id = %s
                """,
                (
                    alpha_listing,
                    "2024-04-04",
                    "2024-04-04T23:59:59Z",
                    tech_sector,
                ),
            )
            path_after_retraction_hidden = cursor.fetchone()[0] == 0

            cursor.execute("SAVEPOINT unsupported_history")
            cursor.execute(
                """
                INSERT INTO atlas.reference_assertion (
                    assertion_id, assertion_key, edge_type,
                    source_node_id, source_node_type, target_node_id, target_node_type,
                    relationship_kind, assertion_status, valid_from,
                    availability_status, recorded_from, source_record, provenance
                ) VALUES (
                    %s, %s, 'classified_as', %s, 'issuer', %s, 'sector',
                    'reference', 'accepted', '2024-01-02',
                    'unknown', %s, 'validation:unknown-availability', %s
                )
                """,
                (
                    stable_id("validation", "unknown-history"),
                    stable_id("validation-key", "unknown-history"),
                    beta_issuer,
                    industrial_sector,
                    FIXTURE_RECORDED_AT,
                    Jsonb({"source": "validation"}),
                ),
            )
            cursor.execute(
                """
                SELECT history_support
                FROM atlas.relationships_as_of(%s, %s, %s)
                WHERE source_record = 'validation:unknown-availability'
                """,
                (
                    "2024-02-10",
                    "2024-02-10T23:59:59Z",
                    "2024-02-10T23:59:59Z",
                ),
            )
            unsupported_history_visible = cursor.fetchone()[0] == "unsupported_history"
            cursor.execute("ROLLBACK TO SAVEPOINT unsupported_history")
            connection.rollback()

        late_fact_differs_by_system_cutoff = (
            "synthetic-fixture:A14" in current_source_context
            and "synthetic-fixture:A14" not in system_replay
        )
        correction_preserves_history = (
            "synthetic-fixture:A6" in before_correction
            and "synthetic-fixture:A15" not in before_correction
            and "synthetic-fixture:A15" in current_correction
            and "synthetic-fixture:A6" not in current_correction
        )
        passed = all(
            (
                late_fact_differs_by_system_cutoff,
                correction_preserves_history,
                path_before_retraction,
                path_after_retraction_hidden,
                unsupported_history_visible,
            )
        )
        return {
            "status": "valid" if passed else "invalid",
            "late_fact_differs_by_system_cutoff": late_fact_differs_by_system_cutoff,
            "correction_preserves_history": correction_preserves_history,
            "path_before_retraction": path_before_retraction,
            "path_after_retraction_hidden": path_after_retraction_hidden,
            "unsupported_history_visible": unsupported_history_visible,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"temporal fixture validation failed: {message}"
        ) from error


def validate_observation_fixture(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Prove cutoff-aware macro and market observation selection."""
    try:
        load_fixture(config, fixture)
        with _connect(config) as connection, connection.cursor() as cursor:
            macro_series = stable_id("node", "M-GROWTH")
            alpha_instrument = stable_id("node", "I-A")
            cursor.execute(
                """
                SELECT vintage, value
                FROM atlas.macro_observations_as_of(%s, NULL)
                WHERE series_node_id = %s AND reference_period_label = '2024-01'
                """,
                ("2024-02-10T23:59:59Z", macro_series),
            )
            early_macro = cursor.fetchone()
            cursor.execute(
                """
                SELECT vintage, value
                FROM atlas.macro_observations_as_of(%s, NULL)
                WHERE series_node_id = %s AND reference_period_label = '2024-01'
                """,
                ("2024-03-10T23:59:59Z", macro_series),
            )
            late_macro = cursor.fetchone()
            cursor.execute(
                """
                SELECT count(*)
                FROM atlas.market_observations_as_of(%s, NULL)
                WHERE instrument_node_id = %s AND session_date = '2024-01-02'
                """,
                ("2024-01-02T12:00:00Z", alpha_instrument),
            )
            unavailable_market_excluded = cursor.fetchone()[0] == 0

            cursor.execute("SAVEPOINT unsupported_adjustment")
            cursor.execute(
                """
                INSERT INTO atlas.market_observation_version (
                    market_observation_version_id, observation_key,
                    instrument_node_id, session_date, measure, value, unit,
                    calendar_name, adjustment_basis, adjustment_history_status,
                    available_at, availability_status, source_record,
                    input_manifest_id, recorded_from
                ) VALUES (
                    %s, %s, %s, '2024-01-03', 'adjusted_close', 101, 'USD',
                    %s, 'vendor-adjusted', 'unknown',
                    '2024-01-03T22:00:00Z', 'known',
                    'validation:unsupported-adjustment', %s, '2024-01-03T22:00:00Z'
                )
                """,
                (
                    stable_id("validation", "unsupported-adjustment"),
                    stable_id("validation-key", "unsupported-adjustment"),
                    alpha_instrument,
                    fixture["metadata"]["calendar"],
                    stable_id("input-manifest", sha256(fixture)),
                ),
            )
            cursor.execute(
                """
                SELECT selection_status
                FROM atlas.market_observations_as_of(%s, NULL)
                WHERE source_record = 'validation:unsupported-adjustment'
                """,
                ("2024-01-04T00:00:00Z",),
            )
            unsupported_adjustment_labeled = (
                cursor.fetchone()[0] == "unsupported_adjusted_history"
            )
            cursor.execute("ROLLBACK TO SAVEPOINT unsupported_adjustment")

            cursor.execute(
                "SELECT manifest_sha256 FROM atlas.input_manifest WHERE input_manifest_id = %s",
                (stable_id("input-manifest", sha256(fixture)),),
            )
            manifest_reproduced = cursor.fetchone()[0] == sha256(fixture)
            connection.rollback()

        macro_revision_selected_by_cutoff = early_macro == (
            "initial",
            Decimal(101),
        ) and late_macro == ("revision", Decimal("101.4"))
        passed = all(
            (
                macro_revision_selected_by_cutoff,
                unavailable_market_excluded,
                unsupported_adjustment_labeled,
                manifest_reproduced,
            )
        )
        return {
            "status": "valid" if passed else "invalid",
            "macro_revision_selected_by_cutoff": macro_revision_selected_by_cutoff,
            "unavailable_market_excluded": unavailable_market_excluded,
            "unsupported_adjustment_labeled": unsupported_adjustment_labeled,
            "manifest_reproduced": manifest_reproduced,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"observation fixture validation failed: {message}"
        ) from error
