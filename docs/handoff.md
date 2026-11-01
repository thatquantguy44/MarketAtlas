# MarketAtlas — Handoff

Updated: 2026-11-01. This is an early implementation handoff, not a completed pilot or production release.

## Start here next session

**Completed T-030 checkpoint (2026-11-01):** Josh requested shipping the analytics
foundation and adding the three browser views. Current branch remains
`feat/macro-relationship-analytics`, from main `9548eef`. Foundation commit
`bd607df` is pushed; [PR #15](https://github.com/thatquantguy44/MarketAtlas/pull/15)
contains the foundation and separate browser change. Check actual GitHub state
for the final head/CI; no merge was requested. Both foundation workflows passed.

Read [browser runbook](report-frontend-runbook.md#relationship-research-views),
[T-030 spec](t030-browser-analytics-spec.md) and
[evidence](../reports/t030-browser-analytics-validation.md). The existing report
http://127.0.0.1:60114/ retains app
`dashboard:b31d5d91-39e6-4d2a-8719-4888de544244` and its four prior tabs, plus
**Relationship research**. It shows heatmap, dispersion timeline, divergence
ranking and exact pair-window/source evidence. Defaults are Treasury yields/latest
evaluation. Named per-group date/pair scopes restore from view links. Monthly
missing results remain unavailable; the latest complete date requires an
explicit selection. No predictive claim or source repair was added.

The attached research pack remains
`a56bd8f7591762d8664a7c03eefe4e0d9406469d421c56808f48c6cf589d56d1` (cutoff
October 31), independent of publication pack
`be93f9085a543d44b84c962f1d8af96bd4e88d1fa53aecabe691adf2d597befc`.
Browser queries retain 2,526 relationships, 808 dispersions, 2,458 nodes, 2,458
window records and 3,512 cached transformed point states. Validated attachment
uses `scripts/refresh-browser-report.py --analytics-pack ...`; explicit
`--update-content` installs tracked authored views. Normal publication-only
refreshes preserve all research queries with their original cutoff. This was
verified on the real report, with hash proof under ignored
`data/generated/macro-analytics/browser-integration-proof.json`.

Full Python suite: 148 tests, 143 passed/five opt-in database skips; core `-S`:
134 passed/14 optional/database skips. Four Node cases pass and run in CI.
Changed Python lint/shell/diff checks pass; eleven untouched baseline lint
findings remain separate. Chrome normal and 390×844 checks pass, including
scope/reset, historical date, source preview, pair action, null states and reload
restoration. Mobile heading/tooltip issues were repaired and rechecked; normal
viewport restored. No captured browser warnings/errors. Final report authoring
status is complete and the research tab is open. Screenshot/logs/proofs remain
ignored under `data/generated/macro-analytics/`.

**Exact next engineering task:** review PR #15 and final CI; merge only on Josh's
request. Next product priority is adding macro preparation/build/validation to
the existing Dagster workflow and refreshing the report only after the research
pack passes, preserving the previous research/report on failure. No new schedule
or upstream API ingestion was added. T-015/AC-009 remains open without Power BI
access; do not repeatedly request it.

**Historical completed T-028/T-029 checkpoint (2026-10-31):** Josh requested comparable
macro series followed by analytical relationships on a new branch. Current branch
is `feat/macro-relationship-analytics`, from merged main `9548eef` (MarketAtlas
#14). EcoMedallion #95 is also merged. The new branch is local; no commit, push or
new PR was requested or created in this session. Review actual Git state before
shipping. Source repair is complete at its prior bounded scope; do not repeat it.

Read [macro analytics runbook](macro-analytics.md),
[method spec](t028-t029-macro-analytics-spec.md) and
[evidence](../reports/t028-t029-macro-analytics-validation.md). New CLI commands
are `analytics prepare-macro`, `build-macro` and `validate-macro`; settings live in
`configs/macro_analytics.toml`. Ten approved FRED series in inflation, labor
conditions and Treasury-yield groups use explicit metadata/transforms/orientation,
date-cutoff vintage selection, conservative grids and fixed sample rules.
No upstream writes, APIs, dependency/schema changes or existing report/schedule
changes were made.

Final live capture: 19,963 versions and 808 evaluation panels. Monthly dated
history is usable from 2010. Each Treasury series has 3,651 undated older rows;
they remain excluded, with dated history beginning in January 2024. Five monthly
members mark October 2025 missing; this also prevents November's adjacent change.
Do not bridge this gap, infer dates or relax thresholds to display a number.
Current affected monthly windows/baselines stay unavailable; latest Treasury
results are supported.

Final pack: 2,526 pair/date rows (2,264 supported), 808 dispersion rows (640
supported), 2,458 node/date rows and ten eligibility rows. Local summary:
`data/generated/macro-analytics/validation-summary.json`. Authoritative pack:
`data/generated/macro-analytics/packs/a56bd8f7591762d8664a7c03eefe4e0d9406469d421c56808f48c6cf589d56d1/`.
Preparation ID: `ddb682876521e92a3393ff161c4f76ee4c2e0e69fedd5b6b89b323220b4801e1`.
Exact retained-input replay reused the same pack/manifest. The independent
`scripts/verify-macro-analytics.py` checked 127,624 transformed points, all 2,264
supported correlations/distances, 1,957 z-scores and 640 dispersions against raw
source histories using 50-digit Decimal arithmetic and tolerance `1e-10`.

Final suite: 143 tests, 138 passed/five opt-in database skips. Core `python -S`:
129 passed/14 optional/database skips. All 23 new tests and changed-file Ruff
checks pass. Whole-repository Ruff has 11 baseline findings in five files proved
identical to merged main; retain these as separate work. No Power BI execution,
predictive/causal validation, historical taxonomy or MarketAtlas historical
possession is claimed. These are separate private research file packs, not new
report publications or an added daily job.

**Exact next engineering task:** review the T-028/T-029 diff; commit/push/create
a PR only when requested. Next product priority is browser consumption of the
validated pack: relationship heatmap, dispersion timeline and node-divergence
ranking with explicit unavailable states and source evidence. Do not claim these
views exist yet. T-015/AC-009 remains open; Josh lacks Power BI access.

**Historical completed T-026/T-027 checkpoint (2026-10-31):** Josh explicitly authorized
staged writes in the named upstream checkout. Repair is complete for the approved
2024-01-01–2026-10-31 window. **Do not ask for that permission again.** Normal
MarketAtlas adapters remain read-only; source-owner writes used the separate
upstream operator workflow. Primary branch: `feat/source-freshness-vintages`,
from main/merged PR #13 `e6aa4d2`. Upstream branch:
`fix/fred-pagination-source-recovery`, base `e6cbe645`, local commits
`647f086` paging/intervals, `7c0deae` stale gating, `e3e48e3` staged repair/restore,
`5f416b4` validated policies. Those hashes identify the executed repair. For PR
review, the four upstream commits were rebased onto main `9ca1694` without
conflicts: `5d4fc57`, `d9eca40`, `a7685fa`, `7ed2af5`. Both branches are pushed;
neither is merged. Paired PRs: [MarketAtlas #14](https://github.com/thatquantguy44/MarketAtlas/pull/14)
and [EcoMedallion #95](https://github.com/thatquantguy44/EcoMedallion/pull/95).

Read [repair runbook](source-health-recovery.md) and
[T-027 evidence](../reports/t027-source-repair-validation.md). The 227-candidate
union produced 226 dated series / 102,185 staged versions plus a 13-period
current-only Existing Home Sales refresh. FRED reports no ALFRED series for
`EXHOSLUSM495S`; its 17 blank-date rows in the broader window remain excluded from
PIT. The source ledger has 227 applied batches plus the restored pilot. All
original affected Silver/latest/revision rows and metadata remain in
`audit.fred_repair_backup` / `audit.fred_repair_batch`. AKUR restore matched every
backup row, then reapplied. Ten canonical manifest files enable 169 policies;
the existing private upstream config enables complete vintage history. Other
Gold models and observations before 2024 were not rebuilt.

New PostgreSQL eligibility: **267 series / 127,907 versions**, current coverage/
quality 268, graph 290 series / 11 concepts. Age flags fell 181 → 23 with zero rule
mismatches or unknown flags. All 23 latest periods match live FRED metadata;
these are period-age/publication-lag cases, not a remaining missing-ingestion
queue. Source flags are preserved and the browser explains their meaning.

Full native repair refresh `af04ae7b-69bb-42dc-a25f-fc797aea2a65` succeeded;
subsequent replay exposed float-to-numeric rounding. Exact Decimal binding now
preserves precision and avoids false repeated corrections. Original/intervening
system-time records remain retained. Final normalization/report run
`3f43b2e2-2975-4b8b-8d25-7991e1871672` succeeded after one context-query retry.
The final independent replay checked all 127,907 versions and inserted/corrected
**zero**, with capture time advanced. Private proof is
`data/generated/source-health/authorized-repair/final-idempotence.json`.
Final validated pack:
`data/generated/powerbi-real/be93f9085a543d44b84c962f1d8af96bd4e88d1fa53aecabe691adf2d597befc/`.
The existing app/URL remain intact. Browser checks passed the 23/268/zero-unknown
panel, 290/11 catalog, 268 quality rows, AKUR summary/provenance filter/reset and
zero console errors. No cloud publication occurred.

MarketAtlas: 120 tests, 115 passed/five opt-in database skips, plus both tests in
the explicit rollback-only correction regression passed (history/as-of/value/
interval/exact precision/idempotence). Upstream PR-base full suite: 1,531 passed, one
skipped and four **pre-existing** failures, reproduced against clean HEAD:
three Spark-schema parser assertions and missing mmkt_rate_snapshot catalog entry.
Source commit hooks passed. Detailed captures, audits, provider comparisons and
logs remain ignored under `data/generated/source-health/authorized-repair/`.

Dagster remains supervised locally at port 3001 with the existing daily 18:30 New
York schedule; no upstream API schedule was added. `fred_source_health` is a manual
read-only diagnostic job. Its successful completion does not certify all age flags
clear. The generic upstream-success marker is still unconfigured; do not equate
that UI label with the separately verified operator repair.

**Exact next engineering task:** review the paired PRs and their CI/validation.
Merge only when requested. Retain the four baseline upstream test findings as
separate work. T-015/AC-009 remains open; the user lacks Power BI access,
so do not repeatedly request it. Broader BLS/ECB adapters and analytical series
exploration remain later work, not part of this completed source repair.

**Historical T-026 diagnosis checkpoint (2026-10-31):** user requested freshness investigation
and vintage recovery. Work is local/uncommitted on `feat/source-freshness-vintages`,
from merged PR #13 / main `e6aa4d2`. PR #13's two GitHub workflows passed. The prior
report/publications are retained; upstream warehouse and source checkout are unchanged.

Read [source-health recovery](source-health-recovery.md) and
[T-026 evidence](../reports/t026-source-health-validation.md). Diagnostics verified
eight read-only contracts (six publication + two separate audit contracts).
Of 268 FRED series, 181 have stale reference-period flags; all match their rules.
Latest attempts for 179 stale series were skipped as not due. Across all selected
series, 209 latest attempts were skipped and 59 succeeded. The latest broader
upstream run was partial (104 succeeded/two failed); do not equate its totals with
MarketAtlas coverage. No source-age thresholds were loosened.

All 170 blank-vintage series have `vintage_enabled = false`: normalization
intentionally blanks dates. There are 35,433 undated versions in the selected
window, 94 dated series and four with no window observations. Selection now labels
current-only policy explicitly while retaining PIT exclusion. For each of the four
financial-conditions series, the last successful upstream extract returned exactly
100,000 rows. The inspected client does not paginate observation rows. A proposed
upstream patch and API fixtures passed 26 targeted tests in an isolated copy and
`git apply --check`; the original source hash is unchanged.

Read-only FRED API probes recovered 65 dated AKUR versions through September 2026
and 10,115 dated ANFCI versions through October 23. They remain private, unpromoted
provider captures; no PostgreSQL repair or broader recovery is claimed. The staged
181-series polling and 170-series vintage review manifests validate with the
upstream loaders. Pilot dry-run argv disable skipping/notifications and never execute
automatically. Source-writer rollout needs the source-owner decision in the runbook.

Manual Dagster job `fred_source_health` passed live as
`6399f461-aded-4d0f-bf83-593d330cb372`; output is under
`data/generated/source-health/<run-id>/`. The existing daily schedule was not changed.
Final MarketAtlas suite: 118 tests, 114 passed/four opt-in database skips.
Ruff and diff checks pass. Generated evidence remains ignored.

**Exact next engineering task:** Josh / source owner confirms the canonical
upstream checkout and explicitly authorizes applying the reviewed patch and staged
source repairs, which write outside MarketAtlas's read-only source boundary.
Start with the generated dry-run pilots, validate source counts/intervals, preserve
current-only rows under an explicit replacement policy, then approve bounded write
rollout and rerun MarketAtlas. Do not use capture/ingestion time as availability.
T-027 is pending; T-015/AC-009 remains open without requesting unavailable Power BI access.

**Historical T-023–T-025 checkpoint (2026-10-30):** work is on
`feat/automated-report-refresh`, created from merged main `f2ea0d8` (PR #12).
This checkpoint is prepared for branch review; use Git and the branch PR for the
final commit and remote state. The 14-stage pipeline now updates the existing
browser report after pack validation, preserving its app ID/URL and prior build
on failure. Checkpoint v3 includes the frozen series selection; older checkpoints
need a fresh full run. Read [automation/series evidence](../reports/t023-t025-automation-series-validation.md).

The macOS user-login Dagster service is installed and verified at
http://127.0.0.1:3001/. Manage it with `scripts/dagster-service.sh`.
The existing daily 18:30 New York schedule was found RUNNING and its state was
retained; next verified tick: 2026-10-31 at 18:30 EDT. Scheduler/run-coordinator
heartbeats had no errors. A normal runtime-directory Node supervisor avoids the
failed direct shell launch from `Documents`; no privacy/security settings or
source credentials were changed/copied. This is a supervised local pilot: the
Mac must be running/logged in and PostgreSQL reachable. See [local automation](local-automation.md).

The user selected **all eligible series already in PostgreSQL**. Within the
approved 290-series catalog, discovery admits **94 point-in-time series / 35,576
observation versions** and an independent **268-series current coverage/quality**
selection. 170 series have blank source-vintage dates, four have no usable window
observations, and 22 are BLS/ECB entries outside the FRED observation adapter.
The graph retains all 290 series/11 concepts. [Eligibility rules](series-coverage.md)
explain these populations; availability is never inferred from capture time.

Direct expanded success: `b0ac9e7c-8f95-463a-81fd-8b8564bf13cd` (about 54.5s).
Service/API success: `65b5a995-69c5-4d93-b3b1-de1683cf2d01`; rerun inserted zero
duplicates. The final validated pack is
`data/generated/powerbi-real/183ecd4962fcc5281901392af185522424d2a144f03d4b7cca5ad0a8993df3f3/`.
The report remains at http://127.0.0.1:60114/, app
`dashboard:b31d5d91-39e6-4d2a-8719-4888de544244`. It shows 181 stale source/series
records out of 268 and zero unknown stale flags; upstream ingestion is not verified.
Its polling monitor offers an explicit reload for newer packs and preserves the
working report on failure. The controlled failure-status test was restored to the
actual successful service run afterward.

Final suites: 109 tests, 105 passed/four opt-in database skips in the Dagster
environment; core-only 97 passed/12 optional/database skips. Shell/JavaScript
syntax, Ruff, hard SQL extraction bounds and browser reload/filter/evidence/failure
checks passed. Generated restricted data remain ignored.

**Exact next engineering task:** Josh / maintainer reviews the T-023–T-025 PR
and its CI results before merging. Subsequent onboarding should address missing source availability
for the 170 current-only series and source-specific BLS/ECB adapters, without
writing to upstream schemas from MarketAtlas. **Next release acceptance remains
T-015 / AC-009** if Power BI access becomes available; the user has no access,
so do not repeat that request or claim Power BI execution from browser checks.

**Historical T-021/T-022 checkpoint (2026-10-30):** native Dagster downstream recovery
is fixed and exercised against PostgreSQL. Parent
`1600569b-a641-4e30-aaeb-8815feef00b0` deliberately failed before graph publication;
child `86359104-cf40-4c3b-9667-c21fa760b3ac` resumed only the six remaining stages
and completed. Version-2 checkpoints verify captures, original dates,
connection identities and publication pointers before resume. Older checkpoints
require a fresh full run. See [recovery evidence](../reports/t021-dagster-recovery-validation.md)
and [runbook](dagster-orchestration.md#resume-a-failed-run).

The final validated real-data pack is
`data/generated/powerbi-real/fb860c24507b9b0fdd66a449ba49b64d0457d2887558fd38d0e68332ba1d170d/`.
Native report projects are generated at
`data/generated/reports/fixture-project/MarketAtlas.pbip` and
`data/generated/reports/real-project-validated/MarketAtlas.pbip`.
Each has five pages; official PBIP/PBIR JSON schemas and model-binding checks
passed. These are **unexecuted Power BI source**, with direct evidence selection
but no configured cross-page drill-through. The user has no Power BI access;
Desktop is unavailable on this Mac, and the discovered Power BI plugin has only
been suggested, not connected. Do not repeatedly request the same unavailable
access or mark T-015/AC-009 passed.

The actual-data browser report is open at [MarketAtlas macro research](http://127.0.0.1:60114/).
It has four verified views and concept/quality filter-reset/evidence checks.
Use `scripts/report-preview.sh start` to reopen it; the
[front-end runbook](report-frontend-runbook.md) covers startup, status, stop and
clean-checkout recovery. Its loopback-only preview restarts after user login, but its data are frozen to
the pack above. It neither publishes externally nor automatically refreshes.
[Report instructions](../powerbi/guides/generated-reports.md) reproduce both
native projects and the browser report. [T-022 evidence](../reports/t022-report-project-validation.md)
records scope and remaining gates.

Final Python checks: 100 tests, 96 passed/four opt-in database skips in the Dagster
environment; core-only: 89 passed/11 optional skips. Dagster UI remains at port
3001 and the daily 18:30 New York schedule remains STOPPED. Upstream ingestion,
production Dagster hosting and automatic Power BI/browser refresh are separate.
The branch is `feat/powerbi-dagster-refresh`, based on pushed commit `84291c4`;
T-021/T-022 and the report startup runbook follow `84291c4` on this branch.
Inspect Git and the branch PR for the final commit and remote state.

**Exact next acceptance task: T-015 / AC-009**, owner Josh / report owner. If an
authorized Power BI environment becomes available, execute the pinned PostgreSQL
fixture refresh, native visual/filter reconciliation and provenance drill-through.
Until then, use the local browser report and preserve the open acceptance gate.

**Historical T-020 checkpoint (2026-10-30):** optional Dagster orchestration now runs
13 ordered PostgreSQL-to-MarketAtlas stages, with rolling dates, contract gates,
private checkpoints, retries and database lock exclusion. The user selected
PostgreSQL-only input; upstream FRED ingestion is not launched. The local
UI/daemon was verified at http://127.0.0.1:3001. The daily 18:30 New York schedule
is defined and STOPPED; no production service or reboot recovery is installed.
See [the Dagster runbook](dagster-orchestration.md) and
[T-020 evidence](../reports/t020-dagster-orchestration-validation.md).

The live run `dc8d2735-a568-409b-99c9-a1f83ee99d30` completed all stages. Its
validated real-data pack is
`data/generated/powerbi-real/f8130b91601b18a60a16ddfdc167ebb2f75aa1fe5ca64a46321252af664d4264/`.
Historical T-020 snapshots: context `e98b634d-0571-5406-a3fc-5d56e8d2c43f`, graph
`0428f123-c947-51ef-884a-91ad7672aca4`, quality
`0782c4b0-b090-59cc-bd3c-6f73fdedea69`. The T-017 values below are historical.
The Dagster-environment suite passed 87 tests with four opt-in database skips;
all 13 orchestration tests passed with the live lock check enabled. Core-only
execution passed 82 tests with nine optional/database skips. The spec, export,
rename and orchestration work is packaged on `feat/powerbi-dagster-refresh`;
preserve any later local changes.
T-015 / AC-009 remains the next report acceptance task.

**T-018 checkpoint (historical):** T-018 adds validated Power BI CSV export
jobs, a Power Query loader, report recipes and synthetic GitHub workflow source.
The main spec has also been reconciled with this handoff. The T-018 work is
included alongside T-019/T-020 in the implementation branch. See [T-018 validation](../reports/t018-powerbi-data-jobs-validation.md)
and [data-job instructions](../powerbi/guides/data-jobs.md). The four existing
local publications passed a read-only export check. Power BI authoring and the
GitHub workflow were not executed in this checkpoint; T-020 later adds the local
Dagster runtime and a stopped daily schedule.

T-019 renames the synthetic database publication to `synthetic_fixture`.
Migration 012 is applied locally; all four publication snapshot IDs and original
timestamps were preserved. Producers, exports, the TMDL template and current
instructions use the new name. Historical manifests and export packs retain
their original labels. See [publication access](publication-access.md) and
[rename validation](../reports/t019-publication-rename-validation.md). The current
credential-free suite passed 75 tests with three opt-in skips; all 15 focused
Power BI/export/rename tests passed with database checks enabled. These changes
are included in the implementation branch. T-015 remains the next acceptance task.

An actual-data-only starter export also passed for the three live macro
publications, excluding the synthetic `synthetic_fixture` publication. Its ignored local
archive is `data/generated/powerbi-real/marketatlas-real-data-1eb65542df03.zip`.
See the actual-data-only command in the data-job guide; the repeatable CLI needs
a dedicated `[report_database]` profile, which was not present at this check.

**Last merged baseline:** T-017 is implemented, validated and merged in
[PR #10](https://github.com/thatquantguy44/MarketAtlas/pull/10). There is no
partially implemented T-017 slice to finish. The next task is **T-015 — Power BI
fixture execution / AC-009**, owned by Josh / project owner. Begin by checking
the available authorized Power BI authoring environment; its absence was the
last recorded blocker. A source template, SQL checks or React demonstration
alone cannot close that acceptance gap.

T-015 remains the exact next acceptance task. The new file-pack route supports
portable report exploration; the retained T-015 checklist still requires the
PostgreSQL template/refresh exercise against one pinned synthetic snapshot.

Read this checkpoint, then [the specification](spec.md),
[tasks](tasks.md), [acceptance register](acceptance.md),
[Power BI instructions](../powerbi/README.md), and
[T-017 evidence](../reports/t017-revision-quality-publication-validation.md).
Read `.agents/AGENTS.md` before acting. The broader history below is reference;
the checkpoint and next-task instructions are the restart path.

| Checkpoint | Last verified value |
| --- | --- |
| Merged T-017 baseline | `5b59210628d66ba832df3c8853bbd042dc041d5c` on `main` |
| Implementation commits | `eda2a60` publication/API/tests; `aab0ac5` workspace; `de537bb` documentation/evidence |
| Migration level | 012, `012_rename_synthetic_fixture_publication.sql` (applied 2026-10-30) |
| Historical T-017 validation baseline | 66 Python tests including PostgreSQL; 11 frontend tests; TypeScript/Vite build; browser metrics/provenance/coverage/outage recovery |
| Historical T-017 credential-free baseline | 65 Python tests passed with `-S`; one opt-in database test skipped |
| Synthetic fixture SHA-256 | `15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da` |
| Historical T-017 quality publication | `macro_revision_quality`, 3 selected summaries and 3 provenance rows |
| Historical T-017 quality snapshot | `4cc8f4fc-0d26-518c-be0e-b5723b2ae060` |
| Historical T-017 quality input manifest | `de3df312-8b4f-5fbc-95eb-980984427e70` |
| Historical T-017 quality build run | `3a578092-9c79-5506-b72b-fd729e7d542b` |
| Historical T-017 quality output SHA-256 | `a8265353122167f2d5fd7d81baf79e7d501f872a0c9c8a67d6082cda3be3b970` |
| Last synthetic `synthetic_fixture` snapshot | `bd0ff55e-db73-5196-81c9-066da5523348`; re-resolve before a Power BI refresh |
| Remaining release gaps | T-015/AC-009; broader T-004 adapters; public source rights/artifact review; scheduled deployment and operational readiness |

These are retained observations, not promises about a future machine or live
publication pointer. The quality snapshot was built from the validated worktree
before the merge; its recorded code revision need not equal the merge commit.
Raw extracts and `data/generated/t017_validation.json` are ignored local files,
so a fresh checkout may not contain them. Source configuration belongs only in
ignored `configs/local.toml`. Source-derived data remain restricted internal-only.

### First actions after reopening

1. Inspect `git status --short`, the current branch and recent history. Fetch
   `origin` and verify the merged baseline is in the intended base branch before
   creating a new task branch. Preserve any new local work; this handoff does not
   authorize resetting it or merging another PR.
2. Use the retained validation above as the baseline. Re-run relevant checks
   when code, dependencies, data or environment have changed. For a fresh
   credential-free check, run `PYTHONPATH=src python3 -S -m unittest discover -s tests -v`.
   Frontend commands are `npm --prefix frontend test` and
   `npm --prefix frontend run build`; install from the existing lockfile with
   `npm --prefix frontend ci` if dependencies are absent.
3. For an authorized local integration check, use
   `MARKETATLAS_TEST_DATABASE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v`.
   Its synthetic T-017 database writes roll back. Consult
   [operations](operations.md) before migrations, refreshes or publication.
4. If reviewing the UI, start the report API and frontend from the repository
   root in separate terminals:

   ```sh
   PYTHONPATH=src python3 -m market_atlas report serve-macro-economic-graph
   npm --prefix frontend run dev -- --host 127.0.0.1
   ```

   The last session used ports 8765 and 3000. Check existing listeners before
   starting duplicates; session process IDs and temporary scripts are not
   durable dependencies. Open **Live macro graph → Inflation → CPI**, inspect
   quality provenance, then select a series outside the quality selection to
   check its coverage label. Graph taxonomy and quality have independent snapshots.

### Execute T-015 next

Use [the Power BI package](../powerbi/README.md) and
[T-015 source-package evidence](../reports/t015-powerbi-source-package.md).
Confirm an authorized Windows Power BI Desktop environment or suitable service
authoring workflow, plus a dedicated report login provisioned by the database
owner. A five-page native project generator now complements the original TMDL source;
record the actual import/project workflow used. Generated CSV projects remain
unexecuted and do not replace the PostgreSQL connector/refresh exercise. The
user has confirmed no Power BI access; the local browser report is usable now.

Resolve the synthetic publication immediately before refresh, using the report
reader, and set the same UUID in every template import through `pSnapshotId`:

```sql
SELECT serving_snapshot_id, published_at
FROM atlas_report.current_snapshot_metadata
WHERE publication_name = 'synthetic_fixture';
```

Build the five documented pages. Reconcile 15 nodes, 14 relationship facts,
3 curated contexts and 32 correlation estimates; prove node/macro/pair filtering
and reset, distinct-count safety, pinned/as-of/freshness labels, and provenance
for relationship `A11`, context `CTX3`, and one correlation. Retain permitted
PBIP/PBIR source, synthetic screenshots, refresh results and reconciliation
evidence. Update `docs/tasks.md`, `docs/acceptance.md`, and this handoff only to
the extent supported by those artifacts.

If authoring access is still unavailable, retain the known access blocker and
keep T-015 open and AC-009 partial. Do not repeat the access request without a
new capability or user direction; SQL/template/browser validation does not
resolve Power BI acceptance. Broader source onboarding
requires its own explicit contract and owner/rights decision.

### Ready-to-paste prompt for the next agent

```text
Resume MarketAtlas from docs/handoff.md, starting with "Start here next session".
T-026/T-027 are complete at their documented restricted-local window scope. Josh
explicitly authorized the staged upstream repair; do not ask again. Preserve the
267-series / 127,907-version repaired source and its reversible backups. Read
source-health-recovery.md and T-027 evidence, then verify both Git branches and the
current app/schedule before acting. Source branch fix/fred-pagination-source-recovery
has four rebased commits ending 7ed2af5; primary branch is feat/source-freshness-vintages.
Both are pushed as EcoMedallion #95 and MarketAtlas #14; neither is merged. The
next task is PR/CI review; merge only if requested. Four upstream full-suite failures reproduce on the baseline; retain
that distinction. Existing Home Sales remains current-only without ALFRED history;
all 23 remaining age flags matched provider latest periods at validation. Routine
MarketAtlas reads stay scoped and corrections preserve system-time history.
T-015/AC-009 remains open without repeated Power BI access requests.
```

## Current state

The original market knowledge graph specification has been reviewed and reorganized into specification, architecture plan, tasks, roadmap, and traceability documents. The product name is MarketAtlas. The repository is [thatquantguy44/MarketAtlas](https://github.com/thatquantguy44/MarketAtlas), default branch `main`.

MacroMedallion and EcoMedallion are interchangeable names for the same upstream asset. Operators may configure an optional local checkout for discovery and lineage in git-ignored `configs/local.toml`; MarketAtlas neither requires a remote repository pin nor imports its source code. The fixture implementation provides a Python CLI, deterministic synthetic records, validation, manifest, and availability-cutoff inspection. The authorized local `macro_medallion` PostgreSQL database is the primary integration contract, connected through a scoped source-reader role. T-004B loads `meta.fred_series` plus `gold.fred_point_in_time` into `atlas` as 3 macro identities and 151 versioned observations under one immutable input manifest; an identical rerun writes zero rows. T-004C.1 adds `contracts/source_contracts.toml` and a metadata-only verifier. T-004C.2 promotes `gold.dim_series`, `gold.release_calendar`, and `gold.v_source_coverage` as read-only, bounded macro-context interfaces. T-004C.3 stores their latest approved records only in dedicated `atlas` current-context tables and publishes a separate immutable `macro_context` report snapshot. T-004C.4 projects the approved current taxonomy into source-backed `measures` assertions and publishes the separate `macro_economic_graph` snapshot. T-004C.5 adds a full approved-series catalog extractor: the validated local run published 290 source-scoped series, 11 taxonomy concepts, and 290 `measures` assertions. The report API returns category-hub navigation first and a bounded, searchable, paged series neighborhood only after category selection; navigation `contains` links are not assertions. The local report API reads only its report views under `marketatlas_report_reader`; the React workspace has an explicit Live macro graph mode. This is descriptive current taxonomy, not historical taxonomy, causality, or sensitivity. Evidence: `reports/t004c-full-series-catalog-validation.md` and the T-004C.1–.4 reports.

T-001–T-003, T-005–T-014, T-016 and T-017 are complete at their stated fixture, design or restricted-local scope; T-004 and T-015 remain open. T-002 established the credential-free CLI/configuration path and T-003 established the deterministic synthetic fixture contract. Migration `001_identity_ontology.sql` created the `atlas` and `atlas_report` schemas, three scoped NOLOGIN roles, identity/ontology tables, endpoint constraints, identifier-overlap protection, and quarantine storage. Migration `002_temporal_assertions.sql` adds correction/retraction versions, effective/knowledge/system cutoff queries, and bounded traversal. Migration `003_observation_versions.sql` adds input manifests, calendar sessions, and market/macro observation versions with cutoff-aware selectors. Migration `004_curated_macro_context.sql` adds versioned series-country/concept and market-context mappings with owner, evidence basis, taxonomy version, and mandatory context-only semantics. Migration `005_rolling_correlation_estimates.sql` adds versioned fixed-window rolling correlations with explicit undefined states and cutoff/input metadata. Migration `006_build_publication.sql` adds immutable build/snapshot identities, a pinned correlation serving fact, and transactional publication. Migration `007_reporting_provenance.sql` adds snapshot-pinned report dimensions, facts, and drill-through provenance. T-013 adds a reproducible release gate with 20-run prepared-query p95 measurements, role/contract/integrity validation, and injected-failure recovery. It corrected fixture provenance validation to pin to the synthetic_fixture publication snapshot when independent live publications exist. T-014 exercised a fresh-checkout fixture walkthrough (49 Python tests), captured fixture/live browser evidence, improved the live canvas to 12 legible nodes per page, and added data/license, operational, and restricted-extension documents. T-016 promoted `gold.v_series_revision_summary` as a sixth restricted internal-only contract and validated a three-series read-only extract without a graph/report write. The React fixture demo provides the evidence-first workspace. A Power BI source package exists, but its report/refresh exercise remains uncompleted.

## Gate Status

T-017 is complete for configured restricted-local revision quality. Migration
`011_revision_quality_publication.sql` adds append-only captured versions and the
separate `macro_revision_quality` publication. The report-only API and live
selected-series drawer expose current metrics/unknowns and independent capture,
snapshot, input and build provenance. Three approved summaries were published;
an identical rerun reused its snapshot. Failure rollback/recovery and browser
coverage/outage states passed. Evidence and exact commands:
[`reports/t017-revision-quality-publication-validation.md`](../reports/t017-revision-quality-publication-validation.md).

**Satisfied for documentation handoff:** the package defines a candidate scope, downstream design, task dependencies, and required evidence. The documents are reviewable planning artifacts.

**Implementation readiness established through T-017 at the stated fixture, design and restricted-local scope:** the upstream interfaces, vintage semantics, dedicated write schemas, role boundaries, temporal reference replay, versioned observation selection, curated context semantics, bounded analytical estimates, atomic fixture publication, report/provenance contract, React demo, clean-room walkthrough, operational boundary, restricted-extension design, and revision-quality context are verified or documented at their stated scope. The named local pilot owner and restricted internal-only redistribution decision are recorded; public redistribution review, Power BI validation, scheduled deployment, and dependency-major upgrade decisions remain open. This is not an end-to-end release gate pass.

## Next Action

**Owner: Josh / project owner.** The next blocked acceptance slice is **T-015 — Power BI exercise / AC-009**. A source-controlled template and reconciliation script now exist, but an authorized Power BI Desktop or service environment must open it against one pinned synthetic snapshot, build the report pages, prove filtering/distinct-count reconciliation and provenance drill-through, and retain its artifacts. Power BI acceptance remains unpassed until that occurs. Future source onboarding still requires an explicit contract for each object; do not promote objects merely because they are readable.

The handoff inputs are the completed identity, temporal, observation, context, analytical, publication, reporting, frontend, and release-validation artifacts, `spec.md`, `plan.md`, `tasks.md`, `reporting.md`, ADR-001, the verified adapter contract, the fixture contract, [contributor walkthrough](contributor-demo.md), [operations handoff](operations.md), and [extension contract](securities-finance-extension.md). Do not write into `meta`, `silver`, `gold`, `bronze`, or `audit`; upstream access remains through `marketatlas_source_reader`.

The implemented frontend follows [ADR-001](decisions/001-quantmeridian-react-scaffold.md): the QuantMeridian React/Vite/TypeScript/Tailwind/Router/Zustand scaffold pattern, with independent MarketAtlas modules and no browser database credentials. T-011/T-012 delivered snapshot-pinned fixture report/provenance contracts and the React workspace; T-017 adds selected-series live quality context.

## Access and integration checklist

| Needed input | Owner role | Why it matters | Default until resolved |
| --- | --- | --- | --- |
| Optional local upstream checkout | Josh / repository owner | Provide local discovery/lineage context without importing source code | No remote URL, commit, or branch pin required |
| Approved source tables/views and grains | Data owner | Establish read contracts and source keys | `meta.fred_series` and `gold.fred_point_in_time` verified for the bounded adapter |
| PostgreSQL version, schema permissions, migration convention | Database owner | Select compatible migration and serving strategy | PostgreSQL 16.15 verified; `atlas`/`atlas_report` and scoped roles created by versioned migration |
| Market adjustment and macro vintage metadata | Quant / data owner | Support historical and analytical claims | Unsupported estimates withheld; latest-only labeled descriptive |
| Source and redistribution rights | Data owner | Define public demo contents | Synthetic fixtures only in public artifacts |
| Power BI authoring/refresh environment | Report owner | Confirm Import/DirectQuery, gateway and visual constraints | Proposed Import pilot; standard visuals remain usable |
| Owner and runtime scheduling | Engineering owner | Make refresh and rollback accountable | Manual fixture run before scheduling |

Never record passwords, connection strings with credentials, internal hostnames, or restricted source samples in the public discovery report. Authorized environment details belong only in git-ignored `configs/local.toml`. The tracked `configs/local.example.toml` contains placeholders.

## Implementation instructions for the receiving agent

Read the specification first and preserve requirement IDs. Use the architecture plan as the candidate implementation approach and execute the task list in dependency order. Complete discovery, update the contracts with verified mappings, and record deviations before changing database objects. Do not assert that unavailable upstream metadata has been verified.

Implement the synthetic fixture mode before relying on an upstream service. Keep read permissions to source systems and write permissions to graph/report schemas separate. Preserve source provenance and historical versions. Do not silently substitute revised macro history for point-in-time data or forward-fill across releases for correlation estimates.

Keep reference assertions, curated macro context mappings, and statistical estimates distinguishable in storage and report outputs. In Power BI, use explicit fact grains and bridges so multi-valued graph relationships cannot multiply observations or aggregate exposures incorrectly.

Mark tasks complete only with the evidence they require. Store validation summaries and input/run manifests without credentials or proprietary payloads. Update the handoff with actual paths, commands, remaining defects, and measured results as implementation progresses.

## Expected delivery evidence

The release candidate should include a clean fixture run, graph integrity results, historical availability/revision checks, a hand-checkable correlation result, repeat-run idempotency evidence, Power BI grain/reconciliation results, measured query performance, and a refresh failure/rollback demonstration. Requirements, tasks, and acceptance evidence must remain traceable.

The clean fixture run, performance evidence, manual recovery procedure, walkthrough, screenshot evidence, and license/data notice are retained. Power BI semantic-model/report artifacts, approved production ownership, alerting, and broader source-rights evidence remain future artifacts.

## Operations handoff requirements

The [operations handoff](operations.md) records the current manual posture, unassigned scheduled-pilot responsibilities, safe refresh, and controlled recovery. Before a scheduled pilot, name the pipeline owner, database owner, report owner, and quant methodology owner. Record source freshness expectations, quarantine rules, serving snapshot selection, alert destination, and recovery procedure. On failed refresh, preserve the last successfully published snapshot, display its as-of time and stale status, and retain failed-run diagnostics. Never promote a partially built graph to reporting views.

Recovery should disable the graph job and restore the prior serving snapshot or migration state without altering upstream MacroMedallion / EcoMedallion tables. Demonstrate this on fixtures or an isolated environment before scheduling.

## Resuming after a handoff

Use the checkpoint and ready-to-paste prompt at the top of this document. After the next session, replace its observations with the last completed task, actual code/PR baseline, migration level, fixture/data hashes, run and serving snapshot IDs, validation evidence, open blockers, and one exact next task with owner. Keep historical validation dates and live versus fixture scopes explicit.
