"""Recover frozen prerequisites and exercise Dagster's real parent-run API."""

import contextlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_orchestration import RecordingBackend, plan_at, test_root

from market_atlas.orchestration.pipeline import (
    STAGES,
    RefreshError,
    RefreshSession,
    write_json,
)
from market_atlas.orchestration.recovery import (
    CAPTURE_PRODUCERS,
    RecoveryError,
    restore_checkpoint,
)

HAS_DAGSTER = importlib.util.find_spec("dagster") is not None


class CapturingBackend(RecordingBackend):
    identity = "same-database-identity"

    def __init__(self, plan, **kwargs):
        super().__init__(**kwargs)
        self.directory = Path(plan.run_directory)

    def run_stage(self, name, state):
        result = super().run_stage(name, state)
        for filename, producer in CAPTURE_PRODUCERS.items():
            if producer == name:
                write_json(
                    self.directory / filename, {"capture": filename, "original": True}
                )
        return result


def failed_parent(root):
    plan = plan_at(root, "parent")
    backend = CapturingBackend(plan, failure="publish_graph")
    with (
        contextlib.suppress(RefreshError),
        RefreshSession(plan, backend).open() as session,
    ):
        for name in STAGES:
            session.step(name)
    return plan


class RecoveryTests(unittest.TestCase):
    def test_restore_prefix_captures_original_dates_and_parent_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            parent = failed_parent(root)
            original = (Path(parent.run_directory) / "run.json").read_bytes()
            plan, state, captures = restore_checkpoint(
                parent.run_directory, "parent", "child", "publish_graph"
            )
            self.assertEqual(plan.run_date, parent.run_date)
            self.assertEqual(plan.context, parent.context)
            self.assertEqual(state["completed_stages"], list(STAGES[:7]))
            backend = CapturingBackend(plan)
            with RefreshSession(
                plan, backend, restored=state, captures=captures
            ).open() as session:
                for name in STAGES[7:]:
                    session.step(name)
            self.assertEqual(backend.calls, list(STAGES[7:]))
            self.assertEqual(
                (Path(parent.run_directory) / "run.json").read_bytes(), original
            )
            write_json(Path(plan.run_directory) / "catalog.json", {"child_only": True})
            self.assertNotIn(
                "child_only", (Path(parent.run_directory) / "catalog.json").read_text()
            )
            saved = json.loads((Path(plan.run_directory) / "run.json").read_text())
            self.assertEqual(saved["status"], "complete")
            self.assertEqual(saved["root_run_id"], "parent")

    def test_missing_modified_or_incompatible_checkpoints_are_rejected(self):
        for failure in ("missing", "modified", "legacy", "plan", "prefix", "skip"):
            with tempfile.TemporaryDirectory() as directory:
                root = test_root(directory)
                parent = failed_parent(root)
                path = Path(parent.run_directory)
                if failure == "missing":
                    (path / "catalog.json").unlink()
                elif failure == "modified":
                    (path / "catalog.json").write_text("{}")
                elif failure == "legacy":
                    state = json.loads((path / "run.json").read_text())
                    state.pop("checkpoint_version")
                    write_json(path / "run.json", state)
                elif failure == "plan":
                    plan = json.loads((path / "plan.json").read_text())
                    plan["run_date"] = "2020-01-01"
                    write_json(path / "plan.json", plan)
                elif failure == "prefix":
                    state = json.loads((path / "run.json").read_text())
                    state["completed_stages"].pop(0)
                    write_json(path / "run.json", state)
                start = "export_powerbi" if failure == "skip" else "publish_graph"
                with self.assertRaises((RecoveryError, FileNotFoundError)):
                    restore_checkpoint(path, "parent", "child", start)

    def test_changed_database_and_advanced_publication_cannot_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            parent = failed_parent(root)
            plan, state, captures = restore_checkpoint(
                parent.run_directory, "parent", "child", "publish_graph"
            )
            backend = CapturingBackend(plan)
            backend.identity = "different-database"
            with self.assertRaisesRegex(RefreshError, "DatabaseConnectionChanged"):
                RefreshSession(plan, backend, restored=state, captures=captures)
            backend.identity = state["backend_identity"]
            backend.publication_state = lambda: {"macro_context": "newer-publication"}
            with (
                self.assertRaisesRegex(RefreshError, "PublicationsAdvanced"),
                RefreshSession(plan, backend, restored=state, captures=captures).open(),
            ):
                self.fail("advanced publication was accepted")

    def test_a_second_failure_can_resume_from_the_child_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            parent = failed_parent(root)
            plan, state, captures = restore_checkpoint(
                parent.run_directory, "parent", "child", "publish_graph"
            )
            backend = CapturingBackend(plan, failure="publish_quality")
            with (
                contextlib.suppress(RefreshError),
                RefreshSession(
                    plan, backend, restored=state, captures=captures
                ).open() as session,
            ):
                for name in STAGES[7:]:
                    session.step(name)
            final_plan, final_state, final_captures = restore_checkpoint(
                plan.run_directory, "child", "grandchild", "publish_quality"
            )
            final_backend = CapturingBackend(final_plan)
            with RefreshSession(
                final_plan, final_backend, restored=final_state, captures=final_captures
            ).open() as session:
                for name in STAGES[9:]:
                    session.step(name)
            self.assertEqual(final_backend.calls, list(STAGES[9:]))
            self.assertEqual(session.state["root_run_id"], "parent")
            self.assertEqual(session.state["resumed_from_run_id"], "child")
            self.assertEqual(session.state["status"], "complete")

    def test_failed_resume_preflight_never_executes_a_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = failed_parent(test_root(directory))
            plan, state, captures = restore_checkpoint(
                parent.run_directory, "parent", "child", "publish_graph"
            )
            backend = CapturingBackend(plan)

            def reject():
                raise RefreshError("resume", "SourceContractChanged")

            backend.validate_resume = reject
            with (
                self.assertRaisesRegex(RefreshError, "SourceContractChanged"),
                RefreshSession(plan, backend, restored=state, captures=captures).open(),
            ):
                self.fail("failed preflight yielded a live session")
            self.assertEqual(backend.calls, [])


@unittest.skipUnless(HAS_DAGSTER, "optional Dagster runtime")
class DagsterRecoveryTests(unittest.TestCase):
    def test_native_reexecute_from_failure_restores_prefix_without_rerunning_it(self):
        from dagster import (
            DagsterInstance,
            ReexecutionOptions,
            execute_job,
            reconstructable,
        )

        from market_atlas.orchestration.definitions import fred_daily_refresh

        with tempfile.TemporaryDirectory() as directory:
            root = test_root(directory)
            instances = root / "instance"
            instances.mkdir()
            write_json(instances / "dagster.yaml", {"telemetry": {"enabled": False}})
            backends = []

            def make(run_id, *args, **kwargs):
                return plan_at(root, run_id)

            def backend(plan, config):
                result = CapturingBackend(
                    plan, failure="publish_graph" if not backends else None
                )
                backends.append(result)
                return result

            with (
                DagsterInstance.from_config(str(instances)) as instance,
                patch(
                    "market_atlas.orchestration.definitions.make_plan", side_effect=make
                ),
                patch(
                    "market_atlas.orchestration.definitions.LiveBackend",
                    side_effect=backend,
                ),
            ):
                parent = execute_job(
                    reconstructable(fred_daily_refresh),
                    instance=instance,
                    raise_on_error=False,
                )
                self.assertFalse(parent.success)
                options = ReexecutionOptions.from_failure(parent.run_id, instance)
                child = execute_job(
                    reconstructable(fred_daily_refresh),
                    instance=instance,
                    reexecution_options=options,
                    raise_on_error=False,
                )
                self.assertTrue(child.success)
                self.assertEqual(backends[1].calls, list(STAGES[7:]))
                run = json.loads(
                    (
                        root / "data/generated/daily" / child.run_id / "run.json"
                    ).read_text()
                )
                self.assertEqual(run["resumed_from_run_id"], parent.run_id)
                self.assertEqual(run["status"], "complete")

    def test_downstream_selection_without_parent_fails_with_actionable_message(self):
        from market_atlas.orchestration.definitions import fred_daily_refresh

        result = fred_daily_refresh.execute_in_process(
            op_selection=["extract_catalog"], raise_on_error=False
        )
        self.assertFalse(result.success)
        errors = [
            event.event_specific_data.error.to_string()
            for event in result.all_events
            if event.event_type_value == "RESOURCE_INIT_FAILURE"
        ]
        self.assertTrue(any("parent run" in error for error in errors))
