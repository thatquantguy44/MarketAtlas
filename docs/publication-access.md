# Access MarketAtlas PostgreSQL publications

Connect to the target PostgreSQL database using the server, port, database and
login configured in ignored `configs/local.toml`. In pgAdmin or DBeaver, browse
**Schemas → atlas_report → Views**. A MarketAtlas publication is a named pointer
to a complete report snapshot. Its registry is
`atlas_report.current_snapshot_metadata`.

Use a PostgreSQL login with permission to assume `marketatlas_report_reader`.
That role itself has `NOLOGIN`; it is not a standalone username/password login.
For repeatable CLI exports, configure the dedicated `[report_database]` profile
shown in [the data-job guide](../powerbi/guides/data-jobs.md). That profile was not
present during the rename check; local validation used the existing authorized
connection and explicitly assumed the reader role. No new login was provisioned.

## Browse all four publications

Run [the read-only discovery script](../sql/queries/publications.sql), or:

```sql
BEGIN READ ONLY;
SET LOCAL ROLE marketatlas_report_reader;
SELECT publication_name, serving_snapshot_id, published_at,
       input_manifest_id, build_run_id, knowledge_cutoff, row_count
FROM atlas_report.current_snapshot_metadata
ORDER BY publication_name;
COMMIT;
```

`row_count` is the publisher's declared snapshot count; it is not the sum of all
report dimension/fact rows. The fixture publisher, for example, records its
correlation estimate count there. Query the relevant view to count its rows.

| Publication | Report views in `atlas_report` | Contents |
| --- | --- | --- |
| `synthetic_fixture` | `current_node_dimension`, `current_relationship_fact`, `current_macro_context_fact`, `current_rolling_correlation_estimate`, `current_bounded_path_bridge` | Generated market-map, context and correlation demonstration |
| `macro_economic_graph` | `current_macro_economic_graph_node`, `current_macro_economic_graph_edge` | Actual current macro-series/concept taxonomy |
| `macro_context` | `current_macro_source_context` | Actual current taxonomy, source coverage and scheduled releases; filter `context_kind` |
| `macro_revision_quality` | `current_macro_revision_quality` | Actual selected-series current revision summaries; scalar metrics are in `details` |

Use `current_provenance` with the selected snapshot ID and subject kind/ID to
inspect lineage. For example, browse actual taxonomy nodes:

```sql
SELECT node_id, node_type, display_label, temporal_status, source_record, details
FROM atlas_report.current_macro_economic_graph_node
ORDER BY node_type, display_label
LIMIT 50;
```

For a multi-query refresh, resolve the snapshot ID once and query the matching
`*_snapshot` tables using `WHERE serving_snapshot_id = <resolved UUID>`. Each
publication keeps its own snapshot and dates. The current views are convenient
for inspection; separately resolving them for each import can mix refresh times.
The [export job](../powerbi/guides/data-jobs.md) already pins them consistently.

## Power BI and CSV access

In Power BI Desktop, use **Get Data → PostgreSQL database**, enter the target
server/port and database from local configuration, and authenticate with the
report login. Select the report schema or use snapshot-filtered SQL. The
synthetic [TMDL template](../powerbi/MarketAtlas.model.template.tmdl) now uses
`pPublicationName = "synthetic_fixture"`; it does not define the live macro pages.

For actual-data CSV packs:

```sh
PYTHONPATH=src python3 -m market_atlas powerbi export \
  --source published --config configs/local.toml \
  --publications macro_economic_graph macro_context macro_revision_quality \
  --output data/generated/powerbi-real
```

To include the synthetic report in a published-data export, explicitly add
`synthetic_fixture` to `--publications`. Retained export folders are immutable
historical artifacts. A pack created before the rename may still contain the
old publication label; generate a new pack for the current label.

## Rename record

Migration [012](../sql/migrations/012_rename_synthetic_fixture_publication.sql)
renames the former `default` pointer to `synthetic_fixture`, preserving snapshot
ID and original publication timestamp. Existing build manifests retain their
original configuration; future fixture builds use the explicit name. The
migration refuses a collision and prevents older producers from recreating the
legacy name. Its local application preserved all three actual-data publication
pointers and did not rebuild or modify their report data. Historical reports and
packs retain the labels observed when they were generated.
