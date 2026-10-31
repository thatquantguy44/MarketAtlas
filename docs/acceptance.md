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
