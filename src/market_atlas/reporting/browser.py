"""Reviewed, typed snapshot for the optional local browser report."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from market_atlas.reporting.export import validate_pack


def browser_snapshot(pack, *, analytics_pack=None):
    pack = Path(pack)
    validate_pack(pack)
    manifest = json.loads((pack / "manifest.json").read_text())
    required = {
        "macro_nodes",
        "macro_edges",
        "source_context",
        "revision_quality",
        "publications",
    }
    if not required <= manifest["tables"].keys():
        raise ValueError("browser report requires the real macro publication pack")
    queries = {}
    for name, spec in manifest["tables"].items():
        rows = []
        with (pack / spec["file"]).open(newline="") as source:
            for row in csv.DictReader(source):
                for column in spec["columns"]:
                    key, kind = column["name"], column["type"]
                    value = row[key]
                    row[key] = (
                        None
                        if value == ""
                        else int(value)
                        if kind == "integer"
                        else float(value)
                        if kind == "number"
                        else value.lower() == "true"
                        if kind == "logical"
                        else value
                    )
                rows.append(row)
        queries[name] = {
            "rows": rows,
            "source": {
                "label": "MarketAtlas PostgreSQL publication export · restricted internal only",
                "files": [spec["file"], "manifest.json"],
                "filters": ["Immutable pack " + manifest["pack_id"]],
                "grain": " + ".join(spec["primary_key"]),
                "notes": [
                    "Publication time is not source freshness.",
                    "Current taxonomy and captured-current quality; historical source availability is not established.",
                ],
                "evidenceFlow": [
                    {
                        "title": "Snapshot-pinned PostgreSQL export",
                        "detail": "Read-only atlas_report export; pack_id "
                        + manifest["pack_id"]
                        + "; table SHA-256 "
                        + spec["sha256"],
                    }
                ],
            },
        }
    nodes = {row["node_id"]: row for row in queries["macro_nodes"]["rows"]}
    counts, catalog = {}, []
    for edge in queries["macro_edges"]["rows"]:
        series, concept = nodes[edge["source_node_id"]], nodes[edge["target_node_id"]]
        counts.setdefault(concept["node_id"], set()).add(series["node_id"])
        catalog.append(
            {
                "series": series["display_label"],
                "node_id": series["node_id"],
                "concept": concept["display_label"],
                "frequency": series.get("details_frequency"),
                "units": series.get("details_units"),
                "source_record": edge["source_record"],
                "assertion_id": edge["assertion_id"],
                "snapshot": edge["serving_snapshot_id"],
            }
        )
    evidence = {
        "label": "Current economic taxonomy",
        "files": ["macro_nodes.csv", "macro_edges.csv", "manifest.json"],
        "filters": ["Immutable pack " + manifest["pack_id"]],
        "notes": [
            "Catalog membership does not establish observation ingestion or analytical eligibility."
        ],
        "metricDefinitions": [
            {
                "label": "Series",
                "definition": "Distinct source node IDs per concept. Counts across concepts are not additive.",
            }
        ],
        "evidenceFlow": [
            {
                "title": "Immutable inputs",
                "detail": "pack_id "
                + manifest["pack_id"]
                + "; macro_nodes SHA-256 "
                + manifest["tables"]["macro_nodes"]["sha256"]
                + "; macro_edges SHA-256 "
                + manifest["tables"]["macro_edges"]["sha256"],
            },
            {
                "title": "Taxonomy join",
                "detail": "Look up both macro_edges endpoints by unique macro_nodes.node_id; group by concept and count distinct source IDs.",
            },
        ],
    }
    queries["catalog"] = {"rows": catalog, "source": evidence}
    queries["concept_coverage"] = {
        "rows": sorted(
            [
                {"concept": nodes[key]["display_label"], "series": len(value)}
                for key, value in counts.items()
            ],
            key=lambda row: -row["series"],
        ),
        "source": evidence,
    }
    if analytics_pack is not None:
        from market_atlas.reporting.macro_analytics import analytics_queries

        queries.update(analytics_queries(analytics_pack))
    return {
        "surface": "dashboard",
        "title": "MarketAtlas · Macro research",
        "generatedAt": datetime.now(UTC).isoformat(),
        "buildStatus": "creating",
        "status": manifest.get("redistribution_status", "restricted_internal_only"),
        "filters": [],
        "queries": queries,
        "exportPreferences": {"selected": None, "destinations": []},
    }
