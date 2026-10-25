# T-004C.1 source-contract verification

Date: 2026-10-25

## Scope

This validation covers the registry and promotion gate only. It neither reads
source rows nor activates an additional upstream object.

## Commands

```bash
PYTHONPATH=src python -m market_atlas database catalog \
  --output data/generated/source_catalog_t004c_verified.json
PYTHONPATH=src python -m market_atlas database verify-contracts \
  --catalog data/generated/source_catalog_t004c_verified.json
```

## Result

The metadata-only catalog completed in a read-only source session. It found 100
upstream objects, 31 MarketAtlas-owned objects, 89
`discovered_not_onboarded` economic objects, 9 unavailable public agent tables,
and 2 `supported_live` contracts. The catalog fingerprint was
`5bfa333e909f483aeee4873511e1d2c68cf03b67ad8a50da0a8de3b1a51f12e4`.

`database verify-contracts` returned `valid` with no errors for:

- `meta.fred_series`
- `gold.fred_point_in_time`

The verifier confirmed required-column and schema/view fingerprints, read-only
access, and zero-row read probes for both declarations in
[`../contracts/source_contracts.toml`](../contracts/source_contracts.toml).

## Boundary retained

No additional object was promoted. The 89 readable economic objects require
their own owner approval, rights review, grain/temporal contract, bounded
adapter, and validation evidence before their lifecycle can become
`supported_live`.
