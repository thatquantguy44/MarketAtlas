# T-004C.3 macro-context publication validation

Run date: 2026-10-25. This report records a bounded local integration result; it contains no credentials, connection details, or source-row payloads.

## Scope

Migration `009_macro_context_publication.sql` created dedicated `atlas` current-context tables and the snapshot-pinned `atlas_report.current_macro_source_context` report view. It does not modify MacroMedallion/EcoMedallion schemas.

The publisher accepts only a context extract that passed the tracked source-contract gate and whose selection and source-row SHA-256 values match the payload. It requires existing T-004B macro-series identities, then writes taxonomy, release, and coverage inputs with their immutable `atlas.input_manifest` lineage.

| Source interface | Stored semantic | Temporal label | Live rows |
| --- | --- | --- | ---: |
| `gold.dim_series` | Series taxonomy | `current_only` | 3 |
| `gold.release_calendar` | Scheduled release event | `scheduled_event` | 42 |
| `gold.v_source_coverage` | Coverage/freshness | `current_only` | 3 |

`gold.release_calendar.release_id` is numeric in the live source and is canonicalized to a text identifier inside MarketAtlas while retaining the source grain `(release_id, release_date)`.

## Commands and outcome

```text
PYTHONPATH=src python -m market_atlas database migrate --config configs/local.toml
PYTHONPATH=src python -m market_atlas adapter extract-context --config configs/local.toml --context-config configs/context_pilot.toml --output data/generated/macro_context_pilot.json
PYTHONPATH=src python -m market_atlas context publish --config configs/local.toml --input data/generated/macro_context_pilot.json
PYTHONPATH=src python -m market_atlas context validate --config configs/local.toml --input data/generated/macro_context_pilot.json
```

The migration applied `009_macro_context_publication.sql`. Publication produced 48 rows in snapshot `da11dbee-200d-59cb-9729-67994db2bbf3`, with output SHA-256 `f6fc805d35adbe40c91ba2511368f5e20c85a2743931332b657b148c1505da1e`. Validation confirmed the exact 3/42/3 grain, 48 provenance rows, one input manifest per context kind, the required temporal labels, and 48 rows visible through `marketatlas_report_reader`. A repeat publish reused the published snapshot without duplicating rows.

## Boundary preserved

The report publication is named `macro_context`, separate from the fixture/default publication. The implementation does not claim taxonomy or coverage point-in-time history, does not create a browser-to-source connection, and does not write to `meta`, `bronze`, `silver`, `gold`, or `audit`.
