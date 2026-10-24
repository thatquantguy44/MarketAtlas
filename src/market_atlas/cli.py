"""MarketAtlas fixture, source-discovery, and adapter command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .adapters.macro_medallion import extract as extract_macro_medallion
from .adapters.macro_medallion import verify_contract as verify_macro_medallion
from .analytics.fixture_correlations import (
    calculate_fixture_correlations,
    validate_rolling_correlation_fixture,
)
from .config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    load_macro_medallion,
    load_source_database,
    load_target_database,
)
from .contracts import available_view, canonical_bytes, validate_fixture
from .database import DatabaseUnavailable, inspect_source
from .fixtures import build_fixture
from .graph.fixture_loader import (
    load_fixture,
    validate_curated_context_fixture,
    validate_fixture_graph,
    validate_observation_fixture,
    validate_temporal_fixture,
)
from .migrations import (
    DEFAULT_MIGRATION_DIRECTORY,
    apply_migrations,
    validate_role_boundaries,
)


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
        "synthetic": True,
        "fixture_version": fixture["metadata"]["fixture_version"],
        "fixture_file": fixture_path.name,
        "sha256": digest,
        "record_counts": {
            key: len(fixture[key])
            for key in (
                "sessions",
                "entities",
                "identifiers",
                "assertions",
                "market_observations",
                "macro_observations",
                "curated_contexts",
                "configured_pairs",
            )
        },
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
    expected_counts = {
        key: len(fixture[key])
        for key in (
            "sessions",
            "entities",
            "identifiers",
            "assertions",
            "market_observations",
            "macro_observations",
            "curated_contexts",
            "configured_pairs",
        )
    }
    if manifest.get("record_counts") != expected_counts:
        errors.append("manifest record counts differ from fixture")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(
        json.dumps(
            {"status": "valid", "sha256": manifest["sha256"], "synthetic": True},
            sort_keys=True,
        )
    )
    return 0


def _inspect_database(config_path: Path, output: Path | None) -> int:
    try:
        config = load_source_database(config_path)
        result = inspect_source(config)
    except (ConfigError, DatabaseUnavailable) as error:
        print(str(error), file=sys.stderr)
        return 1
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_bytes(result))
    summary = {
        "status": result["status"],
        "database": result["server"]["database"],
        "database_user": result["server"]["database_user"],
        "server_version": result["server"]["server_version"],
        "transaction_read_only": result["server"]["transaction_read_only"],
        "schema_count": len(result["schemas"]),
        "object_count": len(result["objects"]),
        "column_count": len(result["columns"]),
        "output": str(output) if output is not None else None,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def _migrate_database(config_path: Path, migration_directory: Path) -> int:
    try:
        result = apply_migrations(
            load_target_database(config_path), directory=migration_directory
        )
    except (ConfigError, DatabaseUnavailable) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


def _validate_database_roles(config_path: Path) -> int:
    try:
        result = validate_role_boundaries(load_target_database(config_path))
    except (ConfigError, DatabaseUnavailable) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _verify_adapter(config_path: Path) -> int:
    try:
        result = verify_macro_medallion(load_source_database(config_path))
    except (ConfigError, DatabaseUnavailable) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _extract_adapter(config_path: Path, pilot_path: Path, output: Path) -> int:
    try:
        result = extract_macro_medallion(
            load_source_database(config_path), load_macro_medallion(pilot_path)
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "status": result["manifest"]["status"],
                "entity_count": len(result["entities"]),
                "macro_observation_count": len(result["macro_observations"]),
                "input_selection_sha256": result["manifest"]["input_selection_sha256"],
                "source_rows_sha256": result["manifest"]["source_rows_sha256"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


def _load_fixture_graph(config_path: Path) -> int:
    try:
        result = load_fixture(load_target_database(config_path), build_fixture())
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


def _validate_fixture_graph(config_path: Path) -> int:
    try:
        result = validate_fixture_graph(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _validate_temporal_fixture(config_path: Path) -> int:
    try:
        result = validate_temporal_fixture(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _validate_observation_fixture(config_path: Path) -> int:
    try:
        result = validate_observation_fixture(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _validate_curated_context_fixture(config_path: Path) -> int:
    try:
        result = validate_curated_context_fixture(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _calculate_fixture_correlations(
    config_path: Path, knowledge_cutoff: str | None
) -> int:
    try:
        result = calculate_fixture_correlations(
            load_target_database(config_path), build_fixture(), knowledge_cutoff
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


def _validate_rolling_correlation_fixture(config_path: Path) -> int:
    try:
        result = validate_rolling_correlation_fixture(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="market-atlas")
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser(
        "fixture", help="generate or validate synthetic inputs"
    )
    fixture_commands = fixture.add_subparsers(dest="fixture_command", required=True)
    build = fixture_commands.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    validate = fixture_commands.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    inspect = fixture_commands.add_parser("inspect")
    inspect.add_argument(
        "--knowledge-cutoff", required=True, help="UTC timestamp ending in Z"
    )
    database = commands.add_parser(
        "database", help="inspect a PostgreSQL source safely"
    )
    database_commands = database.add_subparsers(dest="database_command", required=True)
    database_inspect = database_commands.add_parser("inspect")
    database_inspect.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    database_inspect.add_argument("--output", type=Path)
    database_migrate = database_commands.add_parser("migrate")
    database_migrate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    database_migrate.add_argument(
        "--migration-directory", type=Path, default=DEFAULT_MIGRATION_DIRECTORY
    )
    database_roles = database_commands.add_parser("validate-roles")
    database_roles.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    adapter = commands.add_parser(
        "adapter", help="verify or extract an upstream adapter"
    )
    adapter_commands = adapter.add_subparsers(dest="adapter_command", required=True)
    adapter_verify = adapter_commands.add_parser("verify")
    adapter_verify.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    adapter_extract = adapter_commands.add_parser("extract")
    adapter_extract.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    adapter_extract.add_argument(
        "--pilot-config", type=Path, default=Path("configs/pilot.toml")
    )
    adapter_extract.add_argument("--output", type=Path, required=True)
    graph = commands.add_parser("graph", help="load or validate graph identities")
    graph_commands = graph.add_subparsers(dest="graph_command", required=True)
    graph_load = graph_commands.add_parser("load-fixture")
    graph_load.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    graph_validate = graph_commands.add_parser("validate-fixture")
    graph_validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    graph_validate_temporal = graph_commands.add_parser("validate-temporal-fixture")
    graph_validate_temporal.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    graph_validate_observation = graph_commands.add_parser(
        "validate-observation-fixture"
    )
    graph_validate_observation.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    graph_validate_context = graph_commands.add_parser(
        "validate-curated-context-fixture"
    )
    graph_validate_context.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    analytics = commands.add_parser(
        "analytics", help="calculate or validate bounded fixture estimates"
    )
    analytics_commands = analytics.add_subparsers(
        dest="analytics_command", required=True
    )
    analytics_calculate = analytics_commands.add_parser("calculate-fixture")
    analytics_calculate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    analytics_calculate.add_argument("--knowledge-cutoff")
    analytics_validate = analytics_commands.add_parser("validate-fixture")
    analytics_validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    if args.command == "database":
        if args.database_command == "migrate":
            return _migrate_database(args.config, args.migration_directory)
        if args.database_command == "validate-roles":
            return _validate_database_roles(args.config)
        return _inspect_database(args.config, args.output)
    if args.command == "adapter":
        if args.adapter_command == "verify":
            return _verify_adapter(args.config)
        return _extract_adapter(args.config, args.pilot_config, args.output)
    if args.command == "analytics":
        if args.analytics_command == "calculate-fixture":
            return _calculate_fixture_correlations(args.config, args.knowledge_cutoff)
        return _validate_rolling_correlation_fixture(args.config)
    if args.command == "graph":
        if args.graph_command == "load-fixture":
            return _load_fixture_graph(args.config)
        if args.graph_command == "validate-temporal-fixture":
            return _validate_temporal_fixture(args.config)
        if args.graph_command == "validate-observation-fixture":
            return _validate_observation_fixture(args.config)
        if args.graph_command == "validate-curated-context-fixture":
            return _validate_curated_context_fixture(args.config)
        return _validate_fixture_graph(args.config)
    if args.fixture_command == "build":
        return _build(args.output)
    if args.fixture_command == "validate":
        return _validate(args.input)
    try:
        print(
            json.dumps(
                available_view(build_fixture(), args.knowledge_cutoff), sort_keys=True
            )
        )
    except ValueError as error:
        print(f"invalid cutoff: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
