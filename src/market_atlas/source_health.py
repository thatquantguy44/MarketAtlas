"""Bounded, read-only diagnostics for approved FRED freshness and vintage coverage."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from market_atlas.adapters.macro_medallion import _read_only_connection
from market_atlas.config import DEFAULT_CONFIG_PATH, load_source_database
from market_atlas.database import DatabaseUnavailable, inspect_source
from market_atlas.source_catalog import build_source_catalog
from market_atlas.source_contracts import (
    load_source_contract_registry,
    verify_source_contracts,
)

ROOT = Path(__file__).resolve().parents[2]
# Mirror the fingerprint-pinned coverage view. These measure reference-period age,
# not polling success or first publication. Unknown frequencies remain unknown.
AGE_LIMITS = {
    "d": 10,
    "daily": 10,
    "w": 21,
    "weekly": 21,
    "bw": 30,
    "biweekly": 30,
    "m": 75,
    "monthly": 75,
    "q": 200,
    "quarterly": 200,
    "sa": 380,
    "semiannual": 380,
    "a": 550,
    "annual": 550,
}
METADATA_SQL = """
SELECT m.series_id,m.title,m.frequency,m.units,m.active,m.vintage_enabled,
       m.load_type,m.expected_update_frequency
FROM gold.dim_series d JOIN meta.fred_series m USING(series_id)
WHERE d.source='fred' ORDER BY m.series_id LIMIT %s
"""
VINTAGE_SQL = """
SELECT series_id,count(*) AS observation_versions,
       count(*) FILTER(WHERE coalesce(realtime_start,'')='' AND coalesce(realtime_end,'')='') AS undated_versions,
       count(*) FILTER(WHERE realtime_start ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
         AND realtime_end ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
         AND realtime_start <= realtime_end) AS dated_versions,
       min(observation_date) AS first_period,max(observation_date) AS latest_period,
       min(ingested_at) AS first_ingested_at,max(ingested_at) AS last_changed_at
FROM gold.fred_point_in_time
WHERE series_id=ANY(%s) AND observation_date >= %s AND observation_date <= %s
GROUP BY series_id
"""
COVERAGE_SQL = """
SELECT source,series_id,frequency,latest_observation_date,days_since_last,is_stale
FROM gold.v_source_coverage WHERE source='fred' AND series_id=ANY(%s)
ORDER BY series_id
"""
ATTEMPTS_SQL = """
SELECT DISTINCT ON (series_id) series_id,run_id,status,started_at,ended_at,
       observations_extracted,rows_merged_silver,dq_passed
FROM audit.etl_series_run WHERE series_id=ANY(%s)
ORDER BY series_id,started_at DESC NULLS LAST,run_id DESC
"""
SUCCESSES_SQL = """
SELECT DISTINCT ON (series_id) series_id,run_id,status,started_at,ended_at,
       observations_extracted,rows_merged_silver,dq_passed
FROM audit.etl_series_run WHERE series_id=ANY(%s) AND status='succeeded'
ORDER BY series_id,started_at DESC NULLS LAST,run_id DESC
"""
RUNS_SQL = """
SELECT run_id,status,started_at,ended_at,series_total,series_succeeded,
       series_failed,series_skipped_not_due
FROM audit.etl_run ORDER BY started_at DESC NULLS LAST,run_id LIMIT 20
"""


def _rows(cursor):
    names = [column.name for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def diagnostic_registry():
    registry = load_source_contract_registry()
    registry["contracts"] += load_source_contract_registry(
        ROOT / "contracts/source_health_contracts.toml"
    )["contracts"]
    return registry


def collect(database, *, start, end, max_series=1000, batch_size=25):
    """Return aggregates only; no values, raw errors, DSNs or source write queries."""
    if database.role != "marketatlas_source_reader":
        raise ValueError("source health requires marketatlas_source_reader")
    if not 1 <= max_series <= 1000 or not 1 <= batch_size <= 25:
        raise ValueError("invalid diagnostic series/batch limit")
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("diagnostic window is reversed")
    registry = diagnostic_registry()
    gate = verify_source_contracts(
        build_source_catalog(inspect_source(database), registry), registry
    )
    if gate["status"] != "valid":
        raise ValueError("source health contract gate failed")
    captured = datetime.now(UTC).isoformat()
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_date AS source_date,current_setting('TimeZone') AS source_timezone"
        )
        clock = _rows(cursor)[0]
        cursor.execute(METADATA_SQL, (max_series + 1,))
        metadata = _rows(cursor)
        if len(metadata) > max_series:
            raise ValueError("source health catalog exceeds configured series limit")
        ids = [row["series_id"] for row in metadata]
        tables = {"coverage": [], "vintages": [], "attempts": [], "successes": []}
        for offset in range(0, len(ids), batch_size):
            batch = ids[offset : offset + batch_size]
            for name, sql, parameters in (
                ("coverage", COVERAGE_SQL, (batch,)),
                ("vintages", VINTAGE_SQL, (batch, start, end)),
                ("attempts", ATTEMPTS_SQL, (batch,)),
                ("successes", SUCCESSES_SQL, (batch,)),
            ):
                cursor.execute(sql, parameters)
                tables[name].extend(_rows(cursor))
        cursor.execute(RUNS_SQL)
        runs = _rows(cursor)
    return {
        "captured_at": captured,
        "window": {"start": start, "end": end},
        "clock": clock,
        "metadata": metadata,
        "runs": runs,
        "contract_gate": gate,
        **tables,
    }


def analyze(capture):
    coverage = {row["series_id"]: row for row in capture["coverage"]}
    vintages = {row["series_id"]: row for row in capture["vintages"]}
    attempts = {row["series_id"]: row for row in capture["attempts"]}
    successes = {row["series_id"]: row for row in capture.get("successes", [])}
    source_date = date.fromisoformat(str(capture["clock"]["source_date"]))
    rows = []
    for metadata in capture["metadata"]:
        series_id = metadata["series_id"]
        cov, vintage, attempt = (
            coverage.get(series_id, {}),
            vintages.get(series_id, {}),
            attempts.get(series_id, {}),
        )
        limit = AGE_LIMITS.get(cov.get("frequency"))
        try:
            period_age = (
                source_date - date.fromisoformat(cov["latest_observation_date"])
            ).days
        except (KeyError, TypeError, ValueError):
            period_age = None
        known_flag = cov.get("is_stale") in (0, 1) and cov.get("is_stale") is not None
        reported_stale = bool(cov["is_stale"]) if known_flag else None
        recomputed = (
            period_age > limit if limit is not None and period_age is not None else None
        )
        mismatched = (
            (reported_stale != recomputed or cov.get("days_since_last") != period_age)
            if recomputed is not None and known_flag
            else None
        )
        versions = vintage.get("observation_versions", 0)
        undated = vintage.get("undated_versions", 0)
        dated = vintage.get("dated_versions", 0)
        vintage_status = (
            "no_observations_in_window"
            if not versions
            else "current_only_by_source_policy"
            if undated == versions and metadata.get("vintage_enabled") == 0
            else "unexpected_missing_or_invalid_vintages"
            if dated != versions
            else "dated_observations_present"
        )
        last_success = successes.get(series_id)
        page_limit_suspected = bool(
            last_success
            and last_success.get("observations_extracted") == 100000
            and not versions
        )
        action = (
            "review_frequency_or_coverage_rule"
            if mismatched
            else "review_observation_pagination"
            if page_limit_suspected
            else "review_source_failure"
            if attempt.get("status") == "failed"
            else "force_source_poll_review"
            if reported_stale and attempt.get("status") == "skipped_not_due"
            else "reconcile_with_provider"
            if reported_stale
            else "no_staleness_action"
            if reported_stale is False
            else "coverage_unknown"
        )
        rows.append(
            {
                **metadata,
                "coverage": cov,
                "period_age_days": period_age,
                "age_limit_days": limit,
                "reported_stale": reported_stale,
                "recomputed_stale": recomputed,
                "coverage_rule_mismatch": mismatched,
                "vintages": vintage,
                "vintage_status": vintage_status,
                "latest_attempt": attempt or None,
                "latest_successful_attempt": last_success,
                "observation_page_limit_suspected": page_limit_suspected,
                "freshness_action": action,
            }
        )
    stale = [row for row in rows if row["reported_stale"] is True]
    policy = [
        row for row in rows if row["vintage_status"] == "current_only_by_source_policy"
    ]
    summary = {
        "series": len(rows),
        "stale_series": len(stale),
        "unknown_stale_flags": sum(row["reported_stale"] is None for row in rows),
        "coverage_rule_mismatches": sum(
            row["coverage_rule_mismatch"] is True for row in rows
        ),
        "unverifiable_coverage_rules": sum(
            row["coverage_rule_mismatch"] is None for row in rows
        ),
        "stale_latest_attempt_skipped": sum(
            row["latest_attempt"] is not None
            and row["latest_attempt"]["status"] == "skipped_not_due"
            for row in stale
        ),
        "vintage_status_counts": dict(Counter(row["vintage_status"] for row in rows)),
        "undated_versions": sum(
            row["vintages"].get("undated_versions", 0) for row in rows
        ),
        "observation_page_limit_suspected_series": sum(
            row["observation_page_limit_suspected"] for row in rows
        ),
        "latest_attempt_status_counts": dict(
            Counter(
                (row["latest_attempt"] or {}).get("status", "unknown") for row in rows
            )
        ),
    }
    return {
        "version": "source-health-v1",
        "status": "diagnosis_complete",
        "captured_at": capture["captured_at"],
        "window": capture["window"],
        "clock": capture["clock"],
        "summary": summary,
        "series": rows,
        "recent_runs": capture["runs"],
        "contract_gate": capture["contract_gate"],
        "remediation": {
            "source_poll_review_ids": [row["series_id"] for row in stale],
            "vintage_policy_review_ids": [row["series_id"] for row in policy],
            "writes_performed": False,
            "next_steps": [
                "Reconcile stale series with provider metadata; source period age is not polling age.",
                "Review skipped stale IDs for a targeted upstream no-skip-not-due poll.",
                "For selected current-only series, review a separate vintage-enabled full-history manifest and complete_vintage_history=true extraction against FRED/ALFRED.",
                "Validate API coverage, returned intervals, original values and row limits before any source-owner backfill; do not relabel current-only rows or use ingestion time as availability.",
                "After approved upstream repair, rerun source health and the MarketAtlas daily refresh.",
            ],
        },
        "limits": [
            "Latest observation period, last changed row time, pipeline attempt time and source availability are different clocks.",
            "A skipped attempt is not a successful provider poll. A successful poll can legitimately write zero changed rows.",
            "No provider API was called; upstream freshness and historical vintage recovery are not certified by this diagnosis.",
            "Vintage counts cover the requested observation window without a historical knowledge filter; format checks do not replace strict ingestion validation.",
        ],
    }


def run_diagnostics(config, output, *, start="2024-01-01", end=None):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "data/generated"):
        raise ValueError("diagnostic output must remain inside ignored data/generated")
    end = end or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    capture = collect(load_source_database(Path(config)), start=start, end=end)
    result = analyze(capture)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("capture.json", capture), ("diagnosis.json", result)):
        (output / name).write_text(json.dumps(value, default=str, indent=2) + "\n")
    prepare_recovery_review(result, output / "recovery-review")
    return result


def prepare_recovery_review(result, output):
    """Stage upstream-compatible manifests and dry-run argv; never execute them."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    commands = []
    safe_config = {
        "default": {
            "complete_vintage_history": True,
            "notify_on": "never",
            "alert_webhook_url": "",
            "extract_workers": 1,
            "rate_limit_per_minute": 30,
        }
    }
    config_path = output / "recovery-config.yml"
    config_path.write_text(json.dumps(safe_config, indent=2) + "\n")
    for kind, key in (
        ("freshness", "source_poll_review_ids"),
        ("vintages", "vintage_policy_review_ids"),
    ):
        ids = set(result["remediation"][key])
        specs = []
        for row in result["series"]:
            if row["series_id"] not in ids or not row.get("active"):
                continue
            specs.append(
                {
                    "series_id": row["series_id"],
                    "title": row["title"],
                    "frequency": row["frequency"],
                    "units": row["units"],
                    "source": "fred",
                    "vintage_enabled": True
                    if kind == "vintages"
                    else bool(row["vintage_enabled"]),
                    "load_type": "full" if kind == "vintages" else row["load_type"],
                    "expected_update_frequency": row["expected_update_frequency"],
                }
            )
        if not specs:
            continue
        path = output / f"{kind}-review.yml"
        path.write_text(
            json.dumps(
                {"name": f"marketatlas-{kind}-review", "series": specs}, indent=2
            )
            + "\n"
        )
        preferred = ["AKUR"] if kind == "vintages" else ["AKUR", "GDP", "ANFCI"]
        pilot = [series_id for series_id in preferred if series_id in ids] or [
            specs[0]["series_id"]
        ]
        commands.append(
            {
                "purpose": kind,
                "review_series_count": len(specs),
                "pilot_ids": pilot,
                "working_directory": "SOURCE_OWNER_CONFIRMED_UPSTREAM_CHECKOUT",
                "environment": {
                    "FRED_NOTIFY_ON": "never",
                    "FRED_COMPLETE_VINTAGE_HISTORY": "true",
                },
                "argv": [
                    "python",
                    "-m",
                    "fred_pipeline",
                    "run",
                    "--env",
                    "dev",
                    "--manifests",
                    str(path.resolve()),
                    "--config",
                    str(config_path.resolve()),
                    "--source",
                    "fred",
                    "--series",
                    ",".join(pilot),
                    "--no-skip-not-due",
                    "--dry-run",
                    "--no-gold",
                    "--no-ecb-assets",
                ],
                "executed": False,
            }
        )
    (output / "dry-run-plan.json").write_text(
        json.dumps(
            {
                "status": "review_only_not_executed",
                "commands": commands,
                "requirements": [
                    "Confirm the canonical upstream checkout and review/apply the pagination patch with its regression tests.",
                    "Supply the existing FRED API credential through the upstream environment; none was copied here.",
                    "Review the pilot's completeness, returned intervals, values, rate/row bounds and source rights before any broader extraction.",
                    "Changing vintage policy is not metadata repair. Preserve existing current-only records and design explicit staged/replacement semantics before a source-owner write.",
                    "Do not remove --dry-run until source-owner repair is authorized. MarketAtlas never executes these commands.",
                ],
            },
            indent=2,
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end")
    args = parser.parse_args()
    try:
        result = run_diagnostics(
            args.config, args.output, start=args.start, end=args.end
        )
    except (OSError, ValueError, DatabaseUnavailable) as error:
        parser.exit(
            1,
            f"Source diagnosis failed ({type(error).__name__}); no source writes performed.\n",
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "summary": result["summary"],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
