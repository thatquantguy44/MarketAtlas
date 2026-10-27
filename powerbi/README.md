# Power BI semantic-model source package

This folder contains a source-controlled TMDL template for the synthetic fixture report. It deliberately contains no database credential, local configuration path, or source-schema object. It is not a PBIX or PBIP, and it has not been opened in Power BI Desktop from this macOS environment.

## Snapshot-pinned refresh

Before every refresh, an approved report operator must capture the UUID in `atlas_report.current_snapshot_metadata` for publication `default`, then set `pSnapshotId` in `MarketAtlas.model.template.tmdl`. Do not leave the all-zero placeholder in place.

Each imported fact/dimension query filters an immutable `atlas_report` snapshot table by that same UUID. `Snapshot Metadata` also verifies that the selected UUID is still the active `default` publication when the refresh begins. This prevents different imported tables from resolving a moving publication pointer.

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
