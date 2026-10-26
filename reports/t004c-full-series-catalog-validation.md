# T-004C.5 full approved-series catalog validation

Run date: 2026-10-26. This evidence records only counts, identifiers, and hashes; it contains no credentials, connection coordinates, or source-row payloads.

## Scope and boundary

The full-catalog extractor reads all approved current records from `gold.dim_series` after the source-contract gate succeeds. It uses the read-only source role. Coverage is intentionally not selected for this catalog run: an unbounded scan of `gold.v_source_coverage` is not a suitable full-refresh dependency. That choice is explicit in the manifest as `coverage_temporal_status: not_selected`, not a claim that coverage is absent or historical.

The writer creates source-scoped canonical keys (`macro:{source}:{series_id}`), so a non-FRED approved series cannot be mislabeled as FRED. It writes only MarketAtlas `atlas` and `atlas_report` schemas.

## Executed result

```text
PYTHONPATH=src python -m market_atlas adapter extract-series-catalog \
  --config configs/local.toml --page-size 500 \
  --output data/generated/macro_series_catalog.json
PYTHONPATH=src python -m market_atlas economic-graph publish \
  --config configs/local.toml --input data/generated/macro_series_catalog.json
```

The contract gate passed. The extract contained 290 approved current taxonomy records and zero selected coverage records. Publication created an immutable `macro_economic_graph` snapshot with 301 nodes (290 series plus 11 concepts), 290 source-backed `measures` assertions, and 591 total snapshot rows. The published output SHA-256 was `8343f26cbdfc97711273dd156c4173b844f743dd9d461a8e29705bd03f6715a9`.

## Served behavior

The localhost report endpoint returned a catalog summary of 11 category hubs and 290 series. It reported frequency facets of 175 monthly, 77 daily, 25 quarterly, and 13 weekly series. Selecting the 120-series Regional hub with `limit=50&offset=50` returned 51 nodes (one concept plus 50 series) and 50 real `measures` edges. A category search returned only its matching bounded neighborhood.

The summary's `contains` links exist solely to navigate the UI from the approved catalog hub to category neighborhoods. They are labeled as aggregate navigation and are not stored reference assertions, causal claims, or sensitivities. Browser code still talks only to the local report API; it never queries MacroMedallion/PostgreSQL directly.

## Verification

`PYTHONPATH=src python -m unittest discover -s tests -v` passed 45 tests. `cd frontend && npm test && npm run build` passed 4 frontend assertions and the production TypeScript/Vite build. The API implementation sets the report-reader role and reads only the two snapshot-pinned `atlas_report.current_macro_economic_graph_*` views.
