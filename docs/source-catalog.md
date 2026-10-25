# MacroMedallion/EcoMedallion source catalog

MacroMedallion and EcoMedallion are interchangeable names for one locally selected upstream asset. The catalog is a metadata-only inventory of every discovered table, partitioned table, foreign table, materialized view, and view in the connected PostgreSQL database. It does not read source rows or retain view definitions.

Generate a local catalog with:

    PYTHONPATH=src python -m market_atlas database catalog \
      --output data/generated/source_catalog.json

The output is git-ignored because it reflects a local environment. It stores object/column metadata, select/write access, index-based key clues, hashes of column layouts and view definitions, support classification, and one catalog fingerprint. It never writes upstream objects.

## Contract registry and verification

[`../contracts/source_contracts.toml`](../contracts/source_contracts.toml) is the
tracked, non-secret registry for source interfaces that have an explicit
MarketAtlas contract. Each entry declares an accountable integration owner,
source-owner status, purpose, grain/business key, required columns, expected
column fingerprint, view fingerprint where applicable, temporal semantics,
rights/redistribution status, lifecycle state, and bounded adapter.

Generate and verify a fresh metadata-only catalog before activating or running a
live adapter:

```bash
PYTHONPATH=src python -m market_atlas database catalog \
  --output data/generated/source_catalog.json
PYTHONPATH=src python -m market_atlas database verify-contracts \
  --catalog data/generated/source_catalog.json
```

The verifier fails if a declared object is absent, has the wrong relation type,
lacks read access, has write access, fails its zero-row probe, is missing a
required column, or differs from its declared column/view fingerprint. It does
not read source rows or promote an undeclared object.

## Current catalog result

The 2026-10-25 catalog found 100 upstream relations and 31 MarketAtlas-owned relations. The source reader can execute zero-row probes against 91 economic-pipeline objects. Five are approved as `supported_live`:

| Object | Status | MarketAtlas support |
| --- | --- | --- |
| meta.fred_series | supported_live | Macro-series identity and metadata |
| gold.fred_point_in_time | supported_live | Point-in-time macro observation versions |
| gold.dim_series | supported_live | Current macro taxonomy and descriptive metadata |
| gold.release_calendar | supported_live | Scheduled macro release events at `(release_id, release_date)` grain |
| gold.v_source_coverage | supported_live | Current source-series coverage and freshness status |
| 86 additional economic-pipeline objects | discovered_not_onboarded | Readable for discovery, but not approved for extraction or use |
| 9 public agent runtime tables | unavailable_to_source_role | Deliberately excluded from the source role |

The complete local-run evidence is in the T-001 source catalog validation reports.

## Support states

| State | Meaning |
| --- | --- |
| supported_live | Has an approved read contract, required-column checks, a bounded adapter, manifest lineage, and validation evidence. |
| discovered_not_onboarded | Readable but not yet assigned an owner, grain, rights classification, and adapter contract. |
| unavailable_to_source_role | Discovered as metadata but not approved for the MarketAtlas source role; it must not be queried by adapters. |
| marketatlas_owned | Belongs to atlas or atlas_report, not to the upstream source catalog. |

## Promotion rule

An object moves to supported_live only after its owner approves access and intended use; its business grain/key, temporal/availability semantics, rights classification, required columns, and quality checks are documented; a bounded adapter uses only the approved interface; and schema-drift plus role-boundary tests pass. A catalog entry alone is never authorization to read, copy, or publish a source object.

T-004C validated the initial two FRED contracts on 2026-10-25 against catalog
fingerprint `5bfa333e909f483aeee4873511e1d2c68cf03b67ad8a50da0a8de3b1a51f12e4`.
T-004C.2 added and verified the three bounded macro-context interfaces against
catalog fingerprint `6dcaa1fc2c1881823bcde8d9e874d1b652cc76f55f2864c8f67143253ae843ab`.
The remaining 86 readable economic objects remain `discovered_not_onboarded`.
