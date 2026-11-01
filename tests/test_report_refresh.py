"""Exercise failure isolation and stable-identity refresh without a plugin dependency."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from market_atlas.orchestration.service import service_document
from market_atlas.reporting.refresh import (
    atomic_write,
    encoded,
    project_lock,
    record_failure,
    refresh_report,
)


def snapshot():
    return {
        "generatedAt": "2026-10-31T00:00:00+00:00",
        "status": "restricted_internal_only",
        "queries": {
            "source_context": {
                "rows": [
                    {"context_kind": "source_coverage", "details_is_stale": True},
                    {"context_kind": "source_coverage", "details_is_stale": None},
                ]
            },
            "new_data": {"rows": [{"value": 2}]},
        },
    }


def project_at(root):
    project = root / "report"
    atomic_write(
        project / "src/data.json",
        encoded(
            {
                "id": "dashboard:stable",
                "title": "Owner title",
                "custom": "retained",
                "queries": {"old": {"rows": [{"value": 1}]}},
            }
        ),
    )
    atomic_write(project / "src/content/user-edit.jsx", b"owner content")
    atomic_write(project / "dist/index.html", b"old html")
    atomic_write(project / "dist/old-data.json", b"old retained data")
    atomic_write(project / "dist/data-app-build.json", b"old manifest")
    plugin = root / "plugin"
    atomic_write(plugin / "scripts/data-app.mjs", b"not executed by test builder")
    pack = root / "pack"
    atomic_write(pack / "manifest.json", encoded({"pack_id": "new-pack"}))
    return project, plugin, pack


def fake_build(project, plugin, node):
    import hashlib

    html = b"new html"
    data = b"new snapshot"
    atomic_write(project / "dist/index.html", html)
    atomic_write(project / "dist/new-data.json", data)
    atomic_write(
        project / "dist/data-app-build.json",
        encoded(
            {
                "kind": "separate-data-v1",
                "html": {
                    "path": "index.html",
                    "sha256": hashlib.sha256(html).hexdigest(),
                    "bytes": len(html),
                },
                "snapshot": {
                    "path": "new-data.json",
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                },
            }
        ),
    )


class ReportRefreshTests(unittest.TestCase):
    def test_validated_replacement_retains_identity_content_and_old_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            project, plugin, pack = project_at(Path(directory).resolve())
            with patch(
                "market_atlas.reporting.refresh.browser_snapshot",
                return_value=snapshot(),
            ):
                result = refresh_report(
                    project,
                    pack,
                    run_id="child",
                    plugin=plugin,
                    node="node",
                    builder=fake_build,
                )
            self.assertEqual(result["app_id"], "dashboard:stable")
            current = json.loads((project / "src/data.json").read_text())
            self.assertEqual(current["title"], "Owner title")
            self.assertEqual(current["custom"], "retained")
            self.assertEqual(
                (project / "src/content/user-edit.jsx").read_bytes(), b"owner content"
            )
            self.assertEqual((project / "dist/index.html").read_bytes(), b"new html")
            self.assertEqual(
                (project / "dist/old-data.json").read_bytes(), b"old retained data"
            )
            self.assertEqual(
                current["queries"]["refresh_status"]["rows"][0][
                    "unknown_coverage_records"
                ],
                1,
            )
            record_failure(
                project,
                run_id="failed-run",
                stage="source_gate",
                error_type="ValueError",
            )
            status = json.loads((project / "dist/refresh-status.json").read_text())
            self.assertEqual(status["last_success"]["run_id"], "child")
            self.assertEqual(status["last_attempt"]["status"], "failed")
            self.assertEqual((project / "dist/index.html").read_bytes(), b"new html")

    def test_build_corruption_and_commit_failure_preserve_previous_report(self):
        for failure in ("build", "checksum", "commit"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as directory,
            ):
                project, plugin, pack = project_at(Path(directory).resolve())
                atomic_write(
                    project / "src/content/dashboard/DashboardContent.jsx",
                    b"prior authored content",
                )
                before = {
                    path: (project / path).read_bytes()
                    for path in [
                        "src/data.json",
                        "dist/index.html",
                        "dist/data-app-build.json",
                        "src/content/dashboard/DashboardContent.jsx",
                    ]
                }

                def build(candidate, plugin, node, failure=failure):
                    if failure == "build":
                        raise RuntimeError("controlled failure")
                    fake_build(candidate, plugin, node)
                    if failure == "checksum":
                        (candidate / "dist/new-data.json").write_bytes(b"corrupt")

                def write(path, payload, failure=failure, project=project):
                    if failure == "commit" and path == project / "dist/index.html":
                        raise OSError("controlled atomic commit failure")
                    atomic_write(path, payload)

                with (
                    patch(
                        "market_atlas.reporting.refresh.browser_snapshot",
                        return_value=snapshot(),
                    ),
                    patch(
                        "market_atlas.reporting.refresh.atomic_write", side_effect=write
                    ),
                    self.assertRaises((RuntimeError, ValueError, OSError)),
                ):
                    refresh_report(
                        project,
                        pack,
                        run_id="failed-run",
                        plugin=plugin,
                        node="node",
                        builder=build,
                        update_content=True,
                    )
                for path, expected in before.items():
                    self.assertEqual((project / path).read_bytes(), expected)
                self.assertFalse((project / "dist/refresh-status.json").exists())
                self.assertFalse(
                    (project / "src/content/dashboard/MacroAnalytics.jsx").exists()
                )

    def test_normal_refresh_retains_independent_research_pack_and_cutoff(self):
        with tempfile.TemporaryDirectory() as directory:
            project, plugin, pack = project_at(Path(directory).resolve())
            old = json.loads((project / "src/data.json").read_text())
            research = {
                "rows": [
                    {
                        "group_id": "treasury_yields",
                        "pack_id": "research-pack",
                        "as_of": "2024-06-30",
                    }
                ]
            }
            old["queries"]["macro_analytics_groups"] = research
            atomic_write(project / "src/data.json", encoded(old))
            with patch(
                "market_atlas.reporting.refresh.browser_snapshot",
                return_value=snapshot(),
            ):
                refresh_report(
                    project,
                    pack,
                    run_id="next-daily",
                    plugin=plugin,
                    node="node",
                    builder=fake_build,
                )
            current = json.loads((project / "src/data.json").read_text())
            self.assertEqual(research, current["queries"]["macro_analytics_groups"])
            status = current["queries"]["refresh_status"]["rows"][0]
            self.assertEqual("research-pack", status["analytics_pack_id"])
            self.assertEqual("2024-06-30", status["analytics_as_of"])

    def test_explicit_content_install_keeps_owner_files_and_authoring_state(self):
        with tempfile.TemporaryDirectory() as directory:
            project, plugin, pack = project_at(Path(directory).resolve())
            with patch(
                "market_atlas.reporting.refresh.browser_snapshot",
                return_value=snapshot(),
            ):
                refresh_report(
                    project,
                    pack,
                    run_id="preview",
                    plugin=plugin,
                    node="node",
                    builder=fake_build,
                    update_content=True,
                    build_status="updating",
                )
            current = json.loads((project / "src/data.json").read_text())
            self.assertEqual("updating", current["buildStatus"])
            self.assertEqual(
                b"owner content", (project / "src/content/user-edit.jsx").read_bytes()
            )
            self.assertIn(
                "MacroAnalytics",
                (project / "src/content/dashboard/DashboardContent.jsx").read_text(),
            )
            self.assertTrue(
                (project / "src/content/dashboard/macroAnalytics.mjs").exists()
            )

    def test_overlapping_report_refreshes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            project, plugin, pack = project_at(Path(directory).resolve())
            with (
                project_lock(project),
                self.assertRaisesRegex(ValueError, "already running"),
            ):
                refresh_report(
                    project,
                    pack,
                    run_id="overlap",
                    plugin=plugin,
                    node="node",
                    builder=fake_build,
                )

    def test_service_is_loopback_only_supervised_and_does_not_copy_secret_environment(
        self,
    ):
        with patch.dict(
            "os.environ", {"PRIVATE_TEST_PASSWORD": "never-copy-me"}, clear=False
        ):
            document = service_document(
                "/tmp/example marketatlas", node="/usr/local/bin/node"
            )
        self.assertTrue(document["RunAtLoad"])
        self.assertTrue(document["KeepAlive"])
        self.assertEqual(
            document["EnvironmentVariables"]["DAGSTER_HOME"],
            "/private/tmp/example marketatlas/.dagster"
            if Path("/tmp").resolve() == Path("/private/tmp")
            else "/tmp/example marketatlas/.dagster",
        )
        self.assertEqual(
            document["EnvironmentVariables"]["MARKETATLAS_REPOSITORY_ROOT"],
            str(Path("/tmp/example marketatlas").resolve()),
        )
        self.assertNotIn("PRIVATE_TEST_PASSWORD", document["EnvironmentVariables"])
