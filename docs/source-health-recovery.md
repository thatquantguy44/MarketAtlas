# FRED source health and staged recovery

The authorized October 31, 2026 repair is complete for the approved MarketAtlas
source selection and observation window. Historical availability is now supported
for **267 FRED series / 127,907 versions**, compared with 94 / 35,576 before repair.
Current coverage/quality still includes 268 FRED series; the graph retains all
290 catalog entries and 11 concepts. The repaired observation window is
**2024-01-01 through 2026-10-31**. Older source rows are unchanged.

## What was repaired

- Observation requests now read every API page, including vintage-cap fallback
  and complete-history windows. Requests reject inconsistent counts, empty
  intermediate pages and excessive results rather than truncate silently.
- Real-time windows remain contiguous and the final interval stays open.
  Equal values across an unknown gap are not coalesced. Batches reserve one slot
  for FRED's boundary state under the 2,000-vintage cap; a live 2,001-state error
  established why that reservation is needed.
- Stale FRED observation periods override cadence skipping. Fresh FRED series and
  other providers retain their existing cadence rules. No upstream schedule was
  added; the change takes effect when the upstream pipeline runs.
- 169 formerly current-only series now have validated dates in the repaired
  window. Their canonical manifests and metadata enable vintage tracking; the
  existing private upstream config enables complete vintage history.
- Existing Home Sales (`EXHOSLUSM495S`) remains current-only: FRED explicitly reports
  that it has no ALFRED series. Its available 13 current observations were
  refreshed from September 2025 onward, preserving older records. Its 17 unknown-date
  rows in the broader selected window remain excluded from PIT ingestion.

The initial diagnosis found 181/268 upstream stale flags and 179 stale series last
skipped as not due. After repair, flags fell to **23**, with no age-rule mismatches
or unknown flags. All 23 latest observation periods match live FRED metadata.
They are provider-current series whose period ages exceed the existing rules,
including housing data with long publication lags. Thresholds were not relaxed.
This is a dated provider reconciliation, not a guarantee about later releases.

The report explains these as upstream age flags. Its separate “upstream ingestion
not verified” label reflects the optional full-job success marker, which remains
unconfigured; the bounded repair has independent audit evidence. MarketAtlas's
normal refresh still consumes PostgreSQL only, without launching upstream APIs.

## Diagnostics and evidence

```sh
PYTHONPATH=src .venv-dagster/bin/python -m market_atlas.source_health \
  --output data/generated/source-health/operator-check \
  --start 2024-01-01 --end 2026-10-31
```

Omit `--end` for today's New York date. The supplied view ages are independently
checked against its **source database date/timezone**. Output is confined to
ignored `data/generated/`. The manual Dagster job **`fred_source_health`** exposes
the same checks. Job success means diagnosis completed, not that all age flags
are clear. No additional schedule is enabled.

The tool verifies six publication contracts and two separately scoped
[diagnostic audit contracts](../contracts/source_health_contracts.toml), using
`marketatlas_source_reader`. It reads audit status/timing/counts, not raw errors
or source values, in batches of at most 25 approved IDs. Discovery is capped at
1,000 series; read-only sessions and statement timeouts remain enforced.

Private before/after diagnoses, staged captures, provider comparisons, source
backup counts, rollback proof and native run logs live under
`data/generated/source-health/authorized-repair/` and `post-repair/`.
[Initial diagnosis](../reports/t026-source-health-validation.md) and
[repair validation](../reports/t027-source-repair-validation.md) retain the scope,
counts, run IDs and known test limitations without exposing credentials or values.

## Upstream operator workflow

The separate checkout is
`pipelines/fred-bronze-to-gold-pipeline`, branch
`fix/fred-pagination-source-recovery`. Its
`scripts/repair_marketatlas_fred.py` supplies explicit `stage`, `apply` and
`restore` commands; see that repository's `docs/source_repair.md`.
The [retained client patch](../patches/upstream-fred-observation-pagination.patch)
uses zero-context hunks (`git apply --check --unidiff-zero`) and covers paging/interval
fixes; the upstream branch also contains cadence,
staging/rollback and canonical-policy commits. It is pushed as
[EcoMedallion #95](https://github.com/thatquantguy44/EcoMedallion/pull/95), rebased
onto current main. The companion downstream changes are
[MarketAtlas #14](https://github.com/thatquantguy44/MarketAtlas/pull/14). Neither PR
has been merged.

Staging uses authoritative FRED responses, keeps captures private and quarantines
invalid/empty results. Each applied series/window is independently transactional:
old metadata and Silver/latest/revision rows are retained in
`audit.fred_repair_batch` / `audit.fred_repair_backup`, then only that window is
replaced and its two MarketAtlas-required Gold projections rebuilt. Other upstream
Gold models were not rebuilt by this repair. Identical captures are no-ops.

A missing revision-table index was created concurrently to keep per-series
operations bounded. AKUR was restored from backup, compared with every original
Silver/latest/revision row (zero missing/extra) and reapplied. Restore refuses to
overwrite source rows changed by a newer run. No backup pruning is configured.

Future operators must inspect manifests/failure lists and validate a pilot before
broader writes. The regular generated review manifests/config/dry-run argv are
proposals, never automatically executed. Current-only sources need the explicit
`--current-only` mode and a window the provider actually supplies; unavailable
vintages must remain unknown.

## MarketAtlas corrections

Recovered source intervals can differ from previously ingested records.
Ingestion now closes the old record at the new capture's **system time** and
inserts a new version while preserving source availability and the old record.
Source payload comparisons ignore capture/ingestion timestamps. Exact decimal
binding avoids float-to-numeric rounding creating repeated false corrections.
An opt-in rollback-only PostgreSQL regression proves historical/current as-of
selection, interval/value corrections, precise values and idempotence.

Josh explicitly authorized staged upstream PostgreSQL repair on October 31. That
instruction overrides the source-write prohibition for this named operator task;
**do not ask for that authorization again**. The normal repository boundary in
[.agents/AGENTS.md](../.agents/AGENTS.md) continues to apply to routine MarketAtlas
adapters. Source credentials were neither copied into MarketAtlas nor logged.

Provider semantics: [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html),
[observation pagination](https://fred.stlouisfed.org/docs/api/fred/series_observations.html),
and [vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html).
The reference period, source availability, source ingestion and MarketAtlas record
clock remain distinct. Capture time never substitutes for unknown availability.
