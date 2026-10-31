# T-023–T-025 — Automated report delivery, local service and series expansion

Date: 2026-10-30, America/New_York. UTC captures fall on October 31.
Branch: `feat/automated-report-refresh`, from merged main `f2ea0d8` (PR #12).
Scope: authorized local PostgreSQL/report automation and all eligible approved
FRED series. This is a local pilot, not a completed Power BI or production release.

## Implementation

The 14-stage refresh now delivers the validated pack to the existing browser app.
`reporting/refresh.py` clones the existing app into an isolated candidate, preserves
identity/owner metadata/content, verifies the split build and installs immutable
assets before atomically replacing HTML last. Source snapshot and build/status
metadata roll back if commit fails. Old sidecars remain available to open tabs.
A per-project lock rejects overlaps. Native Dagster resource teardown records a
failed attempt without replacing the previous successful report.

The authored status panel polls the local status file every 30 seconds. It
separates report update time, supplied source stale/unknown counts and upstream
verification. Newer packs offer an explicit reload, preserving unsaved edits.
No protected Data runtime source was changed or cloud publication performed.

The macOS user service uses a Node entry point under the ordinary profile runtime
directory and the pinned Python dependencies. It supervises the existing loopback
Dagster stack, retains `.dagster/` history and supports start/status/restart/stop.
An initial direct shell launch from `Documents` was denied by macOS; the supported
runtime-directory/module entry point works without changing privacy/security
settings or copying credentials. Graceful restart was exercised after correcting
its shutdown-registration race. Scheduler and run-coordinator heartbeats had zero
errors. The schedule was found already running and its enabled state was retained.
The next recorded tick was October 31, 2026 at 18:30 EDT.

## Series admission and live results

Source discovery reads only approved interfaces through `marketatlas_source_reader`.
Metadata, query rows and exclusions stay private under `data/generated/`. Catalog
and observation SQL enforce configured row limits; observation IDs batch in groups
of 25 and use a shrinking hard SQL result budget. The cap is 1,000 catalog entries
and 250,000 observation versions. Selection decisions freeze into checkpoint v3.

An initial wider capture failed extract validation because 35,433 rows in 170
series had blank source-vintage dates. It stopped at `ingest_observations` before
writes. The final eligibility rule excludes those from point-in-time ingestion,
while independently retaining their current coverage/quality. This preserves the
distinction between source availability, extraction time and record time.

| Result | Validated scope |
| --- | --- |
| Catalog | 290 series, 11 concepts, 301 graph nodes, 290 edges |
| Point-in-time observations | 94 series, 35,576 versions; 35,425 newly inserted in first expanded success |
| Current-context selection | 268 FRED series, 32 releases, 268 coverage records; 568 context report rows |
| Current quality | 268 summaries and 268 provenance rows |
| Observation exclusions | 170 with missing/invalid vintage dates, four with no usable window observations |
| Other-source catalog entries | 20 ECB + two BLS; descriptive graph retained, FRED observation adapter excluded |
| Freshness | 181 stale source/series coverage records of 268, zero unknown flags; upstream ingestion not verified |

Successful direct Dagster run: `b0ac9e7c-8f95-463a-81fd-8b8564bf13cd`, about 54.5
seconds of execution. Successful **API/service-launched** run:
`65b5a995-69c5-4d93-b3b1-de1683cf2d01`. The service run saw the same 35,576 versions,
inserted zero duplicates, validated the eight-table pack and updated app
`dashboard:b31d5d91-39e6-4d2a-8719-4888de544244` at the existing URL.
Final retained pack:
`data/generated/powerbi-real/183ecd4962fcc5281901392af185522424d2a144f03d4b7cca5ad0a8993df3f3/`.
A final read-only extraction verified the hard SQL budget retained all 94/35,576
records without truncation. The excluded series and current-context eligibility
are explained in [series coverage](../docs/series-coverage.md).

## Checks

- Optional-runtime suite: 109 tests, 105 passed, four opt-in database skips.
- Core-only suite: 109 tests, 97 passed, 12 optional/database skips.
- Report tests cover successful stable-identity replacement, preserved content and
  old assets, builder failure, checksum corruption, atomic commit failure,
  overlapping refresh refusal, retained successful status, and service secret-env
  isolation. A native Dagster failure test proves monitoring runs on resource
  teardown even when Dagster handles the op exception internally.
- Selection tests cover metadata/source eligibility, invalid observation/vintage
  exclusions, parameterized date windows/batches and discovery/row limit refusal.
  Observation paging tests prove shrinking hard SQL budgets and failure rather
  than silent truncation. Existing native recovery tests pass with checkpoint v3.
- Browser checks: newer-pack notice and reload, updated success/freshness panel,
  268 summary/evidence rows, GDP selecting one matching summary/evidence row, reset
  to 268, and a controlled failure notice with unchanged report HTML. The status
  was restored to the actual successful service run after that controlled test.
- Ruff, shell syntax, supervisor JavaScript syntax and changed-document links pass.

Private run/checkpoint/profile/build/test evidence remains ignored. Startup and
maintenance commands are in [local automation](../docs/local-automation.md) and
[the report runbook](../docs/report-frontend-runbook.md). New branches/runtimes
must be reviewed before replacing this pilot's active checkout.

The Mac must remain running/logged in and PostgreSQL reachable. The job does not
invoke upstream ingestion, send external alerts, publish restricted data or
exercise native Power BI. AC-009 / T-015 remains open. Further raw-source/catalog
onboarding and source availability repairs require their own supported contracts.
