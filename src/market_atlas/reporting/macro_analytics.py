"""Validated, compact reviewed evidence for the browser's macro research views."""

import json
from pathlib import Path

from market_atlas.analytics.macro_pack import validate_pack
from market_atlas.contracts import sha256

QUERY_IDS = tuple(
    "macro_analytics_" + suffix
    for suffix in (
        "groups",
        "relationships",
        "dispersion",
        "nodes",
        "evidence",
        "points",
    )
)
GROUP_LABELS = {
    "inflation": "Inflation",
    "labor_conditions": "Labor conditions",
    "treasury_yields": "Treasury yields",
}


def analytics_queries(pack):
    pack = Path(pack)
    validate_pack(pack)
    manifest = json.loads((pack / "manifest.json").read_text())
    prepared = json.loads((pack / "prepared.json").read_text())
    results = json.loads((pack / "results.json").read_text())
    names = {
        e["source_identifier"]: e.get("label", e["source_identifier"])
        for e in prepared["capture"]["entities"]
    }
    group_rows = []
    for group in prepared["settings"]["groups"]:
        group_rows.append(
            {
                **{k: v for k, v in group.items() if k != "members"},
                "group_id": group["id"],
                "group_label": GROUP_LABELS.get(group["id"], group["id"]),
                "members_json": json.dumps(
                    [
                        {**m, "label": names.get(m["series_id"], m["series_id"])}
                        for m in group["members"]
                    ]
                ),
                "pack_id": manifest["pack_id"],
                "as_of": manifest["as_of"],
                "captured_at": prepared["capture"]["manifest"]["extracted_at"],
                "method_version": results["method_version"],
                "settings_sha256": prepared["settings_sha256"],
                "source_rows_sha256": results["source_rows_sha256"],
            }
        )
    pairs = [
        {**r, "pair_key": r["series_low_id"] + "|" + r["series_high_id"]}
        for r in results["relationships"]
    ]
    points, point_ids, evidence = [], {}, []
    for panel in prepared["panels"]:
        for member in panel["members"]:
            window_ids = []
            for point in member["points"]:
                identity = {
                    "group_id": panel["group_id"],
                    "series_id": member["series_id"],
                    **point,
                }
                digest = sha256(identity)
                if digest not in point_ids:
                    point_ids[digest] = len(points)
                    points.append(
                        {
                            **identity,
                            "point_id": len(points),
                            "source_records": json.dumps(point["source_records"]),
                        }
                    )
                window_ids.append(point_ids[digest])
            evidence.append(
                {
                    **{
                        k: panel[k]
                        for k in (
                            "group_id",
                            "knowledge_date",
                            "reference_start",
                            "reference_end",
                            "input_sha256",
                            "max_input_available_on",
                        )
                    },
                    **{
                        k: member[k]
                        for k in (
                            "series_id",
                            "usable_change_count",
                            "baseline_count",
                            "baseline_mean",
                            "baseline_sd",
                            "baseline_input_sha256",
                            "zscore_status",
                        )
                    },
                    "point_status_counts": json.dumps(
                        member["point_status_counts"], sort_keys=True
                    ),
                    "window_point_ids": json.dumps(window_ids),
                }
            )
    definitions = [
        {
            "label": "Correlation distance",
            "definition": "sqrt(2 * (1 - Pearson correlation)); 0 to 2, retaining the sign of comovement. Not a screen distance or causal measure.",
        },
        {
            "label": "Group dispersion",
            "definition": "Sample standard deviation across every configured member's latest standardized oriented change. Each member uses its own preceding-only baseline; incomplete groups are unavailable.",
        },
        {
            "label": "Node divergence",
            "definition": "Absolute deviation of a member's standardized change from the complete group's mean, in standardized units. Missing members are not removed to create a ranking.",
        },
        {
            "label": "Rolling correlation",
            "definition": "Pearson correlation of paired, oriented transformed changes in the configured fixed window. Requires the declared minimum paired count and nonzero variance; missing periods are not filled.",
        },
        {
            "label": "Standardized change",
            "definition": "The latest oriented change minus its preceding baseline mean, divided by the baseline sample standard deviation. The current change is excluded from its own baseline; insufficient or constant baselines are unavailable.",
        },
    ]
    change_definition = {
        "label": "Transformed changes",
        "definition": "100 * log(current / previous) for configured positive indexes, or percentage-point differences for configured rates/ratios, with the declared orientation. Inputs must be adjacent on the monthly or weekday grid and source-available by the panel's knowledge date.",
    }
    source = {
        "label": "Validated macro relationship research pack",
        "files": ["manifest.json", "prepared.json", "results.json", "schema.json"],
        "filters": [
            "Independent analytics pack " + manifest["pack_id"],
            "Capture cutoff " + manifest["as_of"],
        ],
        "metricDefinitions": definitions,
        "notes": [
            "Descriptive research, not validated predictive or causal signals.",
            "Date-precision source histories reconstructed from a later capture; current metadata and fixed operator groups, not historical taxonomy or MarketAtlas historical possession.",
            "Monthly changes are adjacent calendar-month log percentages or percentage-point differences; daily yields use adjacent weekday percentage-point differences. No filling or window widening.",
            "Analysis pack is independent of report publications and is retained until explicitly replaced; a normal report refresh does not regenerate analytics.",
            "Pairwise missingness may prevent a common metric embedding. Source record time is not availability time.",
        ],
        "evidenceFlow": [
            {
                "title": "Validated retained inputs",
                "detail": "Pack "
                + manifest["pack_id"]
                + "; preparation "
                + prepared["prepared_sha256"]
                + "; source rows "
                + results["source_rows_sha256"]
                + "; settings "
                + prepared["settings_sha256"],
            },
            {
                "title": "Reproduction",
                "detail": "analytics prepare-macro --settings configs/macro_analytics.toml --as-of "
                + manifest["as_of"]
                + "; analytics build-macro --input <retained prepared.json>; analytics validate-macro --input <pack directory>. Retained settings, captures and method versions are in prepared.json.",
            },
            {
                "title": "Method",
                "detail": results["method_version"]
                + "; verify-macro-analytics.py independently checks supported numbers with 50-digit Decimal arithmetic at 1e-10 tolerance.",
            },
        ],
    }

    def query(rows, grain, *, payload_columns=(), metrics=None):
        return {
            "rows": rows,
            "source": {
                **source,
                "grain": grain,
                "metricDefinitions": [
                    d for d in definitions if metrics is None or d["label"] in metrics
                ]
                + [change_definition],
            },
            **({"payloadColumns": list(payload_columns)} if payload_columns else {}),
            "methods": [
                {
                    "language": "python",
                    "code": "market_atlas.reporting.macro_analytics.analytics_queries: validate the immutable research pack; retain original estimates and nulls; deduplicate identical transformed point states by series and source evidence; link each panel to its exact point IDs. No estimates are recalculated for presentation.",
                }
            ],
        }

    return dict(
        zip(
            QUERY_IDS,
            (
                query(
                    group_rows,
                    "group_id within independent analytics pack",
                    payload_columns=("members_json",),
                ),
                query(
                    pairs,
                    "group_id + knowledge_date + canonical series pair",
                    metrics=("Rolling correlation", "Correlation distance"),
                ),
                query(
                    results["group_dispersion"],
                    "group_id + knowledge_date",
                    metrics=("Group dispersion", "Standardized change"),
                ),
                query(
                    results["node_divergence"],
                    "group_id + knowledge_date + series_id",
                    metrics=(
                        "Node divergence",
                        "Correlation distance",
                        "Standardized change",
                    ),
                ),
                query(
                    evidence,
                    "group_id + knowledge_date + series_id",
                    payload_columns=("window_point_ids", "point_status_counts"),
                    metrics=("Standardized change",),
                ),
                query(
                    points,
                    "point_id within independent analytics pack",
                    payload_columns=("source_records",),
                    metrics=(),
                ),
            ),
            strict=True,
        )
    )
