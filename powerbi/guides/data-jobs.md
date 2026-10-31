# Generate Power BI data packs

Use this job to prepare data before building or refreshing a report. The export
is a directory of UTF-8 CSV tables plus `manifest.json`, which records column
types, primary keys, counts, file checksums, and the content-derived pack ID.
The manifest also identifies the Python version, Git base revision and actual
Python source fingerprint. Each pack directory is immutable. The returned JSON
`pack` value is the folder
to use in Power BI. An identical rerun with the same code and environment reuses the same folder.

## Run a credential-free demonstration

From the repository root:

```sh
PYTHONPATH=src python3 -S -m market_atlas powerbi export --output data/generated/powerbi
```

Copy the returned `pack` path, then validate that exact folder:

```sh
PYTHONPATH=src python3 -S -m market_atlas powerbi validate --input data/generated/powerbi/<pack-id>
```

The job calculates correlations using the existing Python method and canonical
fixture inputs. It exports 15 nodes, 14 current relationship versions (including
a retraction), 3 curated contexts, 32 correlation estimates, 49 provenance rows,
2 pair dimension rows, and 16 endpoint dates. It includes no upstream data or
credentials. Its `synthetic_file` publication and `synthetic-file:` input identity
are file-export identities; they are not PostgreSQL serving snapshot or build IDs.
The publication timestamp and database build ID are null rather than invented.

This is a current-context demonstration. It includes the latest assertion
version for each business key, including A15's retraction of A6. Historical
source-availability and system-record replay remain separate database workflows.

## Export published internal data

Provision a login allowed to assume only `marketatlas_report_reader` for this
purpose. Add this section to ignored `configs/local.toml`, using local values:

```toml
[report_database]
host = "replace-me"
port = 5432
database = "replace-me"
username = "replace-me"
password = "replace-me"
role = "marketatlas_report_reader"
```

Install the repository's optional PostgreSQL dependency in your environment,
then run:

```sh
PYTHONPATH=src python3 -m market_atlas powerbi export \
  --source published --config configs/local.toml \
  --publications synthetic_fixture macro_economic_graph macro_context macro_revision_quality \
  --output data/generated/powerbi-internal
```

Select only the publications required for a report. A missing requested
publication fails the job rather than silently omitting data. `--max-rows`
defaults to 100,000 per database table and permits 1–1,000,000. Exceeding the
limit fails rather than truncating the export.

For a report using actual upstream-derived data only, omit `synthetic_fixture`: it is the
synthetic market-map/correlation publication even when read from PostgreSQL.
Use the three live macro publications explicitly:

```sh
PYTHONPATH=src python3 -m market_atlas powerbi export \
  --source published --config configs/local.toml \
  --publications macro_economic_graph macro_context macro_revision_quality \
  --output data/generated/powerbi-real
```

Load `macro_nodes`, `macro_edges`, `source_context`, `revision_quality` and
`publications`, plus the three corresponding provenance tables. Start with
pages 3–6 of [the report recipes](report-recipes.md). The current real graph
encodes series-to-concept taxonomy; real cross-series correlation networks,
community detection and centrality metrics are not yet produced by these jobs.

The job reads only allowlisted `atlas_report` snapshot tables. One read-only,
repeatable-read transaction resolves the selected publication pointers once,
then reads every fact/dimension using the resolved snapshot IDs. Concurrent
publication cannot mix versions inside a pack. No upstream extraction,
migration, analytical rebuild, or serving-pointer update occurs in this job.
Run the existing approved extraction/publication jobs first when newer source
captures are needed; exporting the same publication does not make it fresher.

All published-data packs are classified `restricted_internal_only`. Keep them
in the ignored output directory or approved internal storage. The GitHub job
below exports only generated synthetic data. Code ownership and file export do
not grant new source-data sharing rights.

## Table grains and model keys

| Table | Grain / primary key within one pack | Available from |
| --- | --- | --- |
| `publications` | One selected publication; `publication_name` | Every pack |
| `nodes` | One node; `node_id` | Synthetic / `synthetic_fixture` |
| `relationships` | One relationship version; `assertion_id` | Synthetic / `synthetic_fixture` |
| `contexts` | One curated mapping version; `curated_macro_context_version_id` | Synthetic / `synthetic_fixture` |
| `correlations` | Pair × endpoint × method/input selection; `rolling_correlation_estimate_version_id` | Synthetic / `synthetic_fixture` |
| `provenance` | Subject kind × subject ID | Synthetic / `synthetic_fixture` |
| `pairs` | Canonical low/high instrument pair; `pair_id` | Derived from correlations |
| `dates` | One correlation endpoint date; `date` | Derived from correlations |
| `macro_nodes` | One current taxonomy node; `node_id` | `macro_economic_graph` |
| `macro_edges` | One source-backed taxonomy assertion; `assertion_id` | `macro_economic_graph` |
| `source_context` | Context kind × context subject ID | `macro_context` |
| `revision_quality` | One selected series; `series_node_id` | `macro_revision_quality` |
| `macro_graph_provenance`, `source_context_provenance`, `quality_provenance` | Subject kind × subject ID, in the corresponding independent publication | Respective publication |

Column names and types for the actual pack are in `manifest.json`. Nested
`details` scalars become `details_*` columns, with complete JSON retained in
`details_json`. Provenance objects are retained as `provenance_json`. SQL nulls
become empty CSV fields, and the supplied M loader restores nulls before typing.
Undefined estimates and missing summaries never become zero.

The dimensions contain exactly the rows in the selected publications; the
exporter does not invent series identities to fill a missing join. For catalog
and quality reporting, retain the catalog dimension and display missing quality
selection separately. A graph snapshot and a quality snapshot have independent
input identities, capture times, and publication times.

## Load into Power BI Desktop

1. Validate the pack with the CLI. Copy that complete immutable folder to a path
   accessible to your Power BI authoring machine.
2. In Power Query, create a text parameter `pPackFolder` holding the absolute
   path to that folder, including its pack ID. All tables use the same parameter.
3. Create a blank query named `fnLoadPack`. Paste the function from
   [`../queries/fnLoadPack.pq`](../queries/fnLoadPack.pq) into its Advanced Editor.
4. Create a blank query named `Pack` with `= fnLoadPack(pPackFolder)`. Disable
   load for the function and the record-valued `Pack` query.
5. Create table queries named as shown in the table above. For example:

   ```powerquery
   = Pack[nodes]
   ```

   ```powerquery
   = Pack[correlations]
   ```

   ```powerquery
   = Pack[publications]
   ```

   For live pages, use `= Pack[macro_nodes]`, `= Pack[macro_edges]`,
   `= Pack[source_context]`, and `= Pack[revision_quality]` when exported.
6. Create the relationships in [the report guide](report-recipes.md), then add
   its measures and visuals. Keep IDs as text; numerical estimates should use
   measures rather than implicit sums.

The loader uses the manifest to set types with explicit `en-US` parsing, restores
nulls, and rejects unexpected headers and row counts. The Python validator also
checks hashes, key uniqueness, endpoint integrity and core provenance coverage.
Do not combine different table CSVs with Folder → Combine Files: their schemas
and grains differ. Do not append multiple pack folders without redesigning keys
to include publication and snapshot identity. `dates` is the set of correlation
endpoints, not a complete calendar; use the endpoint field directly on axes and
do not mark this sparse table as a full date table for time-intelligence DAX.

## Repeat or automate

The repository includes
[`.github/workflows/powerbi-data.yml`](../../.github/workflows/powerbi-data.yml).
Once committed and pushed, it runs credential-free tests and exports a synthetic
pack for relevant pull requests or a manual Actions dispatch. Its download
artifact includes the CSV pack, M function and guides. This workflow has not been
run on GitHub merely by creating it locally.

For end-to-end PostgreSQL refresh and export, use the optional
[Dagster jobs](../../docs/dagster-orchestration.md). For export-only jobs, invoke
the published export command from an approved local scheduler or private runner. Run validation after export and retain the JSON
result and exit status in an internal run log. A failed job leaves every earlier
complete pack available. No scheduler or Power BI service refresh is installed
by this change. Do not auto-delete a pack while a report may still reference it.

For a refresh, choose a new validated folder, update `pPackFolder` once, and
refresh all tables. Keep the parameter fixed until refresh finishes; retain the
previous folder for rollback. Do not let individual queries resolve a changing
"latest" directory. For Power BI service use, establish an approved accessible
storage location and gateway/connectivity setup before enabling scheduled
refresh. Credentials remain in the service's data source configuration.

## Validation and remaining acceptance

The repository tests file round-trips, expected fixture counts, undefined/null
handling, reproducible reruns, corrupted files, orphan and duplicate keys,
failed-export isolation, publication pinning, row limits, and read-only access.
An opt-in database test exports the four existing local publications without
writes. See [T-018 evidence](../../reports/t018-powerbi-data-jobs-validation.md).

Power Query/DAX snippets are authoring source; they have not been executed in
Power BI here. T-015 / AC-009 still requires actual report construction,
refresh/filter/count reconciliation, provenance drill-through and retained
artifacts in an authorized Power BI environment. The existing PostgreSQL TMDL
path remains available in [the original package instructions](../README.md).

Implementation references: Microsoft documents the CSV reader and explicit
column typing in [Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document)
and [Table.TransformColumnTypes](https://learn.microsoft.com/en-us/powerquery-m/table-transformcolumntypes),
and service connectivity considerations in [Data refresh](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data).
