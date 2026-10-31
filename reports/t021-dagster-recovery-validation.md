# T-021 — Native Dagster recovery

Date: 2026-10-30 (New York; captures are October 31 UTC).
Scope: recover a failed local daily refresh without rerunning its completed prefix.

## Change

Dagster parent checkpoints now restore the original run date, selection windows,
completed prerequisites and SHA-256-verified captures into a new child directory.
Captures are copied, not linked, and parent files are preserved. Run tags locate
the checkpoint. A subsequent failure can resume from that child with root lineage.

Recovery requires a contiguous stage selection, version-2 checkpoint, intact plan
and captures, matching source/target/report identities, unchanged publication
pointers, an acquired database advisory lock and a successful fresh source-contract
preflight. A downstream-only launch without a parent fails with actionable guidance.
Legacy checkpoints require a fresh full run. Independent manual publishers still
must not run concurrently: they do not participate in the orchestration lock.

## Validation

- Full optional-runtime suite: 100 tests, 96 passed, four opt-in database skips.
- Core-only `python3 -S` suite: 100 tests, 89 passed, 11 optional/database skips.
- `tests/test_orchestration_recovery.py`: original-window/input preservation,
  parent immutability, modified/missing/legacy inputs, missing prerequisites,
  database/publication guards, failed preflight, chained recovery, actual native
  `execute_job` + `ReexecutionOptions.from_failure`, and parentless downstream refusal.
- Ruff and shell syntax checks passed.

Final live PostgreSQL check used the actual local Dagster instance, source-reader,
MarketAtlas writer and report-reader boundaries. A controlled `ValueError` was
injected immediately before graph publication; no upstream API ingestion ran.

| Run | Result |
| --- | --- |
| Parent `1600569b-a641-4e30-aaeb-8815feef00b0` | Seven stages complete, deliberate failure at `publish_graph` |
| Child `86359104-cf40-4c3b-9667-c21fa760b3ac` | Native re-execution ran only the six remaining stages; complete |

The child revalidated source contracts and exported eight tables: 301 macro
nodes, 290 graph edges/provenance rows, 38 context/provenance rows, three quality
summaries/provenance rows and three publication records. Upstream freshness stayed
`not_verified`. Both run checkpoints and sanitized execution logs are retained
under ignored `data/generated/`; the final pack is
`data/generated/powerbi-real/fb860c24507b9b0fdd66a449ba49b64d0457d2887558fd38d0e68332ba1d170d/`.

This is local recovery evidence. It does not enable the stopped daily schedule,
install a production Dagster service, add alerts, or invoke Power BI refresh.
