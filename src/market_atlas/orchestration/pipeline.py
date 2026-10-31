"""Rolling refresh plans, private checkpoints and sequential execution."""

from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from market_atlas.config import (
    MacroContextConfig,
    MacroMedallionConfig,
    ReportDatabaseConfig,
    load_macro_context,
    load_macro_medallion,
    load_report_database,
    load_source_database,
    load_target_database,
)
from market_atlas.contracts import canonical_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SETTINGS = Path("configs/orchestration.toml")
STAGES = (
    "source_gate",
    "extract_observations",
    "ingest_observations",
    "extract_context",
    "publish_context",
    "validate_context",
    "extract_catalog",
    "publish_graph",
    "extract_quality",
    "publish_quality",
    "export_powerbi",
    "validate_powerbi",
    "complete_refresh",
)
LIVE_PUBLICATIONS = ("macro_economic_graph", "macro_context", "macro_revision_quality")
LOCK_KEY = 194700121


class RefreshError(RuntimeError):
    def __init__(self, stage, error_type, retryable=False):
        self.stage, self.error_type, self.retryable = stage, error_type, retryable
        super().__init__(
            f"{stage} failed ({error_type}); see the private run checkpoint"
        )


@dataclass(frozen=True)
class RefreshPlan:
    run_id: str
    run_date: str
    captured_at: str
    timezone: str
    run_directory: str
    pack_directory: str
    observation: MacroMedallionConfig
    context: MacroContextConfig
    page_size: int
    max_export_rows: int
    upstream_success_file: str
    upstream_max_age_hours: int

    def document(self):
        return asdict(self)


def _resolve(root, value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _output(root, value):
    path = _resolve(root, value)
    if not path.is_relative_to(root / "data/generated"):
        raise ValueError("pipeline output must stay inside ignored data/generated")
    return path


def load_settings(path=DEFAULT_SETTINGS, root=REPOSITORY_ROOT):
    root = Path(root).resolve()
    section = tomllib.loads(_resolve(root, path).read_text())["pipeline"]
    for key, low, high in (
        ("release_days_back", 0, 366),
        ("release_days_ahead", 1, 366),
        ("page_size", 1, 1000),
        ("max_export_rows", 1, 1000000),
        ("upstream_max_age_hours", 1, 168),
    ):
        if type(section.get(key)) is not int or not low <= section[key] <= high:
            raise ValueError(f"invalid pipeline setting: {key}")
    ZoneInfo(section["timezone"])
    _output(root, section["output_directory"])
    _output(root, section["pack_directory"])
    return section


def make_plan(
    run_id,
    settings_path=DEFAULT_SETTINGS,
    *,
    as_of=None,
    now=None,
    root=REPOSITORY_ROOT,
):
    root = Path(root).resolve()
    settings = load_settings(settings_path, root)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
        raise ValueError("run_id must be a safe single directory name")
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("pipeline clock must have a timezone")
    today = now.astimezone(ZoneInfo(settings["timezone"])).date()
    day = date.fromisoformat(as_of) if as_of else today
    if day > today:
        raise ValueError("run date must not be in the future")
    observation = load_macro_medallion(_resolve(root, settings["observation_config"]))
    if date.fromisoformat(observation.observation_start) > day:
        raise ValueError("run date precedes configured observation history")
    context = load_macro_context(_resolve(root, settings["context_config"]))
    observation = replace(
        observation, observation_end=day.isoformat(), knowledge_cutoff=day.isoformat()
    )
    context = replace(
        context,
        release_start=(day - timedelta(days=settings["release_days_back"])).isoformat(),
        release_end=(day + timedelta(days=settings["release_days_ahead"])).isoformat(),
    )
    marker = settings.get("upstream_success_file", "")
    return RefreshPlan(
        run_id,
        day.isoformat(),
        now.astimezone(UTC).isoformat(),
        settings["timezone"],
        str(_output(root, settings["output_directory"]) / run_id),
        str(_output(root, settings["pack_directory"])),
        observation,
        context,
        settings["page_size"],
        settings["max_export_rows"],
        str(_resolve(root, marker)) if marker else "",
        settings["upstream_max_age_hours"],
    )


def write_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".refresh-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_bytes(document))
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def check_upstream(plan):
    if not plan.upstream_success_file:
        return {"status": "existing_postgres", "upstream_freshness": "not_verified"}
    marker = json.loads(Path(plan.upstream_success_file).read_text())
    completed = datetime.fromisoformat(marker["completed_at"])
    now = datetime.fromisoformat(plan.captured_at)
    if completed.tzinfo is None or marker.get("status") != "success":
        raise ValueError("upstream success marker is invalid")
    age = (now - completed).total_seconds()
    if not 0 <= age <= plan.upstream_max_age_hours * 3600:
        raise ValueError("upstream success marker is stale or in the future")
    return {
        "status": "success_marker_verified",
        "completed_at": completed.astimezone(UTC).isoformat(),
    }


class LiveBackend:
    def __init__(self, plan, config_path):
        self.plan = plan
        self.directory = Path(plan.run_directory)
        self.source = load_source_database(config_path)
        if self.source.role != "marketatlas_source_reader":
            raise ValueError(
                "pipeline source access requires marketatlas_source_reader"
            )
        self.target = load_target_database(config_path)
        document = tomllib.loads(Path(config_path).read_text())
        if "report_database" in document:
            self.report = load_report_database(config_path)
        else:
            self.report = ReportDatabaseConfig(
                **{
                    k: getattr(self.target, k)
                    for k in ("host", "port", "database", "username", "password")
                }
            )
        self.lock_connection = None

    @contextmanager
    def lock(self):
        import psycopg

        kwargs = self.target.connection_kwargs() | {
            "application_name": "marketatlas-refresh-lock"
        }
        with psycopg.connect(**kwargs, autocommit=True) as connection:
            connection.execute("SET ROLE marketatlas_writer")
            acquired = connection.execute(
                "SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)
            ).fetchone()[0]
            if not acquired:
                raise RefreshError("prepare", "RefreshAlreadyRunning")
            self.lock_connection = connection
            try:
                yield
            finally:
                connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
                self.lock_connection = None

    def _capture(self, name, extract):
        path = self.directory / (name + ".json")
        if not path.exists():
            payload = extract()
            if name in {"context", "catalog", "quality"}:
                payload["manifest"]["source_contract_verification"] = json.loads(
                    (self.directory / "contract_gate.json").read_text()
                )
            write_json(path, payload)
        return json.loads(path.read_text())

    def _read(self, name):
        return json.loads((self.directory / (name + ".json")).read_text())

    @staticmethod
    def _published(result):
        if "failed" in result.get("status", ""):
            raise RuntimeError("publication failed")
        return {
            k: v
            for k, v in result.items()
            if k
            in {
                "status",
                "snapshot_id",
                "snapshot_status",
                "row_count",
                "output_sha256",
                "node_count",
                "edge_count",
                "selected_series_count",
                "unknown_count",
            }
        }

    def run_stage(self, name, state):
        from market_atlas.adapters import macro_context, macro_medallion
        from market_atlas.database import inspect_source
        from market_atlas.graph.macro_economic import build_macro_economic_graph
        from market_atlas.ingestion.macro_medallion import ingest
        from market_atlas.publishing.macro_context import (
            ingest_context_extract,
            publish_context_snapshot,
            validate_context_publication,
        )
        from market_atlas.publishing.revision_quality import publish_revision_quality
        from market_atlas.reporting.export import export_pack, validate_pack
        from market_atlas.source_catalog import build_source_catalog
        from market_atlas.source_contracts import verify_source_contracts

        # Stop if the session holding the cross-process refresh lock was lost.
        self.lock_connection.execute("SELECT 1")
        if name == "source_gate":
            upstream = check_upstream(self.plan)
            catalog = build_source_catalog(inspect_source(self.source))
            gate = verify_source_contracts(catalog)
            if gate["status"] != "valid":
                raise ValueError("source contract gate failed")
            write_json(
                self.directory / "contract_gate.json",
                {
                    k: gate[k]
                    for k in (
                        "status",
                        "registry_version",
                        "catalog_fingerprint_sha256",
                    )
                },
            )
            return {
                "status": "valid",
                "upstream": upstream,
                "catalog_fingerprint_sha256": gate["catalog_fingerprint_sha256"],
            }
        if name == "extract_observations":
            payload = self._capture(
                "observations",
                lambda: macro_medallion.extract(self.source, self.plan.observation),
            )
            return {
                "status": "captured",
                "observation_count": len(payload["macro_observations"]),
            }
        if name == "ingest_observations":
            result = ingest(self.target, self._read("observations"))
            return {
                k: v
                for k, v in result.items()
                if isinstance(v, (int, bool)) or k == "status"
            }
        if name == "extract_context":
            payload = self._capture(
                "context", lambda: macro_context.extract(self.source, self.plan.context)
            )
            return {
                "status": "captured",
                "series_count": len(payload["series_taxonomy"]),
                "release_count": len(payload["release_events"]),
            }
        if name == "publish_context":
            payload = self._read("context")
            ingest_context_extract(self.target, payload)
            return self._published(publish_context_snapshot(self.target, payload))
        if name == "validate_context":
            result = validate_context_publication(self.target, self._read("context"))
            if result["status"] != "valid":
                raise ValueError("context publication validation failed")
            return {"status": "valid", "counts": result["actual_counts"]}
        if name == "extract_catalog":
            payload = self._capture(
                "catalog",
                lambda: macro_context.extract_series_catalog(
                    self.source, self.plan.page_size, False
                ),
            )
            return {
                "status": "captured",
                "series_count": len(payload["series_taxonomy"]),
            }
        if name == "publish_graph":
            payload = self._read("catalog")
            if payload["manifest"].get("selection_scope") != "all_approved_dim_series":
                raise ValueError("daily graph requires the full approved catalog")
            return self._published(
                build_macro_economic_graph(self.target, payload)["publication"]
            )
        if name == "extract_quality":
            payload = self._capture(
                "quality",
                lambda: macro_context.extract_revision_summary(
                    self.source, list(self.plan.context.series_ids), self.plan.page_size
                ),
            )
            return {
                "status": "captured",
                "selected_count": len(self.plan.context.series_ids),
                "missing_count": len(payload["missing_series_ids"]),
            }
        if name == "publish_quality":
            return self._published(
                publish_revision_quality(self.target, self._read("quality"))
            )
        if name == "export_powerbi":
            result = export_pack(
                Path(self.plan.pack_directory),
                config=self.report,
                publications=LIVE_PUBLICATIONS,
                max_rows=self.plan.max_export_rows,
            )
            write_json(self.directory / "export.json", result)
            return result
        if name == "validate_powerbi":
            result = validate_pack(Path(self._read("export")["pack"]))
            expected = {
                "macro_nodes": state["stages"]["extract_catalog"]["result"][
                    "series_count"
                ],
                "revision_quality": len(self.plan.context.series_ids),
            }
            if (
                result["counts"]["macro_nodes"] < expected["macro_nodes"]
                or result["counts"]["revision_quality"] != expected["revision_quality"]
            ):
                raise ValueError("export coverage differs from the configured captures")
            return result
        if name == "complete_refresh":
            return {"status": "complete", "pack_id": self._read("export")["pack_id"]}
        raise ValueError("unknown refresh stage")


class RefreshSession:
    def __init__(self, plan, backend):
        self.plan, self.backend = plan, backend
        self.state = {
            "run_id": plan.run_id,
            "status": "prepared",
            "completed_stages": [],
            "stages": {},
        }
        self.directory = Path(plan.run_directory)

    def save(self):
        write_json(self.directory / "run.json", self.state)

    @contextmanager
    def open(self):
        self.directory.mkdir(parents=True, exist_ok=False)
        write_json(self.directory / "plan.json", self.plan.document())
        self.save()
        try:
            with self.backend.lock():
                self.state["status"] = "running"
                self.save()
                yield self
        except BaseException as error:
            self.state["status"] = "failed"
            self.state["error_type"] = type(error).__name__
            self.save()
            raise
        finally:
            if self.state["status"] not in {"complete", "failed"}:
                self.state["status"] = "incomplete"
                self.save()

    def step(self, name):
        from market_atlas.database import DatabaseUnavailable

        if len(self.state["completed_stages"]) == len(STAGES):
            raise RefreshError(name, "RunAlreadyComplete")
        expected = STAGES[len(self.state["completed_stages"])]
        if name != expected:
            raise RefreshError(name, "StageOrderError")
        attempts = self.state["stages"].get(name, {}).get("attempts", 0) + 1
        self.state["stages"][name] = {"status": "running", "attempts": attempts}
        self.state["status"] = "running"
        self.save()
        try:
            result = self.backend.run_stage(name, self.state)
        except Exception as error:  # noqa: BLE001 - hide driver/config details at the orchestration boundary
            self.state["stages"][name].update(
                status="failed", error_type=type(error).__name__
            )
            self.state["status"] = "failed"
            self.save()
            raise RefreshError(
                name,
                type(error).__name__,
                isinstance(error, (DatabaseUnavailable, OSError, RuntimeError)),
            ) from None
        self.state["stages"][name].update(status="complete", result=result)
        self.state["completed_stages"].append(name)
        if name == STAGES[-1]:
            self.state["status"] = "complete"
        self.save()
        return result


def run_refresh(
    config_path, settings_path=DEFAULT_SETTINGS, *, as_of=None, run_id=None
):
    from uuid import uuid4

    plan = make_plan(run_id or str(uuid4()), settings_path, as_of=as_of)
    backend = LiveBackend(plan, _resolve(REPOSITORY_ROOT, config_path))
    with RefreshSession(plan, backend).open() as session:
        for name in STAGES:
            session.step(name)
        return {
            "status": "complete",
            "run_id": plan.run_id,
            "run_directory": plan.run_directory,
            "pack": session.state["stages"]["export_powerbi"]["result"]["pack"],
        }
