# Snapshot-pinned reporting contract

Every report query begins with `atlas_report.current_snapshot_metadata`. The publication pointer resolves exactly one `serving_snapshot_id`; all current report views join to that ID. Consumers must retain that resolved ID for a refresh and must not independently re-resolve the pointer for each table.

| View | Grain | Purpose |
| --- | --- | --- |
| `current_snapshot_metadata` | Publication | Snapshot, build, input manifest, cutoff, publication time, output hash, and validation summary |
| `current_node_dimension` | Snapshot × node | Canonical entity identity and display attributes |
| `current_relationship_fact` | Snapshot × assertion version | Sourced/curated relationship endpoints, status, rationale, source record, and history support |
| `current_macro_context_fact` | Snapshot × curated-context version | Context type, evidence basis, rationale, owner, taxonomy, supporting assertion, and explicit context-only label |
| `current_macro_source_context` | Macro-context publication snapshot × source context record | Current source taxonomy/coverage or scheduled release event, its exact input manifest, source record, and explicit temporal status |
| `current_macro_economic_graph_node` | Macro-economic-graph snapshot × node | Current source-taxonomy macro series and economic-concept nodes, with manifest lineage |
| `current_macro_economic_graph_edge` | Macro-economic-graph snapshot × `measures` assertion | Source-backed series-to-concept edges, with source record, taxonomy provenance, and explicit `current_only` treatment |
| `current_rolling_correlation_estimate` | Snapshot × correlation estimate version | Canonical pair, endpoint, fixed window, sample count, correlation/undefined status, cutoff, and calculation identity |
| `current_bounded_path_bridge` | Snapshot × bounded directed path | Start/end node, depth (maximum four), ordered node/assertion/edge arrays |
| `current_provenance` | Snapshot × displayed subject | Build, input manifest, source record, support assertion, method/configuration/input-selection identity, cutoff, and details |

`current_relationship_fact`, `current_macro_context_fact`, `current_macro_source_context`, and `current_rolling_correlation_estimate` are separate facts. A curated context must not be aggregated or labeled as a statistical estimate. `current_macro_source_context` is a separate `macro_context` publication, so it cannot replace or mix with the fixture/default publication. Its taxonomy and coverage records are explicitly `current_only`; its release records are explicitly `scheduled_event`. Correlation counts must operate at the estimate-version grain; when joining endpoint nodes, both joins are single-valued snapshot dimensions, so one estimate remains one row.

`current_macro_economic_graph_node` and `current_macro_economic_graph_edge` are a separate `macro_economic_graph` publication. The local report API uses only those two views under `marketatlas_report_reader`; the React client calls that API rather than PostgreSQL. Its edges are source-backed current taxonomy projections and must remain visibly distinct from curated mappings and analytical estimates. For a full catalog, the API returns a source-to-concept aggregate navigation view by default, then a bounded, paged concept neighborhood on selection. Aggregate `contains` links are API/UI navigation aids and are never stored or represented as reference assertions; only returned `measures` edges are source-backed graph assertions.

For provenance drill-through, use `provenance_kind` plus `subject_id`:

- `relationship` joins `subject_id` to `relationship_fact.assertion_id`.
- `macro_context` joins `subject_id` to `macro_context_fact.curated_macro_context_version_id`.
- `macro_source_context` joins `subject_id` to `current_macro_source_context.context_subject_id`.
- `rolling_correlation` joins `subject_id` to `rolling_correlation_estimate_version_id`.

The fixture validation proves a sourced relationship, a curated context, and a correlation each resolve to their expected evidence. These PostgreSQL views are the contract for the later React demo and Power BI implementation; they are not themselves Power BI acceptance evidence.

## Power BI source package

`powerbi/MarketAtlas.model.template.tmdl` is the source-controlled fixture
semantic-model template. It intentionally captures one `pSnapshotId` before a
refresh and filters every imported `atlas_report.*_snapshot` table by that UUID.
It does not import the moving `current_*` fact views. The model package,
report-page design, and fixture reconciliation script are in
[`powerbi/README.md`](../powerbi/README.md). They are validated as source
contracts only; visual/filter/drill-through acceptance remains pending until
the package runs in an authorized Power BI environment.
