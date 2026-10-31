"""Exercise rolling windows, stage sequencing, checkpoints and optional Dagster."""

import contextlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from market_atlas.database import DatabaseUnavailable
from market_atlas.orchestration.pipeline import (
    REPOSITORY_ROOT,
    STAGES,
    LiveBackend,
    RefreshError,
    RefreshSession,
    check_upstream,
    make_plan,
    write_json,
)

HAS_DAGSTER = importlib.util.find_spec("dagster") is not None


def test_root(directory):
    root = Path(directory)
    (root / "configs").mkdir()
    for filename in ("pilot.toml", "context_pilot.toml", "orchestration.toml"):
        shutil.copyfile(
            REPOSITORY_ROOT / "configs" / filename, root / "configs" / filename
        )
    return root


def plan_at(root, run_id="test-run", now=None):
    return make_plan(
        run_id, root=root, now=now or datetime(2026, 10, 31, 1, 0, tzinfo=UTC)
    )


class RecordingBackend:
    def __init__(self, failure=None, transient=False):
        self.calls = []
        self.failure, self.transient = failure, transient
        self.locked = False

    @contextlib.contextmanager
    def lock(self):
        self.locked = True
        try:
            yield
        finally:
            self.locked = False

    def run_stage(self, name, state):
        assert self.locked
        self.calls.append(name)
        if name == self.failure:
            if self.transient:
                self.failure = None
                raise DatabaseUnavailable("secret-test-password")
            raise ValueError("secret-test-password")
        return {"status": "complete"}


class RefreshPlanTests(unittest.TestCase):
    def test_windows_follow_new_york_date_and_preserve_bounded_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan = plan_at(root)
            self.assertEqual(plan.run_date, "2026-10-30")
            self.assertEqual(plan.observation.observation_end, "2026-10-30")
            self.assertEqual(plan.observation.knowledge_cutoff, "2026-10-30")
            self.assertEqual(plan.context.release_start, "2026-10-23")
            self.assertEqual(plan.context.release_end, "2026-12-29")
            self.assertEqual(plan.context.series_ids, ("CPIAUCSL", "GDP", "UNRATE"))
            self.assertEqual(plan.observation.observation_start, "2024-01-01")
            self.assertFalse(Path(plan.run_directory).exists())
            for instant, day in (
                (datetime(2026, 11, 1, 3, 30, tzinfo=UTC), "2026-10-31"),
                (datetime(2026, 11, 1, 6, 30, tzinfo=UTC), "2026-11-01"),
            ):
                self.assertEqual(plan_at(root, now=instant).run_date, day)

    def test_future_dates_unsafe_run_ids_and_tracked_output_locations_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            with self.assertRaises(ValueError):
                make_plan(
                    "x",
                    root=root,
                    as_of="2026-11-01",
                    now=datetime(2026, 10, 30, tzinfo=UTC),
                )
            with self.assertRaises(ValueError):
                plan_at(root, "../escape")
            settings = root / "configs/orchestration.toml"
            settings.write_text(
                settings.read_text().replace(
                    "data/generated/daily", "docs/private-data"
                )
            )
            with self.assertRaisesRegex(ValueError, "ignored"):
                plan_at(root)

    def test_upstream_marker_requires_success_recent_aware_timestamp(self):
        from dataclasses import replace

        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan = plan_at(root)
            self.assertEqual(check_upstream(plan)["upstream_freshness"], "not_verified")
            marker = root / "upstream.json"
            plan = replace(plan, upstream_success_file=str(marker))
            clock = datetime.fromisoformat(plan.captured_at)
            write_json(
                marker,
                {
                    "status": "success",
                    "completed_at": (clock - timedelta(hours=1)).isoformat(),
                },
            )
            self.assertEqual(check_upstream(plan)["status"], "success_marker_verified")
            for status, stamp in (
                ("failed", clock),
                ("success", clock - timedelta(hours=37)),
                ("success", clock + timedelta(seconds=1)),
                ("success", clock.replace(tzinfo=None)),
            ):
                write_json(
                    marker, {"status": status, "completed_at": stamp.isoformat()}
                )
                with self.assertRaises(ValueError):
                    check_upstream(plan)

    def test_success_checkpoints_all_stages_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan, backend = plan_at(root), RecordingBackend()
            with RefreshSession(plan, backend).open() as session:
                for name in STAGES:
                    session.step(name)
            saved = json.loads((Path(plan.run_directory) / "run.json").read_text())
            self.assertEqual(backend.calls, list(STAGES))
            self.assertEqual(saved["status"], "complete")
            self.assertEqual(saved["completed_stages"], list(STAGES))
            self.assertFalse(backend.locked)

    def test_failure_is_sanitized_and_prevents_downstream_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan, backend = plan_at(root), RecordingBackend(failure="publish_context")
            with (
                self.assertRaises(RefreshError) as caught,
                RefreshSession(plan, backend).open() as session,
            ):
                for name in STAGES:
                    session.step(name)
            saved = (Path(plan.run_directory) / "run.json").read_text()
            self.assertNotIn("secret-test-password", saved + str(caught.exception))
            self.assertEqual(json.loads(saved)["status"], "failed")
            self.assertNotIn("export_powerbi", backend.calls)
            self.assertFalse(backend.locked)

    def test_retry_uses_same_stage_and_extraction_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan, backend = (
                plan_at(root),
                RecordingBackend(failure="source_gate", transient=True),
            )
            with RefreshSession(plan, backend).open() as session:
                with self.assertRaises(RefreshError) as caught:
                    session.step("source_gate")
                self.assertTrue(caught.exception.retryable)
                session.step("source_gate")
                self.assertEqual(session.state["stages"]["source_gate"]["attempts"], 2)
                with self.assertRaises(RefreshError):
                    session.step("export_powerbi")
            live = LiveBackend.__new__(LiveBackend)
            live.directory = Path(plan.run_directory)
            capture = {"manifest": {"extracted_at": plan.captured_at}, "rows": [1]}
            self.assertEqual(live._capture("observations", lambda: capture), capture)
            self.assertEqual(
                live._capture("observations", lambda: self.fail("recaptured retry")),
                capture,
            )

    def test_live_connections_enforce_roles_without_reading_secrets_into_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            config = root / "configs/local.toml"
            config.write_text("""[source_database]
host="localhost"
port=5432
database="test"
username="fred"
password="secret-test-password"
role="marketatlas_source_reader"
[target_database]
host="localhost"
port=5432
database="test"
username="fred"
password="secret-test-password"
""")
            plan = plan_at(root)
            backend = LiveBackend(plan, config)
            self.assertEqual(backend.report.role, "marketatlas_report_reader")
            self.assertNotIn("secret-test-password", json.dumps(plan.document()))
            config.write_text(
                config.read_text().replace(
                    'role="marketatlas_source_reader"', 'role="marketatlas_writer"'
                )
            )
            with self.assertRaises(ValueError):
                LiveBackend(plan, config)


@unittest.skipUnless(HAS_DAGSTER, "optional Dagster runtime")
class DagsterRefreshTests(unittest.TestCase):
    def test_source_health_job_reports_findings_without_running_upstream(self):
        from market_atlas.orchestration.definitions import fred_source_health

        with patch(
            "market_atlas.source_health.run_diagnostics",
            return_value={
                "status": "diagnosis_complete",
                "summary": {
                    "stale_series": 181,
                    "stale_latest_attempt_skipped": 179,
                    "undated_versions": 35433,
                },
            },
        ) as diagnose:
            result = fred_source_health.execute_in_process()
        self.assertTrue(result.success)
        self.assertEqual(diagnose.call_count, 1)
        self.assertEqual(diagnose.call_args.kwargs["start"], "2024-01-01")

    def test_definitions_load_without_database_access_and_schedule_has_local_date(self):
        from dagster import Definitions, build_schedule_context

        from market_atlas.orchestration import definitions

        with patch(
            "psycopg.connect",
            side_effect=AssertionError("unexpected database connection"),
        ):
            import importlib

            definitions = importlib.reload(definitions)
            Definitions.validate_loadable(definitions.defs)
        context = build_schedule_context(
            scheduled_execution_time=datetime(2026, 10, 31, 1, 0, tzinfo=UTC)
        )
        request = definitions.fred_daily_schedule(context)
        self.assertEqual(
            request.run_config["resources"]["refresh"]["config"]["as_of"], "2026-10-30"
        )
        self.assertEqual(
            definitions.fred_daily_schedule.execution_timezone, "America/New_York"
        )
        self.assertEqual(definitions.fred_daily_schedule.cron_schedule, "30 18 * * *")

    def test_real_dag_orders_stages_and_stops_on_failure(self):
        from market_atlas.orchestration.definitions import fred_daily_refresh

        for failure in (None, "publish_context"):
            with tempfile.TemporaryDirectory() as directory:
                root = test_root(directory)
                plan, backend = plan_at(root), RecordingBackend(failure=failure)
                with (
                    patch(
                        "market_atlas.orchestration.definitions.make_plan",
                        return_value=plan,
                    ),
                    patch(
                        "market_atlas.orchestration.definitions.LiveBackend",
                        return_value=backend,
                    ),
                ):
                    result = fred_daily_refresh.execute_in_process(raise_on_error=False)
                self.assertEqual(result.success, failure is None)
                if failure is None:
                    self.assertEqual(backend.calls, list(STAGES))
                else:
                    self.assertNotIn("export_powerbi", backend.calls)
                    checkpoint = json.loads(
                        (Path(plan.run_directory) / "run.json").read_text()
                    )
                    self.assertEqual(checkpoint["status"], "failed")

    def test_failed_dagster_op_records_report_failure_at_resource_teardown(self):
        from unittest.mock import Mock

        from market_atlas.orchestration.definitions import fred_daily_refresh

        with tempfile.TemporaryDirectory() as directory:
            plan = plan_at(test_root(directory))
            backend = RecordingBackend(failure="extract_catalog")
            backend.record_report_failure = Mock()
            with (
                patch(
                    "market_atlas.orchestration.definitions.make_plan",
                    return_value=plan,
                ),
                patch(
                    "market_atlas.orchestration.definitions.LiveBackend",
                    return_value=backend,
                ),
            ):
                result = fred_daily_refresh.execute_in_process(raise_on_error=False)
            self.assertFalse(result.success)
            backend.record_report_failure.assert_called_once_with(
                "extract_catalog", "ValueError"
            )

    def test_dagster_retries_a_transient_failure_before_downstream_steps(self):
        from market_atlas.orchestration.definitions import fred_daily_refresh

        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            plan, backend = (
                plan_at(root),
                RecordingBackend(failure="extract_catalog", transient=True),
            )
            with (
                patch(
                    "market_atlas.orchestration.definitions.make_plan",
                    return_value=plan,
                ),
                patch(
                    "market_atlas.orchestration.definitions.LiveBackend",
                    return_value=backend,
                ),
            ):
                result = fred_daily_refresh.execute_in_process(raise_on_error=False)
            self.assertTrue(result.success)
            self.assertEqual(backend.calls.count("extract_catalog"), 2)
            self.assertTrue(
                any(event.is_step_up_for_retry for event in result.all_events)
            )

    def test_dagster_synthetic_smoke_has_real_ingestible_files(self):
        from market_atlas.orchestration.definitions import synthetic_powerbi_smoke

        with tempfile.TemporaryDirectory() as directory:
            result = synthetic_powerbi_smoke.execute_in_process(
                run_config={
                    "ops": {
                        "build_synthetic_powerbi_pack": {
                            "config": {"output_directory": directory}
                        }
                    }
                }
            )
            self.assertTrue(result.success)
            checked = result.output_for_node("validate_synthetic_powerbi_pack")
            self.assertEqual(checked["counts"]["correlations"], 32)

    def test_instance_configuration_limits_concurrent_runs(self):
        from dagster import DagsterInstance

        with tempfile.TemporaryDirectory() as directory:
            shutil.copyfile(
                REPOSITORY_ROOT / "orchestration/dagster.yaml",
                Path(directory) / "dagster.yaml",
            )
            with DagsterInstance.from_config(directory) as instance:
                self.assertEqual(
                    instance.run_coordinator.get_run_queue_config().max_concurrent_runs,
                    1,
                )


@unittest.skipUnless(
    os.environ.get("MARKETATLAS_TEST_DATABASE") == "1", "opt-in advisory-lock check"
)
class RefreshLockDatabaseTests(unittest.TestCase):
    def test_second_refresh_cannot_overlap_and_lock_is_released(self):
        plan = make_plan("lock-check")
        config = REPOSITORY_ROOT / "configs/local.toml"
        first, second = LiveBackend(plan, config), LiveBackend(plan, config)
        with (
            first.lock(),
            self.assertRaisesRegex(RefreshError, "RefreshAlreadyRunning"),
            second.lock(),
        ):
            self.fail("overlapping refresh acquired the lock")
        with second.lock():
            self.assertIsNotNone(second.lock_connection)
