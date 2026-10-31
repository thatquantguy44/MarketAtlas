# Power BI semantic-model source package

This folder contains a source-controlled TMDL template for the synthetic fixture report. It deliberately contains no database credential, local configuration path, or source-schema object. It is not a PBIX or PBIP, and it has not been opened in Power BI Desktop from this macOS environment.

## Data generation jobs and report guides

For portable CSV ingestion, start with [data jobs](guides/data-jobs.md):

```sh
PYTHONPATH=src python3 -S -m market_atlas powerbi export --output data/generated/powerbi
```

The command returns an immutable pack folder with typed tables, checksums,
counts and provenance. It works without a database. A separate report-only
published-data mode exports the existing fixture, macro catalog, release/coverage
and revision-quality publications for restricted internal use. The
[Power Query loader](queries/fnLoadPack.pq) imports one selected pack.

[Report recipes](guides/report-recipes.md) provide model relationships, DAX,
visual layouts and reconciliation checks for market relationships, correlation
changes, macro coverage, release freshness, revision quality and provenance.
The [GitHub workflow](../.github/workflows/powerbi-data.yml) generates synthetic
packs on manual dispatch or relevant pull requests once pushed. Actual Power BI
execution and service refresh remain separate work; AC-009 stays partial.

The remainder of this document describes the existing PostgreSQL TMDL path.

[PostgreSQL publication access](../docs/publication-access.md) lists the registry,
report views and reader-role setup for all four publications. Migration 012
renames the original synthetic publication to `synthetic_fixture`; update that
parameter in any previously saved local template copies.

## Snapshot-pinned refresh

Before every refresh, an approved report operator must capture the UUID in `atlas_report.current_snapshot_metadata` for publication `synthetic_fixture`, then set `pSnapshotId` in `MarketAtlas.model.template.tmdl`. Do not leave the all-zero placeholder in place.

Each imported fact/dimension query filters an immutable `atlas_report` snapshot table by that same UUID. `Snapshot Metadata` also verifies that the selected UUID is still the active `synthetic_fixture` publication when the refresh begins. This prevents different imported tables from resolving a moving publication pointer.

Set `pServer` and `pDatabase` only in an authorized local copy. A database owner must provision a dedicated Power BI login that can use `marketatlas_report_reader`; never use a source-reader or writer role, and do not commit a connection string or password.

## Build the report in Power BI Desktop

Open the template in a Power BI Desktop project in an authorized Windows environment (native, VM, or remote desktop), allow the PostgreSQL connector to infer imported columns, then add the commented DAX measures from the template. Build five pages:

| Page | Required evidence |
| --- | --- |
| Snapshot and quality | pinned-status card, snapshot UUID/published time/cutoff, row count |
| Market map | node slicers, relationship table, source record/rationale drill-through |
| Macro context | mapping/evidence-basis slicers and visible context-only label |
| Correlation monitor | pair/status/date controls; correlation, paired count, window, cutoff, method |
| Provenance | relationship, context, and correlation drill-through to source/input/build/method/cutoff |

Keep relationship/context facts separate from rolling correlation estimates. Use distinct-count measures rather than summing entities after relationship joins. If target-side filtering is needed, create an explicit role-playing node dimension or an inactive target relationship; do not enable ambiguous bidirectional filters.

## AC-009 reconciliation script

For the deterministic fixture snapshot, retain screenshots and verify:

| Check | Expected result |
| --- | ---: |
| Snapshot metadata | exactly one row and `Pinned` status |
| Nodes | 15 |
| Relationship facts | 14 distinct assertion IDs |
| Curated macro contexts | 3 distinct context version IDs |
| Correlation estimates | 32 distinct estimate version IDs |
| Filter reset | compatible visuals change under node/macro/pair filters, then return to the totals above |
| Provenance | relationship `A11`, context `CTX3`, and one correlation expose source/input/build/method/cutoff evidence |

The filter/reset and visual provenance checks require a real Power BI Desktop or Power BI service execution. The source package alone does not pass AC-009.

## Repository validation

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`. The repository checks that the source template has one snapshot parameter, uses it in every imported snapshot query, and does not track secrets. This is model-source validation, not Power BI rendering evidence.
