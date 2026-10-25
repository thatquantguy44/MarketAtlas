# T-001 source catalog validation

Date: 2026-10-25. MacroMedallion and EcoMedallion are interchangeable names for one locally selected upstream asset. This run used only the configured read-only source role.

## Command

    PYTHONPATH=src python3 -m market_atlas database catalog \
      --output data/generated/source_catalog.json

## Result

| Measure | Result |
| --- | --- |
| Catalog status | cataloged_read_only |
| Upstream relations/views inventoried | 100 |
| MarketAtlas-owned relations identified | 31 |
| Approved live source interfaces | 2 |
| Other upstream relations unavailable to source role | 98 |
| Catalog fingerprint | 12f56528b205480484934a5dcbff53d242bf6b7f1f54456fdcce6d291f7c4960 |

The generated local catalog contains object type, estimated rows, select/write privilege, column-layout fingerprint, index-based key clues, and view-definition hash. It contains no source rows or view definition text and is git-ignored.

The source reader is authorized only for meta.fred_series and gold.fred_point_in_time; they are supported_live. The other 98 upstream objects are cataloged as unavailable_to_source_role and cannot be queried or treated as supported without an explicit promotion review.

## Remaining T-001 decisions

The technical inventory is complete for this configured environment. Source-owner assignment, redistribution rights, refresh ownership, and approval for any additional object remain human decisions. T-001 and AC-001 therefore remain partial rather than being represented as a completed release gate.
