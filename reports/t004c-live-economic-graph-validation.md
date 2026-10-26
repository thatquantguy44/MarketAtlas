# T-004C.4 live economic graph validation

Run date: 2026-10-25. This local evidence records schema, publication, API, and frontend validation without credentials or source-row payloads.

## Published graph

Migration `010_macro_economic_graph_publication.sql` creates a current-only taxonomy projection and separate `macro_economic_graph` report publication. The publisher uses the approved `gold.dim_series.econ_category` taxonomy field to create source-backed `measures` assertions only:

| Node/edge kind | Count |
| --- | ---: |
| Macro-series nodes | 3 |
| Economic-concept nodes | 3 |
| `macro_series → measures → economic_concept` edges | 3 |

The local publication was snapshot `0d7643da-b38e-5e41-b09a-2195cf02f5d7`, with 9 snapshot rows and SHA-256 `4c16b4c8f419f2f9b0c9e43eefad2f0b28646e853b026004b2d26e7f4d5398fa`.

## Boundary and interface validation

```text
PYTHONPATH=src python -m market_atlas economic-graph publish --config configs/local.toml --input data/generated/macro_context_pilot.json
PYTHONPATH=src python -m market_atlas report serve-macro-economic-graph --config configs/local.toml
cd frontend && npm test && npm run build && npm run dev -- --port 5188
```

The report API endpoint `/api/v1/macro-economic-graph` returned the publication, snapshot identity, six nodes, and three edges. Its implementation sets `marketatlas_report_reader`, sets the database session read-only, and selects only `atlas_report.current_macro_economic_graph_node` and `atlas_report.current_macro_economic_graph_edge`. The Vite `/api` proxy returned the same payload for the React live mode. The Python suite passed 44 tests; frontend tests passed 4 tests and the production build completed.

## Semantic guard

The live visualization is an approved current source-taxonomy graph. It does not query source schemas from the browser, create a point-in-time taxonomy claim, expose release/coverage as graph edges, or imply causal or measured-sensitivity relationships.
