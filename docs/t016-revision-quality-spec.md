# T-016 — Revision-quality source contract

## Objective

Promote `gold.v_series_revision_summary` as a restricted, internal-only,
current-quality source interface. It supplies revision-risk metadata for already
approved FRED series; it does not create historical taxonomy, revision, causal,
or sensitivity claims.

## Ownership and rights decision

On 2026-10-26, Josh / project owner accepted the source/data, database,
report, quant-methodology, refresh/recovery, and incident-accountability roles
for this local pilot. The approved audience is authorized internal use only.
`restricted` is the manifest/contract status: no external redistribution,
public screenshot, source extract, or derived-data publication is authorized
without a future documented terms decision.

## Contract

The interface grain is one current revision-quality summary per `series_id`.
Required fields are `series_id`, `observation_count`, `avg_revision_count`,
`max_revision_count`, `avg_abs_revision_pct`, and
`max_abs_revision_pct`. A missing row is `unknown`; it is never represented as
zero revisions. The adapter verifies explicitly configured IDs against
`gold.dim_series`, then queries the summary view in configurable batches of
1–1,000 IDs. It deliberately does not initiate a whole-view scan because the
view is derived from a large revision-history surface.

## Implementation plan

1. Add the approved contract and ownership/rights registry entries; test schema
   verification against the metadata catalog.
2. Add a pure extract validator and a read-only bounded adapter/CLI command;
   test duplicate, unknown, and missing-series behavior before implementation.
3. Run the adapter against the local source, retain only an ignored extract,
   validate its manifest/counts, and update discovery/acceptance/handoff.

## Boundaries

- Source sessions use `marketatlas_source_reader` and never write upstream.
- This slice writes no `atlas` or `atlas_report` rows; publication/UI exposure
  is a later task after the bounded extract proves the contract.
- `gold.fred_revision_stats` remains out of scope because its estimated 20.5M
  rows need a separately approved temporal workload.

## Success criteria

- Source-contract verification includes exactly this additional approved view.
- The adapter reads only approved IDs in bounded batches and emits a
  checksum-backed, `current_only` extract with explicit missing IDs.
- Unit tests and one local read-only validation run pass without exposing
  source rows or credentials.
