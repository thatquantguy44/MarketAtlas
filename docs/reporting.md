# Snapshot-pinned reporting contract

Every report query begins with `atlas_report.current_snapshot_metadata`. The publication pointer resolves exactly one `serving_snapshot_id`; all current report views join to that ID. Consumers must retain that resolved ID for a refresh and must not independently re-resolve the pointer for each table.

| View | Grain | Purpose |
| --- | --- | --- |
| `current_snapshot_metadata` | Publication | Snapshot, build, input manifest, cutoff, publication time, output hash, and validation summary |
| `current_node_dimension` | Snapshot × node | Canonical entity identity and display attributes |
| `current_relationship_fact` | Snapshot × assertion version | Sourced/curated relationship endpoints, status, rationale, source record, and history support |
| `current_macro_context_fact` | Snapshot × curated-context version | Context type, evidence basis, rationale, owner, taxonomy, supporting assertion, and explicit context-only label |
| `current_rolling_correlation_estimate` | Snapshot × correlation estimate version | Canonical pair, endpoint, fixed window, sample count, correlation/undefined status, cutoff, and calculation identity |
| `current_bounded_path_bridge` | Snapshot × bounded directed path | Start/end node, depth (maximum four), ordered node/assertion/edge arrays |
| `current_provenance` | Snapshot × displayed subject | Build, input manifest, source record, support assertion, method/configuration/input-selection identity, cutoff, and details |

`current_relationship_fact`, `current_macro_context_fact`, and `current_rolling_correlation_estimate` are separate facts. A curated context must not be aggregated or labeled as a statistical estimate. Correlation counts must operate at the estimate-version grain; when joining endpoint nodes, both joins are single-valued snapshot dimensions, so one estimate remains one row.

For provenance drill-through, use `provenance_kind` plus `subject_id`:

- `relationship` joins `subject_id` to `relationship_fact.assertion_id`.
- `macro_context` joins `subject_id` to `macro_context_fact.curated_macro_context_version_id`.
- `rolling_correlation` joins `subject_id` to `rolling_correlation_estimate_version_id`.

The fixture validation proves a sourced relationship, a curated context, and a correlation each resolve to their expected evidence. These PostgreSQL views are the contract for the later React demo and Power BI implementation; they are not themselves Power BI acceptance evidence.
