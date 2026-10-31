"""User-scoped macOS supervision for the existing local Dagster development stack."""

import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

LABEL = "com.marketatlas.dagster"


def service_document(root, *, node=None, plugin=None, runtime=None):
    root = Path(root).resolve()
    runtime = Path(
        runtime or Path.home() / ".codex/plugin-data/marketatlas/dagster"
    ).resolve()
    node = node or shutil.which("node")
    path = ":".join(
        dict.fromkeys(
            [
                str(root / ".venv-dagster/bin"),
                str(Path(node).parent) if node else "/usr/local/bin",
                "/opt/homebrew/bin",
                "/usr/local/bin",
                "/usr/bin",
                "/bin",
                "/usr/sbin",
                "/sbin",
            ]
        )
    )
    environment = {
        "DAGSTER_HOME": str(root / ".dagster"),
        "PYTHONPATH": str(root / "src"),
        "PATH": path,
    }
    for key in ("MARKETATLAS_CONFIG", "MARKETATLAS_PIPELINE_SETTINGS"):
        if os.environ.get(key):
            environment[key] = os.environ[key]
    if plugin or os.environ.get("MARKETATLAS_DATA_PLUGIN"):
        environment["MARKETATLAS_DATA_PLUGIN"] = str(
            plugin or os.environ["MARKETATLAS_DATA_PLUGIN"]
        )
    environment["MARKETATLAS_REPOSITORY_ROOT"] = str(root)
    return {
        "Label": LABEL,
        "ProgramArguments": [
            node or "/usr/local/bin/node",
            str(runtime / "dagster-supervisor.mjs"),
            str(runtime / "config.json"),
        ],
        "WorkingDirectory": str(runtime),
        "EnvironmentVariables": environment,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "StandardOutPath": str(runtime / "stdout.log"),
        "StandardErrorPath": str(runtime / "stderr.log"),
    }


def listening(port=3001):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def manage_service(action, root, *, home=None):
    if sys.platform != "darwin":
        raise ValueError("Dagster login service currently supports macOS only")
    root = Path(root).resolve()
    path = Path(home or Path.home()) / "Library/LaunchAgents" / f"{LABEL}.plist"
    target = f"gui/{os.getuid()}/{LABEL}"
    runtime = Path(home or Path.home()) / ".codex/plugin-data/marketatlas/dagster"
    if path.exists():
        existing = plistlib.loads(path.read_bytes())
        owner_root = existing.get("EnvironmentVariables", {}).get(
            "MARKETATLAS_REPOSITORY_ROOT"
        ) or existing.get("WorkingDirectory")
        if owner_root != str(root):
            raise ValueError("another checkout owns the Dagster service")
    state = subprocess.run(
        ["launchctl", "print", target], capture_output=True, text=True, check=False
    )
    registered = state.returncode == 0
    if action == "status":
        pid = re.search(r"\bpid = (\d+)", state.stdout)
        return {
            "label": LABEL,
            "registered": registered,
            "running": registered and "state = running" in state.stdout,
            "pid": int(pid.group(1)) if pid else None,
            "ui_listening": listening(),
            "url": "http://127.0.0.1:3001/",
            "logs": str(runtime / "stderr.log"),
        }
    if action == "stop":
        if registered:
            subprocess.run(
                ["launchctl", "bootout", target], check=True, capture_output=True
            )
        path.unlink(missing_ok=True)
        return {"status": "stopped", "label": LABEL}
    if action not in ("start", "restart"):
        raise ValueError("action must be start, status, restart or stop")
    if registered:
        if action == "start":
            return {"status": "already_registered", "label": LABEL}
        subprocess.run(
            ["launchctl", "bootout", target],
            capture_output=True,
            text=True,
            check=False,
        )
        for _ in range(100):
            remaining = subprocess.run(
                ["launchctl", "print", target], capture_output=True, check=False
            )
            if remaining.returncode != 0 and not listening():
                break
            time.sleep(0.2)
        else:
            raise ValueError(
                "Dagster service is still shutting down; retry start after it stops"
            )
    if listening():
        raise ValueError(
            "port 3001 is occupied; stop the identified manual MarketAtlas dev process before service installation"
        )
    if not (root / ".venv-dagster/bin/dagster").is_file():
        raise ValueError("install the pinned Dagster environment first")
    (root / ".dagster").mkdir(exist_ok=True)
    if not (root / ".dagster/dagster.yaml").exists():
        shutil.copyfile(
            root / "orchestration/dagster.yaml", root / ".dagster/dagster.yaml"
        )
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        root / "services/dagster-supervisor.mjs", runtime / "dagster-supervisor.mjs"
    )
    site_packages = next((root / ".venv-dagster/lib").glob("python*/site-packages"))
    environment = service_document(root, runtime=runtime)["EnvironmentVariables"]
    environment["PYTHONPATH"] = str(root / "src") + ":" + str(site_packages)
    environment["VIRTUAL_ENV"] = str(root / ".venv-dagster")
    (runtime / "config.json").write_text(
        json.dumps(
            {
                "python": str((root / ".venv-dagster/bin/python").resolve()),
                "directory": str(runtime),
                "environment": environment,
            },
            indent=2,
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(service_document(root, runtime=runtime)))
    started = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if started.returncode:
        raise ValueError(
            f"launchctl bootstrap failed ({started.returncode}): {started.stderr.strip()}"
        )
    return {
        "status": "started",
        "label": LABEL,
        "restart": "user-login-and-process-exit",
        "url": "http://127.0.0.1:3001/",
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "restart", "stop"))
    args = parser.parse_args()
    try:
        print(
            json.dumps(manage_service(args.action, Path(__file__).resolve().parents[3]))
        )
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(
            f"Dagster service action failed: {error if isinstance(error, ValueError) else type(error).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
