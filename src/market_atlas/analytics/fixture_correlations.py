"""PostgreSQL persistence and validation for synthetic rolling correlations."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from itertools import pairwise
from typing import Any

from market_atlas.analytics.rolling_correlation import (
    CONFIGURATION_SHA256,
    METHOD_VERSION,
    MarketPoint,
    compute_rolling_correlations,
)
from market_atlas.config import TargetDatabaseConfig
from market_atlas.contracts import sha256
from market_atlas.database import DatabaseUnavailable
from market_atlas.graph.fixture_loader import (
    FIXTURE_EXTRACTED_AT,
    _connect,
    load_fixture,
    stable_id,
)


def _fixture_points(cursor: Any, knowledge_cutoff: str | None) -> list[MarketPoint]:
    cursor.execute(
        """
        SELECT
            selected.instrument_node_id::text, selected.session_date,
            selected.value, selected.unit, selected.calendar_name,
            selected.adjustment_basis, stored.available_at,
            selected.source_record, selected.selection_status
        FROM atlas.market_observations_as_of(%s, NULL) AS selected
        JOIN atlas.market_observation_version AS stored
          ON stored.market_observation_version_id
             = selected.market_observation_version_id
        WHERE selected.source_record LIKE 'synthetic-price-%%'
        """,
        (knowledge_cutoff,),
    )
    return [
        MarketPoint(
            instrument_id=row[0],
            session_date=row[1],
            value=float(row[2]),
            unit=row[3],
            calendar_name=row[4],
            adjustment_basis=row[5],
            available_at=row[6],
            source_record=row[7],
            selection_status=row[8],
        )
        for row in cursor.fetchall()
    ]


def calculate_fixture_correlations(
    config: TargetDatabaseConfig,
    fixture: dict[str, Any],
    knowledge_cutoff: str | None = None,
) -> dict[str, Any]:
    """Persist fixed-window fixture estimates for the declared knowledge cutoff."""
    try:
        from psycopg.types.json import Jsonb

        load_fixture(config, fixture)
        with _connect(config) as connection, connection.cursor() as cursor:
            points = _fixture_points(cursor, knowledge_cutoff)
            sessions = [date.fromisoformat(session) for session in fixture["sessions"]]
            if knowledge_cutoff is not None:
                cutoff_date = datetime.fromisoformat(knowledge_cutoff).date()
                sessions = [session for session in sessions if session <= cutoff_date]
            pair_ids = [
                (
                    str(stable_id("node", left)),
                    str(stable_id("node", right)),
                )
                for left, right in fixture["configured_pairs"]
            ]
            estimates = compute_rolling_correlations(sessions, points, pair_ids)
            fixture_hash = sha256(fixture)
            input_manifest_id = stable_id("input-manifest", fixture_hash)
            cutoff_key = knowledge_cutoff or "current-context"
            for estimate in estimates:
                estimate_key = stable_id(
                    "rolling-correlation-key",
                    f"{estimate.instrument_low_id}:{estimate.instrument_high_id}:"
                    f"{estimate.endpoint_session_date.isoformat()}:{cutoff_key}:"
                    f"{METHOD_VERSION}:{CONFIGURATION_SHA256}:"
                    f"{estimate.input_selection_sha256}",
                )
                cursor.execute(
                    """
                    INSERT INTO atlas.rolling_correlation_estimate_version (
                        rolling_correlation_estimate_version_id, estimate_key,
                        instrument_low_node_id, instrument_high_node_id,
                        endpoint_session_date, window_start_session_date,
                        paired_return_count, correlation, estimate_status,
                        return_definition, adjustment_basis, calendar_name,
                        method_version, configuration_sha256, input_selection_sha256,
                        knowledge_cutoff, max_input_available_at, input_manifest_id,
                        recorded_from, provenance
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        'simple_adjusted_close_return', %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (rolling_correlation_estimate_version_id) DO NOTHING
                    """,
                    (
                        stable_id("rolling-correlation", str(estimate_key)),
                        estimate_key,
                        estimate.instrument_low_id,
                        estimate.instrument_high_id,
                        estimate.endpoint_session_date,
                        estimate.window_start_session_date,
                        estimate.paired_return_count,
                        estimate.correlation,
                        estimate.estimate_status,
                        estimate.adjustment_basis,
                        fixture["metadata"]["calendar"],
                        METHOD_VERSION,
                        CONFIGURATION_SHA256,
                        estimate.input_selection_sha256,
                        knowledge_cutoff,
                        estimate.max_input_available_at,
                        input_manifest_id,
                        FIXTURE_EXTRACTED_AT,
                        Jsonb(
                            {
                                "source": "synthetic-fixture",
                                "configuration": CONFIGURATION_SHA256,
                                "method_version": METHOD_VERSION,
                            }
                        ),
                    ),
                )

            counts = _estimate_counts(cursor, input_manifest_id, knowledge_cutoff)
        return {
            "status": "fixture_correlations_calculated",
            "knowledge_cutoff": knowledge_cutoff,
            **counts,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"fixture correlation calculation failed: {message}"
        ) from error


def _estimate_counts(
    cursor: Any, input_manifest_id: Any, knowledge_cutoff: str | None
) -> dict[str, int]:
    cursor.execute(
        """
        SELECT
            count(*),
            count(*) FILTER (WHERE estimate_status = 'supported'),
            count(*) FILTER (WHERE estimate_status = 'zero_variance'),
            count(*) FILTER (WHERE estimate_status = 'insufficient_sample'),
            count(*) FILTER (WHERE estimate_status = 'incompatible_input'),
            count(*) FILTER (WHERE estimate_status = 'unsupported_history')
        FROM atlas.rolling_correlation_estimate_version
        WHERE input_manifest_id = %s
          AND knowledge_cutoff IS NOT DISTINCT FROM %s::timestamptz
          AND recorded_to IS NULL
        """,
        (input_manifest_id, knowledge_cutoff),
    )
    row = cursor.fetchone()
    return {
        "estimate_count": row[0],
        "supported_count": row[1],
        "zero_variance_count": row[2],
        "insufficient_sample_count": row[3],
        "incompatible_input_count": row[4],
        "unsupported_history_count": row[5],
    }


def _independent_final_correlation(fixture: dict[str, Any]) -> float:
    """Separate hand-readable calculation used only by fixture validation."""
    sessions = fixture["sessions"][-60:]
    prices = {
        (row["instrument_id"], row["session"]): float(row["value"])
        for row in fixture["market_observations"]
    }
    left, right = [], []
    for prior_session, session in pairwise(sessions):
        values = (
            prices.get(("I-A", prior_session)),
            prices.get(("I-A", session)),
            prices.get(("I-B", prior_session)),
            prices.get(("I-B", session)),
        )
        if any(value is None for value in values):
            continue
        left.append(values[1] / values[0] - 1)
        right.append(values[3] / values[2] - 1)
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_sum_squares = sum((value - left_mean) ** 2 for value in left)
    right_sum_squares = sum((value - right_mean) ** 2 for value in right)
    return numerator / (left_sum_squares * right_sum_squares) ** 0.5


def validate_rolling_correlation_fixture(
    config: TargetDatabaseConfig, fixture: dict[str, Any]
) -> dict[str, Any]:
    """Validate fixed windows, no look-ahead, and explicit undefined results."""
    try:
        current_first = calculate_fixture_correlations(config, fixture)
        current_second = calculate_fixture_correlations(config, fixture)
        cutoff = "2024-04-05T12:00:00Z"
        historical = calculate_fixture_correlations(config, fixture, cutoff)
        with _connect(config) as connection, connection.cursor() as cursor:
            input_manifest_id = stable_id("input-manifest", sha256(fixture))
            alpha_id, beta_id = sorted(
                (str(stable_id("node", "I-A")), str(stable_id("node", "I-B")))
            )
            cursor.execute(
                """
                SELECT correlation, paired_return_count
                FROM atlas.rolling_correlation_estimate_version
                WHERE input_manifest_id = %s
                  AND knowledge_cutoff IS NULL
                  AND instrument_low_node_id::text = %s
                  AND instrument_high_node_id::text = %s
                  AND endpoint_session_date = %s
                  AND recorded_to IS NULL
                """,
                (input_manifest_id, alpha_id, beta_id, fixture["sessions"][-1]),
            )
            final_supported = cursor.fetchone()
            cursor.execute(
                """
                SELECT
                    bool_and(window_session_count = 60),
                    bool_and(paired_return_count <= 59),
                    bool_and(
                        max_input_available_at IS NULL
                        OR max_input_available_at <= %s::timestamptz
                    )
                FROM atlas.rolling_correlation_estimate_version
                WHERE input_manifest_id = %s
                  AND knowledge_cutoff = %s::timestamptz
                  AND recorded_to IS NULL
                """,
                (cutoff, input_manifest_id, cutoff),
            )
            fixed_window, no_window_expansion, no_lookahead = cursor.fetchone()

        independent_match = (
            final_supported is not None
            and abs(float(final_supported[0]) - _independent_final_correlation(fixture))
            <= 1e-12
            and final_supported[1] >= 45
        )
        current_idempotent = current_first == current_second
        zero_variance_explicit = current_first["zero_variance_count"] > 0
        historical_is_bounded = (
            historical["estimate_count"] > 0
            and historical["estimate_count"] < current_first["estimate_count"]
            and bool(no_lookahead)
        )

        fixture_points = [
            MarketPoint(
                instrument_id=str(stable_id("node", row["instrument_id"])),
                session_date=date.fromisoformat(row["session"]),
                value=float(row["value"]),
                unit=row["unit"],
                calendar_name=fixture["metadata"]["calendar"],
                adjustment_basis=row["adjustment"],
                available_at=datetime.fromisoformat(row["available_at"]),
                source_record=row["source_record"],
                selection_status="supported",
            )
            for row in fixture["market_observations"]
        ]
        unsupported_points = [
            replace(fixture_points[0], selection_status="unsupported_adjusted_history"),
            *fixture_points[1:],
        ]
        unsupported_history_explicit = any(
            estimate.estimate_status == "unsupported_history"
            for estimate in compute_rolling_correlations(
                [date.fromisoformat(session) for session in fixture["sessions"]],
                unsupported_points,
                [
                    (str(stable_id("node", left)), str(stable_id("node", right)))
                    for left, right in fixture["configured_pairs"]
                ],
            )
        )

        passed = all(
            (
                current_idempotent,
                independent_match,
                zero_variance_explicit,
                bool(fixed_window),
                bool(no_window_expansion),
                historical_is_bounded,
                unsupported_history_explicit,
            )
        )
        return {
            "status": "valid" if passed else "invalid",
            "idempotent_reload": current_idempotent,
            "independent_correlation_match": independent_match,
            "zero_variance_explicit": zero_variance_explicit,
            "fixed_window": bool(fixed_window),
            "no_window_expansion": bool(no_window_expansion),
            "no_lookahead": historical_is_bounded,
            "unsupported_history_explicit": unsupported_history_explicit,
        }
    except (ValueError, DatabaseUnavailable):
        raise
    except Exception as error:
        diagnostic = getattr(error, "diag", None)
        message = getattr(diagnostic, "message_primary", None) or str(error)
        raise DatabaseUnavailable(
            f"rolling-correlation fixture validation failed: {message}"
        ) from error
