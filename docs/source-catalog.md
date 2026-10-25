# MacroMedallion/EcoMedallion source catalog

MacroMedallion and EcoMedallion are interchangeable names for one locally selected upstream asset. The catalog is a metadata-only inventory of every discovered table, partitioned table, foreign table, materialized view, and view in the connected PostgreSQL database. It does not read source rows or retain view definitions.

Generate a local catalog with:

    PYTHONPATH=src python -m market_atlas database catalog \
      --output data/generated/source_catalog.json

The output is git-ignored because it reflects a local environment. It stores object/column metadata, select/write access, index-based key clues, hashes of column layouts and view definitions, support classification, and one catalog fingerprint. It never writes upstream objects.

## Current catalog result

The 2026-10-25 catalog found 100 upstream relations and 31 MarketAtlas-owned relations. The source reader can execute zero-row probes against 91 economic-pipeline objects. Only two are approved as supported_live:

| Object | Status | MarketAtlas support |
| --- | --- | --- |
| meta.fred_series | supported_live | Macro-series identity and metadata |
| gold.fred_point_in_time | supported_live | Point-in-time macro observation versions |
| 89 additional economic-pipeline objects | discovered_not_onboarded | Readable for discovery, but not approved for extraction or use |
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
