"""MarketAtlas fixture, source-discovery, and adapter command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .adapters.macro_medallion import extract as extract_macro_medallion
from .adapters.macro_medallion import verify_contract as verify_macro_medallion
from .adapters.macro_context import extract as extract_macro_context
from .adapters.macro_context import verify_contract as verify_macro_context
from .analytics.fixture_correlations import (
    calculate_fixture_correlations,
    validate_rolling_correlation_fixture,
)
from .config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    load_macro_medallion,
    load_macro_context,
    load_source_database,
    load_target_database,
    load_upstream_asset,
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
from .graph.macro_economic import build_macro_economic_graph
from .ingestion.macro_medallion import ingest as ingest_macro_medallion
from .migrations import (
    DEFAULT_MIGRATION_DIRECTORY,
    apply_migrations,
    validate_role_boundaries,
)
from .publishing.fixture_build import (
    build_fixture_snapshot,
    validate_fixture_build,
    validate_fixture_reporting,
)
from .publishing.macro_context import (
    ingest_context_extract,
    load_context_extract,
    publish_context_snapshot,
    validate_context_publication,
)
from .report_api import serve_macro_economic_graph
from .source_catalog import build_source_catalog
from .source_contracts import (
    DEFAULT_SOURCE_CONTRACTS_PATH,
    SourceContractError,
    load_source_contract_registry,
    verify_source_contracts,
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


def _catalog_database(config_path: Path, output: Path) -> int:
    try:
        result = build_source_catalog(inspect_source(load_source_database(config_path)))
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "catalog_fingerprint_sha256": result["catalog_fingerprint_sha256"],
                "source_object_count": result["source_object_count"],
                "marketatlas_object_count": result["marketatlas_object_count"],
                "support_counts": result["support_counts"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_source_contracts(catalog_path: Path, contracts_path: Path) -> int:
    """Verify a metadata-only source catalog against tracked contract declarations."""
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise SourceContractError("catalog root must be a JSON object")
        result = verify_source_contracts(
            catalog, load_source_contract_registry(contracts_path)
        )
    except (OSError, json.JSONDecodeError, SourceContractError) as error:
        print(f"cannot verify source contracts: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


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
        result["upstream_asset"] = load_upstream_asset(config_path).public_summary()
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
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
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


def _verify_context_adapter(config_path: Path) -> int:
    try:
        database = load_source_database(config_path)
        gate = verify_source_contracts(build_source_catalog(inspect_source(database)))
        adapter_result = verify_macro_context(database)
    except (ConfigError, DatabaseUnavailable, SourceContractError) as error:
        print(str(error), file=sys.stderr)
        return 1
    result = {
        "status": (
            "valid"
            if gate["status"] == "valid" and adapter_result["status"] == "valid"
            else "invalid"
        ),
        "source_contract_gate": gate,
        "adapter": adapter_result,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _extract_context_adapter(config_path: Path, pilot_path: Path, output: Path) -> int:
    try:
        database = load_source_database(config_path)
        gate = verify_source_contracts(build_source_catalog(inspect_source(database)))
        if gate["status"] != "valid":
            print(json.dumps(gate, sort_keys=True), file=sys.stderr)
            return 1
        result = extract_macro_context(database, load_macro_context(pilot_path))
    except (ConfigError, DatabaseUnavailable, SourceContractError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    result["manifest"]["source_contract_verification"] = {
        "catalog_fingerprint_sha256": gate["catalog_fingerprint_sha256"],
        "registry_version": gate["registry_version"],
        "status": gate["status"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "status": result["manifest"]["status"],
                "series_taxonomy_count": len(result["series_taxonomy"]),
                "release_event_count": len(result["release_events"]),
                "source_coverage_count": len(result["source_coverage"]),
                "input_selection_sha256": result["manifest"]["input_selection_sha256"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


def _ingest_adapter(config_path: Path, pilot_path: Path) -> int:
    """Read an approved source contract, then write only MarketAtlas schemas."""
    try:
        extract = extract_macro_medallion(
            load_source_database(config_path), load_macro_medallion(pilot_path)
        )
        result = ingest_macro_medallion(load_target_database(config_path), extract)
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


def _ingest_context(config_path: Path, input_path: Path) -> int:
    try:
        result = ingest_context_extract(
            load_target_database(config_path), load_context_extract(input_path)
        )
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


def _publish_context(config_path: Path, input_path: Path) -> int:
    try:
        extract = load_context_extract(input_path)
        ingestion = ingest_context_extract(load_target_database(config_path), extract)
        result = publish_context_snapshot(load_target_database(config_path), extract)
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"ingestion": ingestion, "publication": result}, sort_keys=True))
    return 0 if result["status"] != "macro_context_snapshot_failed" else 1


def _validate_context_publication(config_path: Path, input_path: Path) -> int:
    try:
        result = validate_context_publication(
            load_target_database(config_path), load_context_extract(input_path)
        )
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _publish_macro_economic_graph(config_path: Path, input_path: Path) -> int:
    try:
        result = build_macro_economic_graph(
            load_target_database(config_path), load_context_extract(input_path)
        )
    except (ConfigError, DatabaseUnavailable, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    publication = result["publication"]
    print(json.dumps(result, sort_keys=True))
    return 0 if publication["status"] != "macro_economic_graph_failed" else 1


def _serve_macro_economic_graph(config_path: Path, host: str, port: int) -> int:
    try:
        serve_macro_economic_graph(load_target_database(config_path), host, port)
    except (ConfigError, DatabaseUnavailable, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
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


def _build_fixture_snapshot(config_path: Path, knowledge_cutoff: str | None) -> int:
    try:
        result = build_fixture_snapshot(
            load_target_database(config_path), build_fixture(), knowledge_cutoff
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "fixture_snapshot_failed" else 1


def _validate_fixture_build(config_path: Path) -> int:
    try:
        result = validate_fixture_build(
            load_target_database(config_path), build_fixture()
        )
    except (ConfigError, DatabaseUnavailable, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


def _validate_fixture_reporting(config_path: Path) -> int:
    try:
        result = validate_fixture_reporting(
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
    database_catalog = database_commands.add_parser(
        "catalog", help="write a safe metadata-only source support catalog"
    )
    database_catalog.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    database_catalog.add_argument("--output", type=Path, required=True)
    database_verify_contracts = database_commands.add_parser(
        "verify-contracts",
        help="verify a metadata-only catalog against tracked source contracts",
    )
    database_verify_contracts.add_argument("--catalog", type=Path, required=True)
    database_verify_contracts.add_argument(
        "--contracts", type=Path, default=DEFAULT_SOURCE_CONTRACTS_PATH
    )
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
    adapter_context_verify = adapter_commands.add_parser(
        "verify-context", help="verify the bounded macro context adapter"
    )
    adapter_context_verify.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    adapter_extract = adapter_commands.add_parser("extract")
    adapter_extract.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    adapter_extract.add_argument(
        "--pilot-config", type=Path, default=Path("configs/pilot.toml")
    )
    adapter_extract.add_argument("--output", type=Path, required=True)
    adapter_context_extract = adapter_commands.add_parser(
        "extract-context", help="extract bounded macro taxonomy, releases, and coverage"
    )
    adapter_context_extract.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    adapter_context_extract.add_argument(
        "--context-config", type=Path, default=Path("configs/context_pilot.toml")
    )
    adapter_context_extract.add_argument("--output", type=Path, required=True)
    adapter_ingest = adapter_commands.add_parser(
        "ingest", help="ingest the bounded upstream macro extract into atlas"
    )
    adapter_ingest.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    adapter_ingest.add_argument(
        "--pilot-config", type=Path, default=Path("configs/pilot.toml")
    )
    context = commands.add_parser(
        "context", help="load and publish approved macro-source context extracts"
    )
    context_commands = context.add_subparsers(dest="context_command", required=True)
    context_ingest = context_commands.add_parser("ingest")
    context_ingest.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    context_ingest.add_argument("--input", type=Path, required=True)
    context_publish = context_commands.add_parser("publish")
    context_publish.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    context_publish.add_argument("--input", type=Path, required=True)
    context_validate = context_commands.add_parser("validate")
    context_validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    context_validate.add_argument("--input", type=Path, required=True)
    economic_graph = commands.add_parser(
        "economic-graph", help="project and publish the approved live macro knowledge graph"
    )
    economic_graph_commands = economic_graph.add_subparsers(
        dest="economic_graph_command", required=True
    )
    economic_graph_publish = economic_graph_commands.add_parser("publish")
    economic_graph_publish.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    economic_graph_publish.add_argument("--input", type=Path, required=True)
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
    build_run = commands.add_parser("build", help="build or validate serving snapshots")
    build_commands = build_run.add_subparsers(dest="build_command", required=True)
    build_fixture_command = build_commands.add_parser("fixture")
    build_fixture_command.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH
    )
    build_fixture_command.add_argument("--knowledge-cutoff")
    build_validate = build_commands.add_parser("validate-fixture")
    build_validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    report = commands.add_parser(
        "report", help="validate snapshot-pinned report outputs"
    )
    report_commands = report.add_subparsers(dest="report_command", required=True)
    report_validate = report_commands.add_parser("validate-fixture")
    report_validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    report_serve = report_commands.add_parser(
        "serve-macro-economic-graph",
        help="serve only the snapshot-pinned live macro graph on localhost",
    )
    report_serve.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    report_serve.add_argument("--host", default="127.0.0.1")
    report_serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.command == "database":
        if args.database_command == "migrate":
            return _migrate_database(args.config, args.migration_directory)
        if args.database_command == "validate-roles":
            return _validate_database_roles(args.config)
        if args.database_command == "catalog":
            return _catalog_database(args.config, args.output)
        if args.database_command == "verify-contracts":
            return _verify_source_contracts(args.catalog, args.contracts)
        return _inspect_database(args.config, args.output)
    if args.command == "adapter":
        if args.adapter_command == "verify":
            return _verify_adapter(args.config)
        if args.adapter_command == "verify-context":
            return _verify_context_adapter(args.config)
        if args.adapter_command == "extract-context":
            return _extract_context_adapter(
                args.config, args.context_config, args.output
            )
        if args.adapter_command == "ingest":
            return _ingest_adapter(args.config, args.pilot_config)
        return _extract_adapter(args.config, args.pilot_config, args.output)
    if args.command == "context":
        if args.context_command == "ingest":
            return _ingest_context(args.config, args.input)
        if args.context_command == "validate":
            return _validate_context_publication(args.config, args.input)
        return _publish_context(args.config, args.input)
    if args.command == "economic-graph":
        return _publish_macro_economic_graph(args.config, args.input)
    if args.command == "analytics":
        if args.analytics_command == "calculate-fixture":
            return _calculate_fixture_correlations(args.config, args.knowledge_cutoff)
        return _validate_rolling_correlation_fixture(args.config)
    if args.command == "build":
        if args.build_command == "fixture":
            return _build_fixture_snapshot(args.config, args.knowledge_cutoff)
        return _validate_fixture_build(args.config)
    if args.command == "report":
        if args.report_command == "serve-macro-economic-graph":
            return _serve_macro_economic_graph(args.config, args.host, args.port)
        return _validate_fixture_reporting(args.config)
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
