"""Optional Dagster definitions. Importing this module never connects to PostgreSQL."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dagster import (
    DefaultScheduleStatus,
    Definitions,
    Failure,
    Field,
    In,
    Nothing,
    Out,
    RetryPolicy,
    RunRequest,
    in_process_executor,
    job,
    op,
    resource,
    schedule,
)

from market_atlas.orchestration.pipeline import (
    DEFAULT_SETTINGS,
    REPOSITORY_ROOT,
    STAGES,
    LiveBackend,
    RefreshError,
    RefreshSession,
    load_settings,
    make_plan,
)

SETTINGS_PATH = os.environ.get("MARKETATLAS_PIPELINE_SETTINGS", str(DEFAULT_SETTINGS))
CONFIG_PATH = os.environ.get(
    "MARKETATLAS_CONFIG", str(REPOSITORY_ROOT / "configs/local.toml")
)


@resource(
    config_schema={
        "local_config": Field(str, default_value=CONFIG_PATH),
        "pipeline_settings": Field(str, default_value=SETTINGS_PATH),
        "as_of": Field(str, default_value=""),
    }
)
def refresh_session(context):
    try:
        from .recovery import RecoveryError, restore_checkpoint, selected_stages

        config = context.resource_config
        run = context.run
        selection = selected_stages(run)
        restored, captures = None, None
        if selection[0] != STAGES[0]:
            if not run.parent_run_id:
                raise RecoveryError(
                    "downstream selection requires a parent run; use Re-execute from failure"
                )
            parent = context.instance.get_run_by_id(run.parent_run_id)
            directory = parent.tags.get("marketatlas/checkpoint") if parent else None
            if not directory:
                raise RecoveryError(
                    "parent has no resumable checkpoint; launch a full fresh run"
                )
            plan, restored, captures = restore_checkpoint(
                directory, parent.run_id, run.run_id, selection[0]
            )
            if config["as_of"] and config["as_of"] != plan.run_date:
                raise RecoveryError("resume must retain the original run date")
        else:
            plan = make_plan(
                run.run_id, config["pipeline_settings"], as_of=config["as_of"] or None
            )
        path = Path(config["local_config"])
        if not path.is_absolute():
            path = REPOSITORY_ROOT / path
        backend = LiveBackend(plan, path)
    except RecoveryError as error:
        raise Failure(str(error), allow_retries=False) from None
    except Exception as error:  # noqa: BLE001 - hide driver/config details at the orchestration boundary
        raise Failure(
            f"refresh configuration failed ({type(error).__name__})",
            allow_retries=False,
        ) from None
    try:
        with RefreshSession(
            plan, backend, restored=restored, captures=captures
        ).open() as session:
            context.instance.add_run_tags(
                run.run_id, {"marketatlas/checkpoint": plan.run_directory}
            )
            yield session
    except RefreshError as error:
        raise Failure(str(error), allow_retries=False) from None


def _refresh_op(name, first=False):
    @op(
        name=name,
        ins={} if first else {"after": In(Nothing)},
        out=Out(Nothing),
        required_resource_keys={"refresh"},
        retry_policy=RetryPolicy(max_retries=2, delay=2),
    )
    def run(context):
        try:
            result = context.resources.refresh.step(name)
        except RefreshError as error:
            raise Failure(str(error), allow_retries=error.retryable) from None
        context.add_output_metadata(
            {"stage": name, "status": result.get("status", "complete")}
        )

    return run


OPERATIONS = [_refresh_op(name, first=i == 0) for i, name in enumerate(STAGES)]


@job(
    resource_defs={"refresh": refresh_session},
    executor_def=in_process_executor,
    tags={"marketatlas/pipeline": "fred_daily_refresh"},
    description="Refresh real FRED observations, context, full taxonomy, quality and a validated Power BI pack.",
)
def fred_daily_refresh():
    previous = OPERATIONS[0]()
    for operation in OPERATIONS[1:]:
        previous = operation(previous)


_settings = load_settings(SETTINGS_PATH)


@schedule(
    job=fred_daily_refresh,
    cron_schedule=_settings["cron_schedule"],
    execution_timezone=_settings["timezone"],
    default_status=DefaultScheduleStatus.STOPPED,
)
def fred_daily_schedule(context):
    # Scheduled date is explicit, so delayed ticks do not silently shift windows.
    scheduled = context.scheduled_execution_time.astimezone(
        ZoneInfo(_settings["timezone"])
    )
    return RunRequest(
        run_key=scheduled.isoformat(),
        run_config={
            "resources": {
                "refresh": {"config": {"as_of": scheduled.date().isoformat()}}
            }
        },
        tags={"marketatlas/run_date": scheduled.date().isoformat()},
    )


@op(
    config_schema={
        "output_directory": Field(
            str, default_value=str(REPOSITORY_ROOT / "data/generated/dagster-smoke")
        )
    }
)
def build_synthetic_powerbi_pack(context):
    from market_atlas.reporting.export import export_pack

    result = export_pack(Path(context.op_config["output_directory"]))
    context.add_output_metadata({"pack_id": result["pack_id"], "synthetic": True})
    return result["pack"]


@op
def validate_synthetic_powerbi_pack(pack: str):
    from market_atlas.reporting.export import validate_pack

    return validate_pack(Path(pack))


@job(executor_def=in_process_executor)
def synthetic_powerbi_smoke():
    validate_synthetic_powerbi_pack(build_synthetic_powerbi_pack())


@op(
    config_schema={
        "local_config": Field(str, default_value=CONFIG_PATH),
        "observation_start": Field(str, default_value="2024-01-01"),
        "observation_end": Field(str, default_value=""),
    }
)
def diagnose_fred_source_health(context):
    from market_atlas.source_health import run_diagnostics

    config = context.op_config
    output = REPOSITORY_ROOT / "data/generated/source-health" / context.run_id
    result = run_diagnostics(
        config["local_config"],
        output,
        start=config["observation_start"],
        end=config["observation_end"] or None,
    )
    context.add_output_metadata(
        {
            "status": result["status"],
            "output": str(output),
            "stale_series": result["summary"]["stale_series"],
            "stale_latest_attempt_skipped": result["summary"][
                "stale_latest_attempt_skipped"
            ],
            "undated_versions": result["summary"]["undated_versions"],
        }
    )


@job(
    executor_def=in_process_executor,
    description="Read-only FRED freshness, upstream attempts and vintage-policy diagnosis; success means checks completed, not data are fresh.",
)
def fred_source_health():
    diagnose_fred_source_health()


defs = Definitions(
    jobs=[fred_daily_refresh, synthetic_powerbi_smoke, fred_source_health],
    schedules=[fred_daily_schedule],
)
