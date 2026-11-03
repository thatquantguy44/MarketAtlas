"""Strict UTF-8 JSON/CSV codecs; input pack loading never evaluates rules."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from market_atlas.contracts import canonical_bytes, sha256
from market_atlas.securities_finance.catalog import ReferenceCatalog
from market_atlas.securities_finance.contracts import (
    ContractError,
    TimestampEvidence,
    _require,
    _scaled_quantity,
    _text,
)
from market_atlas.securities_finance.records import (
    SCHEMAS,
    Scalar,
    SourceRecord,
    columns,
    normalize_tables,
)

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TABLE_ROWS = 10000
NULL_TOKEN = "\\N"


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_json_key", "JSON object key repeated")
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise ContractError(
        "invalid_numeric_literal",
        "decimal and nonfinite values require typed decimal text",
    )


def _json(data: bytes) -> object:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except ContractError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ContractError("invalid_json", "invalid UTF-8 JSON") from error


def _check_row(record_type: str, row: object) -> dict[str, Scalar]:
    _require(isinstance(row, dict), "invalid_row", "record must be an object")
    _require(
        set(row) == set(columns(record_type)),
        "invalid_columns",
        "missing or unknown record columns",
    )
    _require(
        all(value is None or type(value) in (str, bool, int) for value in row.values()),
        "invalid_field_type",
        "only flat scalar fields are supported",
    )
    _require(
        NULL_TOKEN not in row.values(),
        "reserved_null_literal",
        "literal null token is unsupported",
    )
    for name, value in row.items():
        kind = SCHEMAS[record_type].fields.get(name, "text").rstrip("?")
        expected = bool if kind == "bool" else int if kind == "int" else str
        _require(
            value is None or type(value) is expected,
            "invalid_field_type",
            "scalar type differs from its declared column",
            name,
        )
    return dict(row)


def decode_table(
    record_type: str, data: bytes, format: str
) -> tuple[dict[str, Scalar], ...]:
    """Decode physical records, retaining scalar types; normalization is separate."""
    expected = columns(record_type)
    _require(
        isinstance(data, bytes) and len(data) <= MAX_FILE_BYTES,
        "file_too_large",
        "source file limit exceeded",
    )
    if format == "json":
        rows = _json(data)
        _require(isinstance(rows, list), "invalid_table", "JSON table must be an array")
        _require(
            len(rows) <= MAX_TABLE_ROWS, "too_many_rows", "table row limit exceeded"
        )
        return tuple(_check_row(record_type, row) for row in rows)
    _require(format == "csv", "unsupported_format", "JSON or CSV required")
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8"), newline=""), strict=True)
        header = next(reader, None)
        _require(
            header is not None
            and len(header) == len(set(header))
            and set(header) == set(expected),
            "invalid_columns",
            "CSV header must contain each declared column once",
        )
        boolean_fields = {
            name
            for name, kind in SCHEMAS[record_type].fields.items()
            if kind.rstrip("?") == "bool"
        }
        integer_fields = {
            name
            for name, kind in SCHEMAS[record_type].fields.items()
            if kind.rstrip("?") == "int"
        }
        result = []
        for values in reader:
            _require(
                len(result) < MAX_TABLE_ROWS,
                "too_many_rows",
                "table row limit exceeded",
            )
            _require(
                len(values) == len(header),
                "invalid_columns",
                "ragged or blank CSV record",
            )
            row: dict[str, Scalar] = {}
            for name, value in zip(header, values, strict=True):
                if value == NULL_TOKEN:
                    row[name] = None
                elif name in boolean_fields:
                    _require(
                        value in ("true", "false"),
                        "invalid_boolean",
                        "lowercase true/false required",
                    )
                    row[name] = value == "true"
                elif name in integer_fields:
                    _require(
                        len(value) <= 18
                        and re.fullmatch(r"0|[1-9][0-9]*", value) is not None,
                        "invalid_integer",
                        "nonnegative integer text required",
                    )
                    row[name] = int(value)
                else:
                    row[name] = value
            result.append(_check_row(record_type, row))
        return tuple(result)
    except (UnicodeError, csv.Error) as error:
        raise ContractError("invalid_csv", "invalid UTF-8 CSV") from error


def encode_table(
    record_type: str, rows: Iterable[Mapping[str, Scalar]], format: str
) -> bytes:
    values = []
    for row in rows:
        _require(
            len(values) < MAX_TABLE_ROWS, "too_many_rows", "table row limit exceeded"
        )
        values.append(_check_row(record_type, dict(row)))
    if format == "json":
        result = canonical_bytes(values)
    else:
        _require(format == "csv", "unsupported_format", "JSON or CSV required")
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        names = columns(record_type)
        writer.writerow(names)
        for row in values:
            writer.writerow(
                NULL_TOKEN
                if row[name] is None
                else str(row[name]).lower()
                if type(row[name]) is bool
                else row[name]
                for name in names
            )
        result = stream.getvalue().encode("utf-8")
    _require(
        len(result) <= MAX_FILE_BYTES, "file_too_large", "source file limit exceeded"
    )
    return result


def _keys(value: object, required: str, optional: str = "") -> dict:
    _require(isinstance(value, dict), "invalid_fields", "object/table required")
    required_keys, allowed = (
        set(required.split()),
        set((required + " " + optional).split()),
    )
    _require(
        required_keys <= set(value) <= allowed,
        "invalid_fields",
        "missing or unknown metadata fields",
    )
    return value


def _integer(value: object, maximum: int, *, minimum: int = 0) -> None:
    _require(
        type(value) is int and minimum <= value <= maximum,
        "invalid_integer",
        "unsupported integer bound",
    )


def load_settings(data: bytes) -> dict:
    """Validate v1 settings policy; catalog consistency is checked on pack load."""
    _require(
        len(data) <= MAX_FILE_BYTES, "file_too_large", "settings file limit exceeded"
    )
    try:
        settings = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError, RecursionError) as error:
        raise ContractError("invalid_settings", "invalid UTF-8 TOML") from error
    _keys(
        settings,
        "schema_version classification default_profile inputs time freshness quantity rules solver bounds earnings profiles",
    )
    _require(
        type(settings["schema_version"]) is int and settings["schema_version"] == 1,
        "unsupported_schema_version",
        "schema version 1 required",
    )
    _require(
        settings["classification"] == "synthetic",
        "invalid_classification",
        "synthetic inputs required",
    )
    inputs = _keys(
        settings["inputs"],
        "record_formats manifest_format settings_format source_shape authoritative_representation snapshot_event_boundary csv",
    )
    _require(
        inputs["record_formats"] in (["json", "csv"], ["csv", "json"])
        and inputs["manifest_format"] == "json"
        and inputs["settings_format"] == "toml"
        and inputs["source_shape"] == "versioned_snapshots_plus_selected_events"
        and inputs["authoritative_representation"] == "one_per_logical_dataset"
        and inputs["snapshot_event_boundary"] == "explicit_event_version_ids",
        "unsupported_input_policy",
        "unsupported encoding/source-shape policy",
    )
    dialect = _keys(
        inputs["csv"], "encoding delimiter quotechar null_token header_required"
    )
    _require(
        dialect
        == {
            "encoding": "utf-8",
            "delimiter": ",",
            "quotechar": '"',
            "null_token": NULL_TOKEN,
            "header_required": True,
        },
        "unsupported_csv_dialect",
        "version-1 CSV dialect required",
    )
    _require(
        type(dialect["header_required"]) is bool,
        "invalid_boolean",
        "boolean header policy required",
    )
    time = _keys(
        settings["time"],
        "business_as_of knowledge_cutoff system_cutoff date_only_policy ambiguous_consequential_fifo known_equal_timestamp_tie_break",
    )
    for name in ("business_as_of", "knowledge_cutoff", "system_cutoff"):
        TimestampEvidence(time[name], "instant")
    _require(
        (
            time["date_only_policy"],
            time["ambiguous_consequential_fifo"],
            time["known_equal_timestamp_tie_break"],
        )
        == (
            "preserve_interval_withhold_ambiguous_claims",
            "withhold_preserve_prior_pack",
            "request_id",
        ),
        "unsupported_time_policy",
        "version-1 uncertainty policy required",
    )
    freshness = _keys(
        settings["freshness"],
        "reference_clock evidence_field max_age_inclusive inventory_max_age_seconds request_max_age_seconds agreement_status_max_age_seconds",
    )
    _require(
        freshness["reference_clock"] == "knowledge_cutoff"
        and freshness["evidence_field"] == "source_confirmed_at"
        and freshness["max_age_inclusive"] is True,
        "unsupported_freshness_policy",
        "declared evidence-clock policy required",
    )
    for name in (
        "inventory_max_age_seconds",
        "request_max_age_seconds",
        "agreement_status_max_age_seconds",
    ):
        _integer(freshness[name], 1000000000)
    quantity = _keys(settings["quantity"], "equity fixed_income")
    _keys(
        quantity["equity"],
        "convention_id quantity_unit quantity_precision minimum_allocation allocation_increment increment_origin minimum_scope",
    )
    _require(
        isinstance(quantity["fixed_income"], list),
        "invalid_fields",
        "bond conventions must be an array",
    )
    for row in quantity["fixed_income"]:
        _keys(
            row,
            "source_instrument_id convention_id quantity_unit quantity_currency quantity_precision minimum_allocation allocation_increment increment_origin minimum_scope",
        )
        _text(row["source_instrument_id"], "source_instrument_id")
    rules = _keys(settings["rules"], "version required_checks")
    _text(rules["version"], "rules.version")
    required = [
        "agreement_active",
        "party_account_permission",
        "instrument_compatible",
        "location_compatible",
        "settlement_ready",
        "source_fresh",
    ]
    _require(
        isinstance(rules["required_checks"], list)
        and len(rules["required_checks"]) == len(required)
        and all(item in rules["required_checks"] for item in required),
        "unsupported_rule_vocabulary",
        "all core typed checks required",
    )
    solver = _keys(
        settings["solver"],
        "adapter dependency_extra total_time_limit_seconds mip_rel_gap presolve near_integer_abs_tolerance continuous_objective_abs_tolerance max_scaled_integer_magnitude require_all_stages_proven publication_policy",
    )
    _require(
        solver["adapter"] == "scipy_highs_milp"
        and solver["dependency_extra"] == "optimization"
        and solver["require_all_stages_proven"] is True
        and solver["publication_policy"] == "proven_validated_only",
        "unsupported_solver_policy",
        "selected adapter/proof policy required",
    )
    _integer(solver["total_time_limit_seconds"], 86400, minimum=1)
    _integer(solver["max_scaled_integer_magnitude"], 2**53 - 1, minimum=1)
    _require(
        _scaled_quantity(solver["mip_rel_gap"], 18, "mip_rel_gap") == 0,
        "unsupported_solver_policy",
        "zero requested relative gap required",
    )
    _require(
        type(solver["presolve"]) is bool, "invalid_boolean", "boolean presolve required"
    )
    for name in ("near_integer_abs_tolerance", "continuous_objective_abs_tolerance"):
        _require(
            0 < _scaled_quantity(solver[name], 18, name) <= 10**15,
            "invalid_tolerance",
            "positive tolerance no greater than 0.001 required",
        )
    bounds = _keys(
        settings["bounds"],
        "max_positions max_requests max_loans max_events max_explanation_hops max_explanation_rows",
    )
    for name, limit in {
        "max_positions": 100,
        "max_requests": 20,
        "max_loans": 20,
        "max_events": 100,
        "max_explanation_hops": 6,
        "max_explanation_rows": 200,
    }.items():
        _integer(bounds[name], limit, minimum=1)
    earnings = _keys(
        settings["earnings"],
        "input_method currency horizon_id horizon_start horizon_end objective_currency_precision missing_coefficient_policy",
    )
    _require(
        earnings["input_method"] == "supplied_net_benefit"
        and earnings["missing_coefficient_policy"] == "fail_requested_profile"
        and type(earnings["objective_currency_precision"]) is int
        and earnings["objective_currency_precision"] == 6,
        "unsupported_earnings_method",
        "supplied micro-currency coefficients required",
    )
    _require(
        isinstance(earnings["currency"], str)
        and re.fullmatch(r"[A-Z]{3}", earnings["currency"]) is not None,
        "invalid_currency",
        "explicit objective currency required",
    )
    _text(earnings["horizon_id"], "horizon_id")
    _require(
        TimestampEvidence(earnings["horizon_start"], "instant").as_utc()
        < TimestampEvidence(earnings["horizon_end"], "instant").as_utc(),
        "invalid_horizon",
        "positive horizon required",
    )
    _require(
        isinstance(settings["profiles"], dict)
        and isinstance(settings["default_profile"], str)
        and settings["default_profile"] in settings["profiles"],
        "unknown_profile",
        "default profile is not declared",
    )
    terms = {
        "total_shortfall",
        "fifo_shortfall",
        "canonical_allocation",
        "priority_tier_shortfall",
        "worst_shortfall_fraction",
        "negative_net_benefit",
        "weighted_score",
    }
    for profile in settings["profiles"].values():
        _keys(
            profile,
            "policy_id ordered_terms",
            "tier_order population empty_population_metric weighted_terms",
        )
        _text(profile["policy_id"], "policy_id")
        stages = profile["ordered_terms"]
        _require(
            isinstance(stages, list)
            and bool(stages)
            and all(isinstance(term, str) and term in terms for term in stages)
            and len(stages) == len(set(stages))
            and stages[-1] == "canonical_allocation",
            "unsupported_objective_terms",
            "declared terms with canonical ties last required",
        )
        if "priority_tier_shortfall" in stages:
            tiers = profile.get("tier_order")
            _require(
                isinstance(tiers, list) and bool(tiers),
                "invalid_priority_tiers",
                "explicit tiers required",
            )
            for tier in tiers:
                _integer(tier, 1000000000)
            _require(
                len(tiers) == len(set(tiers)),
                "invalid_priority_tiers",
                "tiers must be unique",
            )
        else:
            _require(
                "tier_order" not in profile,
                "unused_policy_parameter",
                "tier order without priority stage",
            )
        if "worst_shortfall_fraction" in stages:
            _require(
                profile.get("population")
                == "positive_demand_with_provably_usable_eligible_supply"
                and profile.get("empty_population_metric") == "unavailable",
                "unsupported_balance_policy",
                "selected request-balance semantics required",
            )
        else:
            _require(
                "population" not in profile
                and "empty_population_metric" not in profile,
                "unused_policy_parameter",
                "balance parameters without balance stage",
            )
        if "weighted_score" in stages:
            components = profile.get("weighted_terms")
            _require(
                isinstance(components, list) and bool(components),
                "invalid_weights",
                "weighted components required",
            )
            weights = []
            seen = set()
            for term in components:
                _keys(
                    term, "term weight", "scale scale_amount scale_currency horizon_id"
                )
                _require(
                    term["term"] in ("total_shortfall", "negative_net_benefit")
                    and term["term"] not in seen,
                    "unsupported_objective_terms",
                    "distinct supported weighted components required",
                )
                seen.add(term["term"])
                weights.append(_scaled_quantity(term["weight"], 18, "weight"))
                if term["term"] == "total_shortfall":
                    _require(
                        set(term) == {"term", "weight", "scale"}
                        and term["scale"] == "group_total_positive_open_demand",
                        "invalid_scale",
                        "declared positive-demand scale required",
                    )
                else:
                    _require(
                        set(term)
                        == {
                            "term",
                            "weight",
                            "scale_amount",
                            "scale_currency",
                            "horizon_id",
                        }
                        and term["scale_currency"] == earnings["currency"]
                        and term["horizon_id"] == earnings["horizon_id"]
                        and _scaled_quantity(term["scale_amount"], 6, "scale_amount")
                        > 0,
                        "invalid_scale",
                        "matching monetary scale/currency/horizon required",
                    )
            _require(
                sum(weights) > 0,
                "invalid_weights",
                "at least one positive weight required",
            )
        else:
            _require(
                "weighted_terms" not in profile,
                "unused_policy_parameter",
                "weights without weighted stage",
            )
    return settings


def validate_settings_catalog(settings: Mapping, catalog: ReferenceCatalog) -> None:
    expected = []
    equity = settings["quantity"]["equity"]
    for instrument in catalog.instruments:
        if instrument.asset_class == "equity":
            source_id = instrument.canonical_key.removeprefix("fixture:")
            expected.append(
                {
                    **equity,
                    "convention_id": f"{equity['convention_id']}:{source_id}",
                    "instrument_node_id": instrument.instrument_node_id,
                    "quantity_currency": None,
                }
            )
    for row in settings["quantity"]["fixed_income"]:
        references = [
            item
            for item in catalog.instruments
            if item.canonical_key == f"fixture:{row['source_instrument_id']}"
            and item.asset_class == "fixed_income"
        ]
        _require(
            len(references) == 1,
            "unknown_instrument",
            "settings bond reference is absent/ambiguous",
        )
        expected.append(
            {
                key: value
                for key, value in {
                    **row,
                    "instrument_node_id": references[0].instrument_node_id,
                }.items()
                if key != "source_instrument_id"
            }
        )
    _require(
        len(expected) == len(catalog.conventions)
        and len({row["convention_id"] for row in expected}) == len(expected),
        "settings_catalog_mismatch",
        "convention population differs from settings",
    )
    for row in expected:
        from market_atlas.securities_finance.contracts import QuantityConvention

        _require(
            catalog.convention(row["convention_id"])
            == QuantityConvention.from_mapping(row),
            "settings_catalog_mismatch",
            "catalog convention differs from settings",
        )


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class SourceLocation:
    logical_dataset_id: str
    record_type: str
    source_name: str
    path: str
    format: str
    sha256: str
    record_number: int  # Logical record ordinal, not a physical CSV line number.


@dataclass(frozen=True)
class InputPack:
    manifest_id: str
    semantic_identity: str
    manifest: Mapping
    settings: Mapping
    tables: Mapping[str, tuple[SourceRecord, ...]]
    catalog: ReferenceCatalog
    provenance: tuple[SourceLocation, ...]


def _file(root: Path, entry: object) -> tuple[bytes, str]:
    data = _keys(entry, "path sha256", "format")
    path, digest = data["path"], data["sha256"]
    _require(
        isinstance(path, str)
        and bool(path)
        and "\\" not in path
        and ":" not in path
        and not PurePosixPath(path).is_absolute()
        and ".." not in PurePosixPath(path).parts
        and str(PurePosixPath(path)) == path,
        "invalid_path",
        "relative input path required",
    )
    target = (root / path).resolve()
    _require(target.is_relative_to(root), "invalid_path", "input path escapes pack")
    _require(
        target.is_file(), "missing_input_file", "declared input is not a regular file"
    )
    _require(
        isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
        "invalid_hash",
        "SHA-256 text required",
    )
    with target.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    _require(len(raw) <= MAX_FILE_BYTES, "file_too_large", "source file limit exceeded")
    _require(
        hashlib.sha256(raw).hexdigest() == digest,
        "hash_mismatch",
        "input bytes differ from manifest",
    )
    return raw, path


def read_input_pack(directory: str | Path) -> InputPack:
    """Verify both representations, return one authoritative set of records."""
    root = Path(directory).resolve()
    manifest_path = (root / "manifest.json").resolve()
    _require(
        manifest_path.is_relative_to(root), "invalid_path", "manifest escapes pack"
    )
    _require(manifest_path.is_file(), "missing_input_file", "input manifest is absent")
    with manifest_path.open("rb") as stream:
        manifest_bytes = stream.read(MAX_FILE_BYTES + 1)
    _require(
        len(manifest_bytes) <= MAX_FILE_BYTES,
        "file_too_large",
        "manifest limit exceeded",
    )
    manifest = _keys(
        _json(manifest_bytes),
        "schema_version manifest_id classification datasets instrument_catalog cutoffs settings_file",
    )
    _require(
        type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
        "unsupported_schema_version",
        "schema version 1 required",
    )
    _require(
        manifest["classification"] == "synthetic",
        "invalid_classification",
        "synthetic inputs required",
    )
    _require(
        manifest["manifest_id"]
        == sha256(
            {key: value for key, value in manifest.items() if key != "manifest_id"}
        ),
        "manifest_identity_mismatch",
        "manifest contents differ from identity",
    )
    raw_settings, settings_path = _file(root, manifest["settings_file"])
    settings = load_settings(raw_settings)
    cutoffs = _keys(
        manifest["cutoffs"], "business_as_of knowledge_cutoff system_cutoff"
    )
    for name, value in cutoffs.items():
        _require(
            TimestampEvidence(value, "instant").as_utc()
            == TimestampEvidence(settings["time"][name], "instant").as_utc(),
            "cutoff_mismatch",
            "manifest and settings cutoffs differ",
        )
    datasets = manifest["datasets"]
    _require(
        isinstance(datasets, list) and len(datasets) == len(SCHEMAS),
        "invalid_datasets",
        "one dataset per table required",
    )
    raw_tables = {format: {} for format in ("json", "csv")}
    sources, metadata, selected, locations = {}, {}, {}, []
    paths, dataset_ids, logical_ids = {settings_path, "manifest.json"}, set(), set()
    for item in datasets:
        dataset = _keys(
            item,
            "dataset_id logical_dataset_id record_type schema_version source_name selected_format files",
            "snapshot_id event_stream_id",
        )
        for key in ("dataset_id", "logical_dataset_id", "source_name"):
            _text(dataset[key], key)
        name = dataset["record_type"]
        _require(
            isinstance(name, str)
            and name in SCHEMAS
            and name not in sources
            and dataset["dataset_id"] not in dataset_ids
            and dataset["logical_dataset_id"] not in logical_ids,
            "duplicate_dataset",
            "table/dataset/authority identity absent or repeated",
        )
        _require(
            type(dataset["schema_version"]) is int and dataset["schema_version"] == 1,
            "unsupported_schema_version",
            "dataset version 1 required",
        )
        boundary = "event_stream_id" if name == "lifecycle_event" else "snapshot_id"
        _require(
            boundary in dataset
            and ("snapshot_id" if boundary == "event_stream_id" else "event_stream_id")
            not in dataset,
            "invalid_dataset_scope",
            "explicit snapshot or event stream required",
        )
        _text(dataset[boundary], boundary)
        _require(
            dataset["selected_format"] in ("json", "csv"),
            "unsupported_format",
            "one authority format required",
        )
        _require(
            isinstance(dataset["files"], list) and len(dataset["files"]) == 2,
            "invalid_representations",
            "exactly JSON and CSV representations required",
        )
        formats = set()
        for entry in dataset["files"]:
            file = _keys(entry, "path format sha256")
            _require(
                file["format"] in ("json", "csv") and file["format"] not in formats,
                "duplicate_representation",
                "one physical file per format required",
            )
            raw, path = _file(root, file)
            _require(path not in paths, "duplicate_path", "physical source file reused")
            paths.add(path)
            formats.add(file["format"])
            rows = decode_table(name, raw, file["format"])
            raw_tables[file["format"]][name] = rows
            if file["format"] == dataset["selected_format"]:
                selected[name] = rows
                locations.extend(
                    SourceLocation(
                        dataset["logical_dataset_id"],
                        name,
                        dataset["source_name"],
                        path,
                        file["format"],
                        file["sha256"],
                        number,
                    )
                    for number in range(1, len(rows) + 1)
                )
        sources[name] = dataset["source_name"]
        metadata[name] = dataset
        dataset_ids.add(dataset["dataset_id"])
        logical_ids.add(dataset["logical_dataset_id"])
    _require(
        manifest["instrument_catalog"] == metadata["instrument_catalog"]["dataset_id"],
        "invalid_catalog_reference",
        "manifest catalog dataset differs",
    )
    normalized = {}
    for raw in raw_tables.values():
        for table, bound in {
            "inventory_position": "max_positions",
            "borrow_request": "max_requests",
            "loan": "max_loans",
            "lifecycle_event": "max_events",
        }.items():
            _require(
                len({row["record_id"] for row in raw[table]})
                <= settings["bounds"][bound],
                "workload_exceeded",
                "input exceeds declared workload",
            )
    for format in ("json", "csv"):
        normalized[format], catalog = normalize_tables(raw_tables[format], sources)
        validate_settings_catalog(settings, catalog)

    def semantic_tables(tables):
        return {
            name: sorted(
                (row.to_row(semantic=True) for row in rows), key=canonical_bytes
            )
            for name, rows in tables.items()
        }

    _require(
        semantic_tables(normalized["json"]) == semantic_tables(normalized["csv"]),
        "representation_mismatch",
        "JSON and CSV business facts differ",
    )
    tables, catalog = normalize_tables(selected, sources)
    for name, rows in tables.items():
        scope = "event_stream_id" if name == "lifecycle_event" else "snapshot_id"
        for row in rows:
            if scope in row.payload:
                _require(
                    row.payload[scope] == metadata[name][scope],
                    "dataset_scope_mismatch",
                    "row scope differs from manifest",
                )
    for row in tables["net_benefit"]:
        for field in ("currency", "horizon_id", "horizon_start", "horizon_end"):
            expected = settings["earnings"][field]
            if field in ("horizon_start", "horizon_end"):
                expected = TimestampEvidence(expected, "instant").normalized_value
            _require(
                row.payload[field] == expected,
                "earnings_convention_mismatch",
                "coefficient currency/horizon differs from settings",
            )
    semantic = {
        "schema_version": 1,
        "classification": "synthetic",
        "settings": settings,
        "tables": semantic_tables(tables),
        "sources": sources,
        "scopes": {
            name: {
                key: value
                for key, value in entry.items()
                if key not in ("files", "selected_format")
            }
            for name, entry in metadata.items()
        },
    }
    return InputPack(
        manifest["manifest_id"],
        sha256(semantic),
        _freeze(manifest),
        _freeze(settings),
        tables,
        catalog,
        tuple(locations),
    )
