# T-027 — Authorized staged source repair

Completed October 31, 2026 at restricted-local scope, with explicit user
instruction **Authorize staged upstream repair**. MarketAtlas branch:
`feat/source-freshness-vintages`; upstream branch:
`fix/fred-pagination-source-recovery`, based on `e6cbe645`.

## Source fixes and rollout

The upstream client now paginates observation rows in ordinary/fallback/history
requests, validates page completeness, preserves open and contiguous real-time
intervals, and reserves a boundary-state slot under FRED's vintage cap. Stale FRED
periods override cadence skipping without changing other providers' cadence.

Three bounded pilots applied: AKUR 65 versions, GDP 45 and ANFCI 10,115.
AKUR batch `4885f6cf48b942b0b0b32d5130ec8593` was restored and compared against
all backed-up Silver/latest/revision rows: zero missing or extra rows and the
original disabled-vintage flag. It was reapplied as
`fe2c8519e3584abb954c34a8428350c5`.

The expanded union contained 227 stale/current-only candidates. After retrying
live vintage-cap boundary failures, **226 series / 102,185 dated versions** passed
staging and applied (223 new applies plus three pilot no-ops). Existing Home Sales
has no ALFRED history according to FRED; an explicit current-only stage refreshed
13 available periods from September 2025 onward. Older rows remain intact and
its availability dates remain blank. The source ledger has **227 applied series
batches / 102,198 rows**, plus the restored pilot. Backup tables retain 45,315
Silver, 37,049 latest and 35,658 revision-stat rows, including the restore/reapply
copies; these are backup row counts, not distinct observations.

All 169 recoverable formerly current-only policies are enabled in ten canonical
manifest files. The existing private config enables complete history without
copying its credential. Existing Home Sales retains its disabled-vintage policy.
Only the 2024–October 2026 window and the two serving projections used by
MarketAtlas were repaired. This is not full-history or all-Gold-model recovery.

## Reconciliation and downstream results

| Measure | Before | After |
| --- | ---: | ---: |
| PIT-eligible FRED series | 94 | 267 |
| Eligible observation versions | 35,576 | 127,907 |
| Current-only FRED series | 170 | 1 |
| No-window series | 4 | 0 |
| Upstream age flags | 181 / 268 | 23 / 268 |
| Stale series last skipped | 179 | 0 |
| Page-limit-suspected series | 4 | 0 |

All 23 remaining flagged periods match live FRED metadata. Their age flags
reflect existing period-age rules/publication lag; no thresholds were loosened.
The graph remains 290 series / 11 concepts; current context/quality remains 268.

Full native Dagster refresh `af04ae7b-69bb-42dc-a25f-fc797aea2a65` succeeded,
seeing 127,907 observations and inserting 92,584 versions, including 253 tuple
corrections. The first repeat exposed float-to-numeric rounding causing 234
repeated corrections. Exact Decimal binding fixes this; the intervening historical
records are retained. Native normalization refresh
`3f43b2e2-2975-4b8b-8d25-7991e1871672` succeeded, with one successful retry of a
30-second context query. The final replay, with capture time advanced, checked all 127,907 versions and
inserted/corrected **zero**; its exact result is retained in `final-idempotence.json`.
The final validated pack is
`data/generated/powerbi-real/be93f9085a543d44b84c962f1d8af96bd4e88d1fa53aecabe691adf2d597befc/`.
A successful Dagster status alone was not treated as proof of idempotence.

The browser app retains its existing identity/URL and explains upstream period-age
flags. Browser checks verified the 23/268/zero-unknown panel, catalog 290/11,
268 revision summaries/evidence rows, AKUR filtering to one matching evidence row,
filter reset and zero console errors. The report was rebuilt through its existing
runtime, without cloud publication or native Power BI claims.

## Checks and limitations

- MarketAtlas: 120 tests, 115 passed/five opt-in database skips. The explicit
  rollback-only correction regression passed both tests, including as-of history,
  changed intervals/values and exact-precision replay.
- Upstream PR-base full suite: 1,531 passed, one skipped, **four pre-existing failures**.
  Those same failures reproduce on clean `e6cbe645`: three Spark schema-source
  parser assertions and missing `mmkt_rate_snapshot` in the Power BI catalog.
  They are retained as unrelated findings, not reported as a clean full-suite pass.
- Targeted client, cadence, repair and manifest checks passed. Ruff, repository
  commit hooks, document links and diff checks are retained with the handoff.
- All source captures, provider comparisons, backup counts, authorization and
  detailed logs stay ignored. No external alerts, source-credential copying,
  broader Gold rebuild, new upstream scheduler, remote merge or public data
  publication occurred. T-015/AC-009 remains open.

[Recovery runbook](../docs/source-health-recovery.md) describes the continuing
role boundary, current-only exception and rollback procedure.

Upstream local commits: `647f086` (client/validity), `7c0deae` (cadence),
`e3e48e3` (staged recovery/restore), `5f416b4` (169 policies). All commit hooks
passed. These identify the executed repair. The four commits were subsequently
rebased onto main `9ca1694` as `5d4fc57`, `d9eca40`, `a7685fa`, `7ed2af5` for
[EcoMedallion #95](https://github.com/thatquantguy44/EcoMedallion/pull/95).
The full suite on that PR base passed 1,531 tests with one skip and the same four
baseline failures. Downstream changes are in
[MarketAtlas #14](https://github.com/thatquantguy44/MarketAtlas/pull/14).
Both branches are pushed; neither PR is merged.
