"""Fixture-only command line interface. No upstream or database access."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .contracts import available_view, canonical_bytes, validate_fixture
from .fixtures import build_fixture


def _build(output: Path) -> int:
    fixture = build_fixture()
    errors = validate_fixture(fixture)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    output.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(fixture)
    fixture_path = output / "fixture.json"
    fixture_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {
        "synthetic": True, "fixture_version": fixture["metadata"]["fixture_version"],
        "fixture_file": fixture_path.name, "sha256": digest,
        "record_counts": {key: len(fixture[key]) for key in ("sessions", "entities", "identifiers", "assertions", "market_observations", "macro_observations", "configured_pairs")},
        "status": "fixture_contract_validated; graph_and_report_not_built",
    }
    (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    print(json.dumps({"output": str(output), **manifest}, sort_keys=True))
    return 0


def _validate(directory: Path) -> int:
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        payload = (directory / "fixture.json").read_bytes()
        fixture = json.loads(payload)
    except (OSError, json.JSONDecodeError) as error:
        print(f"cannot load fixture: {error}", file=sys.stderr)
        return 1
    errors = validate_fixture(fixture)
    if hashlib.sha256(payload).hexdigest() != manifest.get("sha256"):
        errors.append("fixture SHA-256 differs from manifest")
    if payload != canonical_bytes(fixture):
        errors.append("fixture is not in canonical JSON format")
    if manifest.get("synthetic") is not True:
        errors.append("manifest must be labeled synthetic")
    expected_counts = {key: len(fixture[key]) for key in ("sessions", "entities", "identifiers", "assertions", "market_observations", "macro_observations", "configured_pairs")}
    if manifest.get("record_counts") != expected_counts:
        errors.append("manifest record counts differ from fixture")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(json.dumps({"status": "valid", "sha256": manifest["sha256"], "synthetic": True}, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="market-atlas")
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixture", help="generate or validate synthetic inputs")
    fixture_commands = fixture.add_subparsers(dest="fixture_command", required=True)
    build = fixture_commands.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    validate = fixture_commands.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    inspect = fixture_commands.add_parser("inspect")
    inspect.add_argument("--knowledge-cutoff", required=True, help="UTC timestamp ending in Z")
    args = parser.parse_args(argv)
    if args.fixture_command == "build":
        return _build(args.output)
    if args.fixture_command == "validate":
        return _validate(args.input)
    try:
        print(json.dumps(available_view(build_fixture(), args.knowledge_cutoff), sort_keys=True))
    except ValueError as error:
        print(f"invalid cutoff: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
