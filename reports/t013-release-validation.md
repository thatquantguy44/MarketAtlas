# T-013 release validation and performance checks

Run date: 2026-10-26. This report records aggregate results only: no credentials, connection coordinates, source-row payloads, or host name are retained.

## Command and envelope

```text
PYTHONPATH=src python -m market_atlas release validate \
  --config configs/local.toml --samples 20 \
  --output data/generated/t013_release_validation.json
```

The gate uses the deterministic `synthetic-v1` fixture (SHA-256 `15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da`) and the published current macro catalog. The environment was macOS/Darwin 25.5.0 on arm64, Python 3.13.9, with 15 logical CPUs reported. Query timing used one warm, local PostgreSQL connection under `marketatlas_report_reader`, one unmeasured prepared-statement warm-up per case, and did not clear operating-system or database caches.

## Results

| Check | Result |
| --- | --- |
| Source, writer, and report-role boundaries | Passed; source write/create and writer upstream access remained denied |
| Source contracts | Passed for all five approved live objects; no drift errors |
| Graph, temporal, observation, context, and numerical fixture guards | Passed |
| Reproducible fixture publication | Passed; fixture snapshot built/published with 32 serving rows |
| Injected publication failure and recovery | Passed; failed build remained unpublished with zero serving rows and the prior pointer unchanged |
| Fixture reporting/provenance grain | Passed; 15 nodes, 14 relationships, 3 contexts, 24 bounded paths, and 49 provenance rows for the pinned fixture snapshot |
| Live catalog surface | Passed; 290 approved series and 11 concepts were visible from the immutable macro graph snapshot |
| Fixture build target | 0.188182 seconds, below the 300-second target |
| Prepared catalog-summary query | 20 samples; p95 0.000161 seconds, below the 2-second target |
| Prepared largest-category neighborhood query (limit 50) | 20 samples; p95 0.000964 seconds, below the 2-second target |

The timing result is a local-envelope measurement, not a production capacity or concurrency guarantee. The results are intentionally limited to the documented fixture and current 290-series catalog scale.

## Defect found and corrected

The first T-013 attempt identified that the fixture reporting validator counted provenance from all independently published surfaces. Once the live macro graph publication existed, this made a valid fixture snapshot appear unpinned. The data and publication pointer were correct; the validator was corrected to restrict provenance checks to the fixture publication's selected snapshot. The focused report validation and the complete release gate then passed.

## Remaining release gaps

This evidence does not complete public release review, Power BI acceptance, a clean-room contributor walkthrough, named refresh/recovery ownership, source-owner/redistribution decisions, or production workload testing. Those remain explicit work for T-014 and the relevant acceptance criteria.
