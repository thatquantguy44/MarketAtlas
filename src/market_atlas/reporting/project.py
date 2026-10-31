"""Generate editable Power BI projects from validated, snapshot-pinned CSV packs.

This authors source only; it does not execute Power Query, DAX or Power BI.
"""

import json
from pathlib import Path

from market_atlas.reporting.export import validate_pack

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/"
DEFINITION = SCHEMA + "definition/"
TYPE_MAP = {
    "text": "string",
    "integer": "int64",
    "number": "double",
    "date": "dateTime",
    "datetimezone": "dateTime",
    "logical": "boolean",
}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _field(table, name, measure=False):
    kind = "Measure" if measure else "Column"
    return {
        "field": {
            kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}
        },
        "queryRef": f"{table}.{name}",
    }


def _visual(name, kind, title, roles, x, y, width, height):
    return {
        "$schema": DEFINITION + "visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": 0,
            "height": height,
            "width": width,
            "tabOrder": y + x,
        },
        "visual": {
            "visualType": kind,
            "query": {
                "queryState": {
                    role: {"projections": fields} for role, fields in roles.items()
                }
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'" + title.replace("'", "''") + "'"
                                    }
                                }
                            },
                        }
                    }
                ]
            },
        },
    }


def build_project(pack, output):
    """Write a new PBIP directory. Never overwrite a report or copy source rows."""
    pack, output = Path(pack).resolve(), Path(output).resolve()
    validate_pack(pack)
    manifest = json.loads((pack / "manifest.json").read_text())
    fixture = "relationships" in manifest["tables"]
    required = (
        {
            "nodes",
            "relationships",
            "contexts",
            "correlations",
            "pairs",
            "dates",
            "provenance",
            "publications",
        }
        if fixture
        else {
            "macro_nodes",
            "macro_edges",
            "source_context",
            "revision_quality",
            "publications",
            "macro_graph_provenance",
            "source_context_provenance",
            "quality_provenance",
        }
    )
    if not required <= manifest["tables"].keys():
        raise ValueError("pack does not contain the required report tables")
    if output.exists():
        raise FileExistsError("report output already exists; choose a new directory")
    output.mkdir(parents=True)
    model_dir = output / "MarketAtlas.SemanticModel"
    report_dir = output / "MarketAtlas.Report"
    _write(
        output / "MarketAtlas.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": "MarketAtlas.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    _write(model_dir / "definition.pbism", {"version": "1.0", "settings": {}})
    loader = (
        Path(__file__).resolve().parents[3] / "powerbi/queries/fnLoadPack.pq"
    ).read_text()
    tables = []
    for name, spec in manifest["tables"].items():
        conversions = [
            f'{{"{c["name"]}", each if _ = null then null else DateTimeZone.RemoveZone(DateTimeZone.ToUtc(_)), type datetime}}'
            for c in spec["columns"]
            if c["type"] == "datetimezone"
        ]
        expression = f'let Loaded = Record.Field(fnLoadPack(pPackFolder), "{name}")'
        expression += (
            ", UTC = Table.TransformColumns(Loaded, {"
            + ", ".join(conversions)
            + "}) in UTC"
            if conversions
            else " in Loaded"
        )
        tables.append(
            {
                "name": name,
                "columns": [
                    {
                        "name": c["name"],
                        "dataType": TYPE_MAP[c["type"]],
                        "sourceColumn": c["name"],
                        "summarizeBy": "none",
                    }
                    for c in spec["columns"]
                ],
                "partitions": [
                    {
                        "name": name,
                        "mode": "import",
                        "source": {"type": "m", "expression": expression},
                    }
                ],
            }
        )
    by_name = {t["name"]: t for t in tables}
    relations = []

    def copy_dimension(name, original, condition=None):
        table = json.loads(json.dumps(by_name[original]))
        table["name"] = table["partitions"][0]["name"] = name
        table["partitions"][0]["source"]["expression"] = (
            f"Table.SelectRows({original}, each {condition})" if condition else original
        )
        tables.append(table)
        by_name[name] = table

    def relationship(dimension, key, fact, foreign):
        relations.append(
            {
                "name": f"{dimension}_{fact}_{foreign}",
                "fromTable": fact,
                "fromColumn": foreign,
                "fromCardinality": "many",
                "toTable": dimension,
                "toColumn": key,
                "toCardinality": "one",
                "crossFilteringBehavior": "oneDirection",
                "isActive": True,
            }
        )

    def measure(table, name, expression, fmt="0"):
        by_name[table].setdefault("measures", []).append(
            {"name": name, "expression": expression, "formatString": fmt}
        )

    if fixture:
        for dim in ("SourceNode", "TargetNode", "ContextSeries", "ContextTarget"):
            copy_dimension(
                dim,
                "nodes",
                '[node_type] = "macro_series"' if dim == "ContextSeries" else None,
            )
        for dim, fact, foreign in [
            ("SourceNode", "relationships", "source_node_id"),
            ("TargetNode", "relationships", "target_node_id"),
            ("ContextSeries", "contexts", "macro_series_node_id"),
            ("ContextTarget", "contexts", "target_node_id"),
        ]:
            relationship(dim, "node_id", fact, foreign)
        relationship("pairs", "pair_id", "correlations", "pair_id")
        relationship("dates", "date", "correlations", "endpoint_session_date")
        for table, name, column in [
            ("nodes", "Node count", "node_id"),
            ("relationships", "Connection count", "assertion_id"),
            ("contexts", "Context count", "curated_macro_context_version_id"),
            (
                "correlations",
                "Estimate count",
                "rolling_correlation_estimate_version_id",
            ),
        ]:
            measure(table, name, f"DISTINCTCOUNT({table}[{column}])")
        measure(
            "correlations",
            "Correlation",
            "IF(HASONEVALUE(pairs[pair_id]) && HASONEVALUE(dates[date]), SELECTEDVALUE(correlations[correlation]))",
            "0.000",
        )
        pages = [
            (
                "Snapshot and quality",
                [
                    (
                        "card",
                        "Nodes",
                        {"Values": [_field("nodes", "Node count", True)]},
                    ),
                    (
                        "card",
                        "Connections",
                        {"Values": [_field("relationships", "Connection count", True)]},
                    ),
                    (
                        "tableEx",
                        "Pinned publication · synthetic fixture",
                        {
                            "Values": [
                                _field("publications", c)
                                for c in [
                                    "publication_name",
                                    "serving_snapshot_id",
                                    "published_at",
                                    "knowledge_cutoff",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Market map",
                [
                    (
                        "slicer",
                        "Source node",
                        {"Values": [_field("SourceNode", "display_label")]},
                    ),
                    (
                        "tableEx",
                        "Connections · retractions remain visible",
                        {
                            "Values": [
                                _field("relationships", c)
                                for c in [
                                    "assertion_id",
                                    "source_node_id",
                                    "target_node_id",
                                    "edge_type",
                                    "assertion_status",
                                    "rationale",
                                    "source_record",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Macro context",
                [
                    (
                        "slicer",
                        "Macro series",
                        {"Values": [_field("ContextSeries", "display_label")]},
                    ),
                    (
                        "tableEx",
                        "Context only · no measured sensitivity or causality",
                        {
                            "Values": [
                                _field("contexts", c)
                                for c in [
                                    "curated_macro_context_version_id",
                                    "macro_series_node_id",
                                    "target_node_id",
                                    "mapping_kind",
                                    "evidence_basis",
                                    "rationale",
                                    "mapping_owner",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Correlation monitor",
                [
                    ("slicer", "Pair", {"Values": [_field("pairs", "pair_label")]}),
                    (
                        "lineChart",
                        "Correlation · undefined estimates stay blank",
                        {
                            "Category": [_field("dates", "date")],
                            "Y": [_field("correlations", "Correlation", True)],
                            "Series": [_field("pairs", "pair_label")],
                        },
                    ),
                    (
                        "tableEx",
                        "Estimate diagnostics",
                        {
                            "Values": [
                                _field("correlations", c)
                                for c in [
                                    "pair_id",
                                    "endpoint_session_date",
                                    "estimate_status",
                                    "correlation",
                                    "paired_return_count",
                                    "method_version",
                                    "knowledge_cutoff",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Provenance",
                [
                    (
                        "slicer",
                        "Evidence kind",
                        {"Values": [_field("provenance", "provenance_kind")]},
                    ),
                    (
                        "slicer",
                        "Subject · A11 / CTX3 / estimate ID",
                        {"Values": [_field("provenance", "subject_id")]},
                    ),
                    (
                        "tableEx",
                        "Source and build evidence",
                        {
                            "Values": [
                                _field("provenance", c)
                                for c in [
                                    "provenance_kind",
                                    "subject_id",
                                    "source_record",
                                    "input_manifest_id",
                                    "build_run_id",
                                    "method_version",
                                    "knowledge_cutoff",
                                    "serving_snapshot_id",
                                ]
                            ]
                        },
                    ),
                ],
            ),
        ]
    else:
        copy_dimension("MacroSeries", "macro_nodes", '[node_type] = "macro_series"')
        copy_dimension(
            "MacroConcept", "macro_nodes", '[node_type] = "economic_concept"'
        )
        copy_dimension(
            "Coverage", "source_context", '[context_kind] = "source_coverage"'
        )
        copy_dimension("Releases", "source_context", '[context_kind] = "release_event"')
        for dim, fact, foreign in [
            ("MacroSeries", "macro_edges", "source_node_id"),
            ("MacroConcept", "macro_edges", "target_node_id"),
            ("MacroSeries", "Coverage", "series_node_id"),
            ("MacroSeries", "revision_quality", "series_node_id"),
        ]:
            relationship(dim, "node_id", fact, foreign)
        measure("MacroSeries", "Catalog series", "DISTINCTCOUNT(MacroSeries[node_id])")
        measure(
            "macro_edges",
            "Series in concept",
            "DISTINCTCOUNT(macro_edges[source_node_id])",
        )
        pages = [
            (
                "Publication status",
                [
                    (
                        "card",
                        "Catalog series",
                        {"Values": [_field("MacroSeries", "Catalog series", True)]},
                    ),
                    (
                        "tableEx",
                        "Independent publication snapshots · restricted internal only",
                        {
                            "Values": [
                                _field("publications", c)
                                for c in [
                                    "publication_name",
                                    "serving_snapshot_id",
                                    "published_at",
                                    "knowledge_cutoff",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Catalog coverage",
                [
                    (
                        "barChart",
                        "Series by economic concept",
                        {
                            "Category": [_field("MacroConcept", "display_label")],
                            "Y": [_field("macro_edges", "Series in concept", True)],
                        },
                    ),
                    (
                        "tableEx",
                        "Cataloged series · ingestion eligibility is separate",
                        {
                            "Values": [
                                _field("MacroSeries", c)
                                for c in [
                                    "display_label",
                                    "details_frequency",
                                    "details_units",
                                    "source_record",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Releases and freshness",
                [
                    (
                        "tableEx",
                        "Captured release calendar",
                        {
                            "Values": [
                                _field("Releases", c)
                                for c in [
                                    "effective_date",
                                    "details_release_name",
                                    "details_importance",
                                    "details_source_extracted_at",
                                ]
                            ]
                        },
                    ),
                    (
                        "tableEx",
                        "Source coverage · supplied stale flags",
                        {
                            "Values": [
                                _field("Coverage", c)
                                for c in [
                                    "details_series_id",
                                    "details_latest_observation_date",
                                    "details_observation_count",
                                    "details_is_stale",
                                    "details_source_extracted_at",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Revision quality",
                [
                    (
                        "slicer",
                        "Series",
                        {"Values": [_field("MacroSeries", "display_label")]},
                    ),
                    (
                        "tableEx",
                        "Captured-current summaries · unknown remains blank",
                        {
                            "Values": [
                                _field("revision_quality", c)
                                for c in [
                                    "series_id",
                                    "details_quality_status",
                                    "details_avg_revision_count",
                                    "details_max_revision_count",
                                    "details_avg_abs_revision_pct",
                                    "details_source_extracted_at",
                                ]
                            ]
                        },
                    ),
                ],
            ),
            (
                "Provenance",
                [
                    (
                        "tableEx",
                        "Graph evidence",
                        {
                            "Values": [
                                _field("macro_graph_provenance", c)
                                for c in [
                                    "subject_id",
                                    "source_record",
                                    "input_manifest_id",
                                    "build_run_id",
                                    "knowledge_cutoff",
                                ]
                            ]
                        },
                    ),
                    (
                        "tableEx",
                        "Context evidence",
                        {
                            "Values": [
                                _field("source_context_provenance", c)
                                for c in [
                                    "provenance_kind",
                                    "subject_id",
                                    "source_record",
                                    "build_run_id",
                                ]
                            ]
                        },
                    ),
                    (
                        "tableEx",
                        "Quality evidence",
                        {
                            "Values": [
                                _field("quality_provenance", c)
                                for c in [
                                    "subject_id",
                                    "source_record",
                                    "method_version",
                                    "knowledge_cutoff",
                                ]
                            ]
                        },
                    ),
                ],
            ),
        ]
    _write(
        model_dir / "model.bim",
        {
            "name": "MarketAtlas",
            "compatibilityLevel": 1600,
            "model": {
                "culture": "en-US",
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "expressions": [
                    {
                        "name": "pPackFolder",
                        "kind": "m",
                        "expression": ('"' + str(pack).replace('"', '""') + '"')
                        + ' meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
                    },
                    {"name": "fnLoadPack", "kind": "m", "expression": loader},
                ],
                "tables": tables,
                "relationships": relations,
            },
        },
    )
    _write(
        report_dir / "definition.pbir",
        {
            "$schema": SCHEMA + "definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": "../MarketAtlas.SemanticModel"}},
        },
    )
    definition = report_dir / "definition"
    _write(
        definition / "version.json",
        {
            "$schema": DEFINITION + "versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    _write(
        definition / "report.json",
        {"$schema": DEFINITION + "report/3.1.0/schema.json", "themeCollection": {}},
    )
    page_names = []
    for index, (title, visuals) in enumerate(pages):
        page_name = f"page{index + 1}"
        page_names.append(page_name)
        directory = definition / "pages" / page_name
        _write(
            directory / "page.json",
            {
                "$schema": DEFINITION + "page/2.0.0/schema.json",
                "name": page_name,
                "displayName": title,
                "displayOption": "FitToPage",
                "width": 1280,
                "height": 900,
            },
        )
        for number, (kind, label, roles) in enumerate(visuals):
            # Independent vertical regions avoid overlap; native Power BI can edit every visual.
            height = 820 / len(visuals)
            _write(
                directory / "visuals" / f"visual{number + 1}" / "visual.json",
                _visual(
                    f"p{index + 1}v{number + 1}",
                    kind,
                    label,
                    roles,
                    32,
                    32 + number * height,
                    1216,
                    height - 20,
                ),
            )
    _write(
        definition / "pages/pages.json",
        {
            "$schema": DEFINITION + "pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_names,
            "activePageName": page_names[0],
        },
    )
    _write(
        output / "project-manifest.json",
        {
            "pack_id": manifest["pack_id"],
            "source_kind": manifest["source_kind"],
            "redistribution_status": manifest.get("redistribution_status"),
            "pages": [p[0] for p in pages],
            "validation": "source_only_powerbi_execution_required",
            "pack_folder": str(pack),
        },
    )
    (output / "README.txt").write_text(
        "Open MarketAtlas.pbip in Power BI Desktop on Windows with PBIP/PBIR preview enabled.\n"
        "Power Query parameter pPackFolder points to one validated immutable pack.\n"
        "If moving computers, copy that pack privately and change pPackFolder before refresh.\n"
        "No database credentials or data rows are included in this project.\n"
        "This generated source has not been refreshed or rendered in Power BI.\n"
        "Dates originating with time zones are normalized to UTC before import.\n"
        "Evidence uses explicit subject/kind slicers; cross-page drill-through is not yet configured.\n"
    )
    return {
        "project": str(output / "MarketAtlas.pbip"),
        "pack_id": manifest["pack_id"],
        "pages": len(pages),
        "status": "source_only",
    }
