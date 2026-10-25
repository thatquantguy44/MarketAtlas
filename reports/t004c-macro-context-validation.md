# T-004C.2 macro-context adapter validation

Date: 2026-10-25

## Scope

This slice promotes three bounded, read-only source interfaces for internal
macro-context extraction. It does not load their output into `atlas` or publish
it through `atlas_report`.

## Contracted interfaces

| Object | Grain | Temporal interpretation |
| --- | --- | --- |
| `gold.dim_series` | `series_id` | Current taxonomy/descriptive metadata only |
| `gold.release_calendar` | `release_id`, `release_date` | Scheduled event date plus source `fetched_at` |
| `gold.v_source_coverage` | `source`, `series_id` | Current coverage/freshness only |

The release-calendar grain was verified: 42 rows and 42 distinct
`(release_id, release_date)` pairs. Its `release_id` alone is not unique.

## Commands

```bash
PYTHONPATH=src python -m market_atlas adapter verify-context
PYTHONPATH=src python -m market_atlas adapter extract-context \
  --context-config configs/context_pilot.toml \
  --output data/generated/macro_context_pilot.json
```

## Result

The verifier returned `valid`: all five source contracts passed the metadata
gate, each selected context interface had required columns, the source session
was read-only, and the reader had no source-write privileges. The catalog
fingerprint was
`6dcaa1fc2c1881823bcde8d9e874d1b652cc76f55f2864c8f67143253ae843ab`.

The bounded extract used the configured three FRED identifiers and the
2026-10-01 through 2026-12-31 release window. It produced 3 series-taxonomy
records, 42 release events, and 3 source-coverage records under input-selection
hash `563dfa0a4b2557dbf6133dd24a139d2adf5852a95b3b0f14a7f63e2b99ae16cf`.

## Boundary retained

The new context records remain local generated output only. They are classified
as `restricted_pending_rights`, do not imply historical point-in-time support,
and are not exposed to the browser or inserted into reporting views.
