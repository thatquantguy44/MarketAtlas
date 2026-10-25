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
| Readable but not-yet-onboarded economic-pipeline objects | 89 |
| Public agent runtime tables unavailable to source role | 9 |
| Catalog fingerprint | 709e2ebe613fe4b29deb657df7128bbebd3c3648f8da71c604820ee0f85448b7 |

The generated local catalog contains object type, estimated rows, select/write privilege, column-layout fingerprint, index-based key clues, and view-definition hash. It contains no source rows or view definition text and is git-ignored.

The source reader has zero-row read-probe access to 91 economic-pipeline relations/views. Only meta.fred_series and gold.fred_point_in_time are supported_live. The other 89 are discovered_not_onboarded and cannot be extracted or treated as supported without an explicit promotion review; the 9 public agent runtime tables remain unavailable_to_source_role.

## Remaining T-001 decisions

The technical inventory is complete for this configured environment. Source-owner assignment, redistribution rights, refresh ownership, and approval for any additional object remain human decisions. T-001 and AC-001 therefore remain partial rather than being represented as a completed release gate.
