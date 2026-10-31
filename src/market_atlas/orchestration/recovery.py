"""Restore a completed prefix without changing its input selection or captures."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from market_atlas.config import MacroContextConfig, MacroMedallionConfig
from market_atlas.contracts import sha256


class RecoveryError(ValueError):
    """A safe operator-facing reason why a checkpoint cannot be resumed."""


CHECKPOINT_VERSION = 3
CAPTURE_PRODUCERS = {
    "contract_gate.json": "source_gate",
    "series_selection.json": "source_gate",
    "observations.json": "extract_observations",
    "context.json": "extract_context",
    "catalog.json": "extract_catalog",
    "quality.json": "extract_quality",
    "export.json": "export_powerbi",
}
PUBLICATION_STAGES = {
    "publish_context": "macro_context",
    "publish_graph": "macro_economic_graph",
    "publish_quality": "macro_revision_quality",
}


def artifact_hashes(directory):
    directory = Path(directory)
    return {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in CAPTURE_PRODUCERS
        if (directory / name).is_file()
    }


def selected_stages(run):
    from .pipeline import STAGES

    selected = run.step_keys_to_execute or run.resolved_op_selection or STAGES
    ordered = [stage for stage in STAGES if stage in selected]
    if not ordered or set(ordered) != set(selected):
        raise RecoveryError("unknown refresh step selection")
    start = STAGES.index(ordered[0])
    if ordered != list(STAGES[start : start + len(ordered)]):
        raise RecoveryError("refresh re-execution requires contiguous stages")
    return ordered


def restore_checkpoint(
    directory, parent_run_id, child_run_id, start_stage, *, now=None
):
    from .pipeline import STAGES, RefreshPlan

    directory = Path(directory).resolve()
    if directory.name != parent_run_id or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", child_run_id
    ):
        raise RecoveryError("invalid recovery run identity")
    document = json.loads((directory / "plan.json").read_text())
    parent = json.loads((directory / "run.json").read_text())
    if parent.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise RecoveryError("legacy checkpoint requires a fresh full run")
    if (
        parent.get("run_id") != parent_run_id
        or document.get("run_id") != parent_run_id
        or Path(document["run_directory"]).resolve() != directory
        or parent.get("plan_sha256") != sha256(document)
        or parent.get("stage_order") != list(STAGES)
    ):
        raise RecoveryError("checkpoint plan or stage order differs")
    completed = parent.get("completed_stages", [])
    if completed != list(STAGES[: len(completed)]):
        raise RecoveryError("checkpoint is not a completed prefix")
    start = STAGES.index(start_stage)
    if start > len(completed):
        raise RecoveryError("checkpoint lacks prerequisite stages")
    prefix = list(STAGES[:start])
    if any(
        parent["stages"].get(name, {}).get("status") != "complete" for name in prefix
    ):
        raise RecoveryError("checkpoint prerequisite is incomplete")
    needed = {
        name
        for name, producer in CAPTURE_PRODUCERS.items()
        if STAGES.index(producer) < start
    }
    captures = {
        name: digest
        for name, digest in parent.get("artifacts", {}).items()
        if name in CAPTURE_PRODUCERS and STAGES.index(CAPTURE_PRODUCERS[name]) <= start
    }
    if not needed <= captures.keys():
        raise RecoveryError("checkpoint lacks prerequisite input captures")
    for name, expected in captures.items():
        path = directory / name
        if (
            path.is_symlink()
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise RecoveryError("checkpoint input capture is missing or modified")
    for field, cls in (
        ("observation", MacroMedallionConfig),
        ("context", MacroContextConfig),
    ):
        values = dict(document[field])
        values["series_ids"] = tuple(values["series_ids"])
        document[field] = cls(**values)
    old_plan = RefreshPlan(**document)
    child = replace(
        old_plan,
        run_id=child_run_id,
        run_directory=str(directory.parent / child_run_id),
        captured_at=(now or datetime.now(UTC)).astimezone(UTC).isoformat(),
    )
    state = {
        "completed_stages": prefix,
        "stages": {name: deepcopy(parent["stages"][name]) for name in prefix},
        "root_run_id": parent.get("root_run_id", parent_run_id),
        "resumed_from_run_id": parent_run_id,
        "backend_identity": parent.get("backend_identity"),
        "publication_state": dict(parent.get("publication_state", {})),
    }
    return child, state, {name: directory / name for name in captures}


def copy_captures(captures, directory):
    directory = Path(directory)
    for name, source in captures.items():
        # Copy rather than hard-link so child retries cannot mutate parent inputs.
        shutil.copyfile(source, directory / name)
