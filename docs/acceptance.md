# MarketAtlas — Acceptance Evidence Register

Status: implementation evidence is in progress. AC-002 through AC-008, AC-010 through AC-012, AC-017, and AC-018 pass at their stated fixture/design scope; several checks remain partial. A task checkbox or planning review does not satisfy an acceptance criterion.

| Acceptance | Requirement | Status | Evidence artifact / run / commit | Reviewer and date |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | Passed (local restricted scope) | `reports/t001-source-catalog-validation.md`, `reports/t001b-source-reader-scope-validation.md`, `reports/t004b-live-ingestion-validation.md`, `reports/t004c-source-contract-verification.md`, `reports/t004c-macro-context-validation.md`, `reports/t004c-macro-context-publication-validation.md`, `reports/t004c-live-economic-graph-validation.md`, `reports/t016-source-governance-discovery.md`, `docs/source-catalog.md`, and `contracts/source_contracts.toml`: all local relations/views cataloged; six approved live interfaces have verified source contracts and bounded adapters; Josh owns the local source/data, database, report, methodology, refresh/recovery, and incident roles; redistribution is restricted internal-only and public sharing remains unauthorized | Josh / project owner, 2026-10-26 |
| AC-002 | REQ-002 | Passed (fixture) | `reports/t002-validation.md`, `reports/t003-validation.md`: credential-free deterministic fixture build, validation, and cutoff inspection pass | Implementation agent, 2026-10-24 |
| AC-003 | REQ-003 | Passed (fixture) | `reports/t005-validation.md`: stable UUID reload, ticker history, overlap rejection | Implementation agent, 2026-10-24 |
| AC-004 | REQ-004 | Passed (fixture) | `reports/t006-validation.md`: bounded path, endpoint rules, disputed/retracted state handling, and invalid-type rejection pass | Implementation agent, 2026-10-24 |
| AC-005 | REQ-005 | Passed (fixture) | `reports/t006-validation.md`: source availability and MarketAtlas record-time replay differ as expected; unsupported history is explicit | Implementation agent, 2026-10-24 |
| AC-006 | REQ-006 | Passed (fixture + bounded live macro) | `reports/t017-revision-quality-publication-validation.md`: restricted current-quality capture remains distinct from unsupported source availability/history;  reports/t007-validation.md and reports/t004b-live-ingestion-validation.md: fixture version contracts plus live point-in-time macro metadata/observations, input manifest, and idempotent load pass | Implementation agent, 2026-10-26 |
| AC-007 | REQ-007 | Passed (fixture) | `reports/t008-validation.md`: source-backed country/concept and curated sector context mappings have rationale, owner, source, dates, taxonomy version, and explicit non-sensitivity label | Implementation agent, 2026-10-24 |
| AC-008 | REQ-008 | Passed (fixture) | `reports/t009-validation.md`: fixed-window configured-pair return correlations, independent numerical match, undefined statuses, input/cutoff metadata, and no-lookahead validation | Implementation agent, 2026-10-24 |
| AC-009 | REQ-009 | Partial | `reports/t011-validation.md`, `docs/reporting.md`, `reports/t012-validation.md`, `reports/t015-powerbi-source-package.md`, and `powerbi/`: snapshot-pinned outputs, React demo, template, generated native projects and a verified local actual-data browser report exist (see `reports/t022-report-project-validation.md`); Power BI visual/refresh/drill-through execution remains required | Implementation agent, 2026-10-30 |
| AC-010 | REQ-010 | Passed (fixture + restricted quality) | `reports/t017-revision-quality-publication-validation.md`: separate immutable quality publication, exact rerun reuse, report grain and prior-pointer retention pass;  `reports/t010-validation.md`: immutable build/snapshot identities, idempotent output reuse, validation hash, and single-pointer publication | Implementation agent, 2026-10-26 |
| AC-011 | REQ-011 | Passed (fixture + restricted quality) | `reports/t017-revision-quality-publication-validation.md`: selected quality rows expose source/input/build, capture time and independent publication provenance through the report API and browser;  `reports/t011-validation.md`: sourced relationship, curated context, and correlation each drill through to snapshot, build/input, and source/method evidence | Implementation agent, 2026-10-26 |
| AC-012 | REQ-012 | Passed (design) | `docs/securities-finance-extension.md`: controlled restricted client/agreement/loan/collateral/rule-evaluation grains reference existing instrument node IDs only; public report/browser grants are excluded, and unknown eligibility remains explicit | Implementation agent, 2026-10-26 |
| AC-013 | NFR-001 | Partial | `reports/t017-revision-quality-publication-validation.md`: report-reader scope and restricted-current payload boundaries pass;  `reports/t005-validation.md`, `reports/t013-release-validation.md`, `reports/t016-source-governance-discovery.md`: source/writer/report role boundaries, source read-only access, and six approved restricted-live contracts pass in the local environment; public release-artifact review remains outside the restricted local scope | Implementation agent, 2026-10-26 |
| AC-014 | NFR-002 | Passed (fixture) | `reports/t007-validation.md`, `reports/t009-validation.md`, `reports/t010-validation.md`, `reports/t013-release-validation.md`: the same deterministic fixture identity, method/configuration, output snapshot, and report result reproduce through the release gate; broader upstream reproducibility remains separately limited by source rights/history | Implementation agent, 2026-10-26 |
| AC-015 | NFR-003 | Partial | `reports/t017-revision-quality-publication-validation.md`: tampering, missing-ID accounting, numeric/temporal/rights gates and unique snapshot/series grain pass;  `reports/t005-validation.md`, `reports/t006-validation.md`, `reports/t007-validation.md`, `reports/t008-validation.md`, `reports/t009-validation.md`, `reports/t010-validation.md`, `reports/t011-validation.md`, `reports/t013-release-validation.md`: graph, temporal, observation, context, analytical, serving-snapshot, and report-grain guards pass again in the release gate; broader release-artifact checks remain | Implementation agent, 2026-10-26 |
| AC-016 | NFR-004 | Passed (local envelope) | `reports/t013-release-validation.md`: one declared warm local PostgreSQL fixture build completed in 0.188182 seconds; 20 prepared executions each of catalog summary and largest 50-series neighborhood had p95 0.000161 and 0.000964 seconds, below the proposed 300-second/2-second targets | Implementation agent, 2026-10-26 |
| AC-017 | NFR-005 | Passed (fixture + restricted quality) | `reports/t017-revision-quality-publication-validation.md`: injected quality materialization failure rolls back rows, retains a failed run, preserves the pointer and recovers on retry;  `reports/t010-validation.md`, `reports/t013-release-validation.md`: an injected failed fixture build records failure, writes zero serving rows, and leaves the previous published pointer unchanged; rerun/recovery validation passes | Implementation agent, 2026-10-26 |
| AC-018 | NFR-006 | Passed (fixture walkthrough) | `docs/contributor-demo.md`, `reports/t014-contributor-handoff.md`: fresh-checkout credential-free fixture build/validate/inspect and all 49 Python tests passed; README/handoff links trace the requirements, tasks, evidence, data notice, operations, and extension contract. Optional live API and Power BI remain explicitly out of this walkthrough | Implementation agent, 2026-10-26 |

T-018 supplementary evidence (2026-10-30): [Power BI data-job validation](../reports/t018-powerbi-data-jobs-validation.md)
records portable file generation, typed/hashed pack validation, safe reruns,
failed-export isolation, and report-only export of four existing local
publications. [Job instructions](../powerbi/guides/data-jobs.md) and
[report recipes](../powerbi/guides/report-recipes.md) extend the contributor/report
handoff for AC-002/009/010/011/013/014/015/017/018 without changing their recorded
release status. AC-009 remains partial: M/DAX source and GitHub workflow source
have not been executed in Power BI or GitHub, and no scheduler or service refresh
has been enabled.

T-020 supplementary evidence (2026-10-30): [Dagster orchestration validation](../reports/t020-dagster-orchestration-validation.md)
records a successful 13-stage live PostgreSQL refresh, rolling-date plans,
source-contract gating, checkpoint/retry/failure behavior, database lock
exclusion, definition/schedule checks and a validated real-data export. The
local UI/daemon is verified; the daily schedule is defined and stopped. This
extends operating evidence for AC-006/010/011/013/014/015/017/018 at local scope;
production scheduling, upstream ingestion and Power BI service/report execution
are not established. AC-009 remains partial.

Attach reproducible output locations, input hashes, method/configuration versions, declared environment, and concise results as appropriate. Restricted data and environment details must stay in their authorized location; public summaries should use synthetic examples and safe identifiers. Record failed and unsupported checks honestly.

T-021/T-022 supplementary evidence (2026-10-30): [native recovery](../reports/t021-dagster-recovery-validation.md)
passed with a real failed parent and successful six-stage child; [report source
and browser validation](../reports/t022-report-project-validation.md) covers native
JSON schemas/bindings and actual-data browser filtering/evidence. These strengthen
local recovery and report access. AC-009 remains partial: no Power BI engine
refresh, rendering or cross-page drill-through was executed.

T-023–T-025 supplementary evidence (2026-10-30): [automation and expanded-series
validation](../reports/t023-t025-automation-series-validation.md) records failure-safe
local report delivery, source freshness/failure notices, supervised macOS startup,
a running daily schedule and a successful background-service refresh. Point-in-time
ingestion expanded to 94 series/35,576 versions; current coverage/quality expanded
to 268 FRED series with separate temporal eligibility. These extend local scope
under AC-006/007/009/010/011/013/014/015/017/018. Source availability is not invented
for 170 vintage-unknown series, source APIs remain unrefreshed, and AC-009 remains
partial pending actual Power BI execution. Production/always-on hosting is not claimed.

## T-026 source-health evidence (2026-10-31)

The bounded read-only diagnosis/manual Dagster job supplies supplementary evidence
for AC-006/010/013/015/018: independent clocks, verified age rules, explicit
current-only policy and source-write isolation. See [T-026 evidence](../reports/t026-source-health-validation.md).
Provider probes and the tested upstream patch do not close source-repair tasks,
certify PostgreSQL freshness, expand admitted PIT coverage or satisfy AC-009.

## T-027 staged source repair (2026-10-31)

Explicitly authorized local source repair adds evidence for AC-006/010/013/014/015/017/018:
267 admitted series / 127,907 versions, authoritative source dates, reversible
source backups, independent clocks, system-time corrections and zero-change replay.
All 23 remaining age flags matched provider periods. See [T-027 evidence](../reports/t027-source-repair-validation.md).
The current-only exception, bounded history and four baseline upstream test
failures are retained limitations. No broader Gold, production, public-data or
native Power BI acceptance is claimed.

## T-028/T-029 macro research foundation (2026-10-31)

[Macro analytics validation](../reports/t028-t029-macro-analytics-validation.md)
adds supplementary research evidence for AC-006/008/011/014/015/017/018:
source-date-cutoff preparation, explicit transformations/groups, bounded longer
history, independently checked correlations/distances/standardization/dispersion,
immutable typed evidence packs and exact replay/tamper/failure checks. This is
separate from the instrument-return method and database report publications.
Incomplete samples and unknown vintages stay unavailable. No historical taxonomy,
MarketAtlas historical possession, predictive value, browser integration or new
schedule is established. AC-009 remains partial without Power BI execution.

## T-030 browser research views (2026-11-01)

[Browser analytics evidence](../reports/t030-browser-analytics-validation.md)
extends supplementary AC-008/009/010/011/014/015/017/018 evidence with the locally
rendered heatmap, dispersion timeline, divergence ranking, exact transformed
window/source investigation and scoped controls. Actual normal/narrow checks,
null handling, pack identity, retained analytics across normal refreshes and
authored-content rollback pass. This adds browser consumption of the independent
research pack; it does not establish automatic research generation, predictive
value or native Power BI execution. AC-009 remains partial.

## Spec 001 / WP-02A foundation (2026-11-03)

[WP-02A evidence](../reports/spec001-wp02a-validation.md) records typed
envelope/quantity/reference validation and an isolated synthetic instrument
catalog. The base fixture's hash and existing instrument meanings remain
unchanged. Spec 001's independent SF-AC-003/004/015/017 have structural subcase
evidence only; their full scenarios and every complete feature acceptance row
remain pending. No JSON/CSV equivalence, cutoff selection, eligibility, optimizer,
restricted database permission or report acceptance is claimed. MarketAtlas
AC-012 remains passed at design scope; the foundation does not expand that status.

## Spec 001 / WP-02B input fixtures and adapters (2026-11-03)

[WP-02B evidence](../reports/spec001-wp02b-validation.md) records deterministic
17-table/95-record input packs, strict JSON/CSV adapters into common normalized
facts, TOML/settings and manifest/hash checks, one authoritative representation
per dataset and record-level physical provenance. Gross/net source variants,
unknown/zero quantities, versions, children and selected events remain explicit.
The base public fixture remains unchanged. SF-AC-003/004/015/016/017 have additional
structural/input-equivalence evidence only: active version selection, event
application, balances, eligibility, optimization and downstream reports remain
pending. No complete feature acceptance or expansion of parent AC-012's design
status is claimed.

## Spec 001 / WP-02C temporal selection and event plans (2026-11-03)

[WP-02C evidence](../reports/spec001-wp02c-validation.md) records three independent
cutoffs, half-open state/system intervals, conservative source-day predicates,
supported version/correction selection, unavailable selected-parent propagation,
FIFO uncertainty and JSON/CSV selection equivalence. Exact snapshot-version,
stream/component and completeness declarations support immutable inclusion,
replacement and reversal plans. Unknown boundaries, late unsupported effects and
duplicate reversals block affected calculations; replays do not append effects.

87 focused tests pass (32 new). Full standard-library and Dagster-enabled suites
discover 235 tests: 221 passed/14 skips and 230 passed/five skips respectively.
The base fixture is unchanged. SF-AC-003/004/016 gain partial selection/planning
evidence; all complete feature rows remain pending. Effect arithmetic, capacity,
freshness/eligibility, allocation, recall impact, publication recovery and reports
remain later work. MarketAtlas AC-012 retains its design-only scope.
