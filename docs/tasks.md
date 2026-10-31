# MarketAtlas — Implementation Tasks

Status: active task plan, 2026-10-30. T-001–T-003, T-005–T-014, T-016–T-020 are complete at their stated fixture, design or restricted-local scope. Broader T-004 adapters and T-015 Power BI execution remain open. A checked task is not a release claim; shared downstream acceptance criteria may remain partial.

Role names are proposed responsibilities. Record the actual person/agent on assignment. Each task must preserve the mapped specification IDs and attach evidence in [acceptance.md](acceptance.md). Read [plan.md](plan.md) for contracts and design decisions.

## Phase A — Establish a portable foundation

### [x] T-001 — Discover source assets and record scope

Owner: integration engineer. Dependencies: none. Maps: REQ-001 → AC-001.

Treat MacroMedallion and EcoMedallion as interchangeable names for one upstream asset. Accept an optional user-selected local checkout through git-ignored configuration; do not require a remote URL, commit, branch pin, or source-code import. Identify owners, PostgreSQL interfaces, grains, permissions, history, and redistribution terms. Produce `reports/discovery.md` with reusable components and unresolved gaps. If access is unavailable, record the limitation and select the independent fixture track; never mark upstream verification passed. Evidence: actual inspected metadata or an explicit unresolved-status inventory, reviewed pilot defaults, and source-owner decisions.

Completed 2026-10-26 for the local restricted scope. A read-only metadata catalog inventories every discovered source relation/view with column and view fingerprints, index-based key clues, select/write access, and a support state. It found 102 upstream relations/views: 6 supported-live interfaces, 85 readable discovered-not-onboarded objects, and 11 unavailable objects; 41 MarketAtlas-owned relations are separately identified. Josh accepted source/data, database, report, methodology, refresh/recovery, and incident accountability. All local source outputs are `restricted_internal_only` with `restricted` redistribution status; public sharing remains unauthorized. Evidence: reports/t001-source-catalog-validation.md, reports/t001b-source-reader-scope-validation.md, reports/t016-source-governance-discovery.md, docs/source-catalog.md, docs/operations.md, and contracts/source_contracts.toml.

### [x] T-002 — Scaffold repository and isolated runtime

Owner: implementation engineer. Dependencies: T-001 scope decision; fixture-only decision is sufficient. Maps: REQ-002, NFR-001, NFR-006 → AC-002, AC-013, AC-018.

Create package/configuration/migration layout, a documented PostgreSQL prerequisite or optional local container, dependency lock, non-secret example configuration, and CLI entry point. Separate source reader and graph writer configuration. Evidence: a clean environment installs and reports configuration without printing secrets; no upstream connection is required for fixture mode. Document real commands only after implementation.

Completed 2026-10-24 for the fixture track. The standard-library CLI, isolated fixture workflow, non-secret configuration example, separate source/target role settings, migrations, and dependency lock are present. `fixture build`, `fixture validate`, and cutoff inspection were exercised without upstream credentials; the CLI regression suite covers the documented inspection command. Evidence: `reports/t002-validation.md`.

### [x] T-003 — Build deterministic synthetic fixtures

Owner: data engineer / quant. Dependencies: T-002. Maps: REQ-002, NFR-002 → AC-002, AC-014.

Define mock instruments/listings, issuer/classification/index nodes, macro series, and synthetic observations. Include ticker changes, multi-membership, late corrections, macro revisions, disputed mappings, missing/constant returns, and a known correlation example. Label every fixture and output synthetic. Evidence: reproducible seed/checksums, data dictionary, expected outcomes, and a fixture adapter manifest; no copied private records.

Completed 2026-10-24 for the fixture track. The canonical synthetic fixture generates deterministic entities, identifiers, assertions, curated contexts, sessions, macro vintages, market observations, configured pairs, and edge cases for ticker history, multi-membership, corrections, missingness, and zero variance. Build/validation and early-cutoff inspection pass with a stable manifest hash. Evidence: `reports/t003-validation.md`, `docs/fixtures.md`.

### [ ] T-004 — Implement canonical adapter contracts

Owner: integration engineer. Dependencies: T-001, T-003. Maps: REQ-001, REQ-006, NFR-001 → AC-001, AC-006, AC-013.

Implement normalized contracts for entities, assertions, observations, and manifests. Map verified upstream objects when available; record optional adapter status separately from working fixtures. Validate required metadata, schema drift, rights, timestamp coverage, and source read permissions. Evidence: fixture contract checks plus inspected upstream mappings and read-only role checks for each activated adapter. Unavailable upstream adapters remain pending, not advertised as implemented.

Progress: T-004B completed 2026-10-24 for the bounded local PostgreSQL pilot. The reader extracts three configured macro series and point-in-time observation versions; the separate writer validates the extract, records an immutable input manifest, upserts macro-series identities, and inserts versioned macro observations into atlas. The first live run inserted 3 identities and 151 observation versions; an identical repeat reused the manifest and inserted zero rows. T-004C.1 through .5 completed the source-contract registry, bounded context interfaces, current-context publication, macro-economic graph, and full 290-series taxonomy catalog. T-016 completed 2026-10-26: `gold.v_series_revision_summary` passed source-contract verification as the sixth restricted internal-only interface; its adapter validates configured IDs against `gold.dim_series`, reads in 1–1,000-ID batches, preserves missing summaries as unknown, and produced three local summaries with no missing IDs. It does not scan the 20.5-million-row revision-history table or write/publish `atlas` data. Evidence: reports/t004b-live-ingestion-validation.md, reports/t004c-source-contract-verification.md, reports/t004c-macro-context-validation.md, reports/t004c-macro-context-publication-validation.md, reports/t004c-live-economic-graph-validation.md, reports/t004c-full-series-catalog-validation.md, reports/t016-source-governance-discovery.md, docs/t016-revision-quality-spec.md, contracts/source_contracts.toml. Broader entity/relationship contracts and deployment/scheduling remain future work.

## Phase B — Build graph and analytical contracts

### [x] T-005 — Implement identities and ontology

Owner: database / implementation engineer. Dependencies: T-003, T-004 fixture contract. Maps: REQ-003, REQ-004, NFR-003 → AC-003, AC-004, AC-015.

Add dedicated-schema migrations for stable entities, versioned attributes, source identifiers, controlled predicates, and allowed endpoint pairs. Distinguish instruments/listings and types referenced by index/country/concept links. Evidence: stable IDs on reload, ticker-change and ticker-collision cases, no orphan accepted endpoints, and rejected invalid types/ambiguous overlaps. Preserve valid multi-membership.

Completed 2026-10-24 for the fixture track. Migration `001_identity_ontology.sql` created dedicated schemas, scoped NOLOGIN roles, identity/ontology tables, declarative endpoint enforcement, identifier overlap protection, and quarantine storage. The live fixture validation loaded 15 nodes, 4 identifier intervals, and 14 assertions; identical reloads preserved counts and UUIDs, `OLDX`/`NEWX` resolved to one listing, and invalid endpoint plus overlapping identifier probes were rejected. Evidence: `reports/t005-validation.md`.

### [x] T-006 — Implement temporal reference assertions

Owner: database engineer. Dependencies: T-005. Maps: REQ-004, REQ-005, NFR-003 → AC-004, AC-005, AC-015.

Store effective validity, source availability, and system record intervals with provenance. Preserve corrections/retractions and disputed/unknown states. Implement bounded path queries with explicit effective/knowledge/system cutoffs. Evidence: late-arrival fixture produces the expected difference between current context and historical replay; unsupported history is visible, and invalid intervals are quarantined.

Completed 2026-10-24 for the fixture track. Migration `002_temporal_assertions.sql` adds assertion business keys, correction versioning, source/effective/system cutoff queries, and recursive bounded paths. The live validation proves late source availability differs from historical MarketAtlas replay, a retraction retains the prior accepted version, the affected path disappears in current context, and an unknown-availability assertion is returned as `unsupported_history`. Evidence: `reports/t006-validation.md`.

### [x] T-007 — Implement observation versions and availability selection

Owner: data engineer / quant. Dependencies: T-004, T-005. Maps: REQ-005, REQ-006, NFR-002, NFR-003 → AC-005, AC-006, AC-014, AC-015.

Implement calendar, measure/unit, adjustment, release/vintage, and cutoff contracts. Retain immutable permitted inputs or reproducible immutable source references. Evidence: macro revision and future-release fixtures select only eligible versions; unsupported adjusted-history/availability cases are withheld or labeled descriptive; manifests reproduce input selection.

Completed 2026-10-24 for the fixture track. Migration `003_observation_versions.sql` adds `input_manifest`, calendar sessions, versioned market and macro observations, and cutoff-aware query functions. The live validation confirms an initial macro vintage at the early cutoff and the later revision only after its availability time; it excludes a not-yet-available market observation, labels an unsupported adjusted-history probe, and reproduces the fixture manifest hash. Evidence: `reports/t007-validation.md`.

### [x] T-008 — Add curated macro context

Owner: quant / mapping owner. Dependencies: T-006, T-007. Maps: REQ-007 → AC-007.

Add source-backed or curated series-country/concept mappings and a limited set of market relevance links. Record rationale, owner, effective/knowledge dates, and taxonomy/provider versions. Distinguish domicile/listing/currency facts from economic exposure. Evidence: inspectable mapping examples and explicit context labels; no curated link is presented as measured sensitivity.

Completed 2026-10-24 for the fixture track. Migration `004_curated_macro_context.sql` adds versioned mappings with explicit source/curated basis, owner, source reference, taxonomy provider/version, support assertion, temporal fields, input manifest, and the required `context_only_not_measured_sensitivity_or_causality` label. The fixture validation exposes source-backed country and concept mappings plus a curated sector mapping, verifies complete provenance, and rejects an invalid country-to-instrument context mapping. Evidence: `reports/t008-validation.md`.

### [x] T-009 — Implement bounded rolling correlations

Owner: quant implementation engineer. Dependencies: T-007. Maps: REQ-008, NFR-002, NFR-003 → AC-008, AC-014, AC-015.

Implement the configured pair list, common session grid, transformed returns, fixed 60-session window/minimum 45 paired observations, canonical pair IDs, and explicit undefined statuses. Record method/input/window metadata. Evidence: independent numerical comparison within declared tolerance; missing data does not expand windows; constant/incompatible/asynchronous inputs are handled explicitly; future observations cannot enter earlier cutoffs.

Completed 2026-10-24 for the fixture track. Migration `005_rolling_correlation_estimates.sql` adds versioned, canonical instrument-pair estimates with the fixed 60-session/45-pair contract, method/configuration hashes, input selection hash, availability cutoff, and explicit supported/undefined statuses. The fixture validation persists 16 supported `I-A`/`I-B` estimates and 16 explicit zero-variance `I-A`/`I-C` outcomes; the final supported value agrees with an independent calculation within `1e-12`, missing prices do not expand the window, and a historical cutoff produces only 20 estimates whose inputs were already available. Evidence: `reports/t009-validation.md`.

## Phase C — Publish and explain

### [x] T-010 — Implement repeatable builds and atomic publication

Owner: pipeline/database engineer. Dependencies: T-006, T-007, T-008, T-009. Maps: REQ-010, NFR-002, NFR-003, NFR-005 → AC-010, AC-014, AC-015, AC-017.

Create build manifests, validation/quarantine outputs, immutable serving snapshots, atomic publication, and prior-snapshot retention. Evidence: identical inputs preserve business results without duplicates; injected build failure leaves prior publication intact; readers never see mixed snapshots. Document snapshot pinning and safe cleanup.

Completed 2026-10-24 for the fixture track. Migration `006_build_publication.sql` adds immutable build runs, serving snapshots, a single publication pointer, a snapshot-pinned correlation fact, and an `atlas_report.current_rolling_correlation_estimate` view. Builds record input manifest, cutoff, configuration hash/payload, code revision/dirty state, Python environment, validation summary, and output hash. The live validation published 32 rows from one snapshot, reused that snapshot on identical input, and recorded an injected failure without rows or publication-pointer change. Evidence: `reports/t010-validation.md`.

### [x] T-011 — Implement reporting outputs and provenance

Owner: database / BI engineer. Dependencies: T-010. Maps: REQ-009, REQ-011 → AC-009, AC-011.

Create grain-documented dimensions/facts/bridges, bounded paths, quality/freshness, and provenance outputs. Bind all queries to one report snapshot and its temporal cutoffs. Evidence: source-row reconciliation and no multiplied observations/pairs under multi-membership; one sourced edge, curated link, and estimate trace to original evidence and build. SQL evidence alone does not pass Power BI acceptance.

Completed 2026-10-24 for the fixture track. Migration `007_reporting_provenance.sql` materializes snapshot-pinned node, relationship, macro-context, bounded-path, and provenance reporting tables, with current views resolving only through the publication pointer. The live report validation found 15 nodes, 14 relationship facts, 3 context facts, 24 bounded paths, 32 correlation facts, and 49 provenance records in one snapshot. It reconciles endpoint joins without multiplying correlations and traces one sourced edge, one curated mapping, and one estimate to the build/input/method evidence. Evidence: `reports/t011-validation.md`, `reporting.md`.

### [x] T-012 — Implement and exercise demo report (React)

Owner: frontend / BI engineer. Dependencies: T-011 and supported frontend runtime. Maps: REQ-009, REQ-011 → AC-009, AC-011.

Build market-map, macro-context, correlation, and provenance/quality pages using explicit relationships and standard visuals. Pin a single snapshot across refresh queries. Evidence: actual semantic-model/report artifacts, filter and distinct-count reconciliation, valid as-of labels, drill-through, and refresh behavior. Retain screenshots from the synthetic demonstration. The user selected the React implementation in ADR-001; Power BI acceptance remains pending until separately exercised.

Completed 2026-10-24 for the fixture demo. The independent `frontend/` application uses React, TypeScript, Vite, React Router, Zustand, and Tailwind in the QuantMeridian scaffold pattern. Its current focused evidence workspace replaces the permanent navigation rail with a selected MarketAtlas graph lens, explicit source/review/candidate/context treatments, provenance drawer, scoped-evidence modal, and opt-in candidate-review queue. It remains fixture-only and prohibits browser-to-PostgreSQL access. Typecheck, four frontend fixture tests, and production build pass. Evidence: `reports/t012-validation.md`, `frontend/README.md`. AC-009 remains partial because Power BI has not been exercised.

## Phase D — Validate and hand off

### [x] T-013 — Execute release validation and performance checks

Owner: validation engineer / quant reviewer. Dependencies: T-010, T-011; T-012 for BI evidence. Maps: NFR-001, NFR-002, NFR-003, NFR-004, NFR-005 → AC-013, AC-014, AC-015, AC-016, AC-017.

Run meaningful role-scope, integrity, temporal, reproducibility, numerical, publication-failure, and recovery checks. Benchmark the documented fixture envelope on declared hardware; retain build time and at least 20 runs per prepared query with cache policy and p95. Proposed targets: build under 5 minutes and query p95 at most 2 seconds. Evidence: actual results/defects in the acceptance register; adjust targets explicitly before release if justified. Never fabricate passing evidence.

Completed 2026-10-26 for the local fixture and approved live-catalog envelope. `market-atlas release validate --samples 20` verifies role boundaries, source-contract drift, graph/temporal/observation/context/numerical fixture guards, deterministic fixture publication, injected-failure recovery, report grains, and the published 290-series/11-concept catalog surface. It benchmarks prepared catalog-summary and 50-series category-neighborhood queries on one warm local PostgreSQL connection. The measured fixture build was 0.188182 seconds; p95 was 0.000161 seconds and 0.000964 seconds respectively, both inside the documented targets. Validation exposed and corrected a fixture-report provenance check that mixed independent publication snapshots; it now pins provenance to the selected fixture snapshot. Evidence: `reports/t013-release-validation.md`, `data/generated/t013_release_validation.json` (local ignored output), and `tests/test_release_validation.py`. This is local-envelope evidence, not a production capacity guarantee; public release-artifact review, Power BI acceptance, named owners, scheduling, and broader source ownership/rights remain open.

### [x] T-014 — Finish contributor demo, extension design, and handoff

Owner: maintainer / implementation engineer. Dependencies: T-011, T-013; T-012 for a release claiming Power BI completion. Maps: REQ-002, REQ-012, NFR-001, NFR-005, NFR-006 → AC-002, AC-012, AC-013, AC-017, AC-018.

Replace planned setup commands with exercised commands; complete clean-room fixture walkthrough, actual screenshots, license/data notices, owner/refresh/recovery details, and synthetic securities-finance extension contract. Update README, roadmap, and handoff with real status. Evidence: new-contributor walkthrough and reviewed mappings/permissions; all public claims match implemented capabilities.

Completed 2026-10-26 for the portable fixture/design handoff scope. A `git archive` fresh checkout exercised the credential-free fixture build, validate, cutoff inspection, and all 49 Python tests without upstream credentials or a database. Local browser walkthroughs captured the fixture graph, live 290-series/11-concept catalog, and a Regional category page; the live canvas was revised to request 12 visual nodes per page, grid cards, and suppress repeated detail-edge labels while retaining the independently benchmarked 50-row API contract. The handoff adds contributor, license/data, operations/recovery, and restricted securities-finance extension documents. Scheduled-pilot ownership, alerting, source redistribution approval, restricted deployment, and Power BI remain explicitly uncompleted. Evidence: `reports/t014-contributor-handoff.md`, `docs/contributor-demo.md`, `docs/data-and-license-notice.md`, `docs/operations.md`, and `docs/securities-finance-extension.md`.

### [ ] T-015 — Exercise the Power BI fixture report

T-022 adds generated native projects and a working actual-data browser report;
the Power BI refresh/render/drill-through acceptance exercise is still open.

Owner: BI engineer / report owner. Dependencies: T-011, T-013. Maps: REQ-009, REQ-011 → AC-009, AC-011.

Open the tracked `powerbi/MarketAtlas.model.template.tmdl` in an authorized Power BI Desktop or Power BI service environment, set one captured fixture snapshot UUID, create the five report pages, and retain the PBIP/PBIR source plus screenshots. Prove filter/reset reconciliation, distinct-count grain safety, as-of/freshness labels, and drill-through for sourced relationship `A11`, curated context `CTX3`, and one correlation. Evidence: an executed Power BI report/artifact and reconciliation results; a source template or SQL-only validation does not pass AC-009.

Progress 2026-10-26: a source-controlled TMDL template, report design, snapshot-pinning protocol, fixture reconciliation script, cache ignore rules, and Python contract tests exist. Local macOS has no Power BI Desktop, and the Power BI service requires sign-in, so no Power BI visual/refresh evidence is claimed. Evidence: `powerbi/README.md`, `powerbi/MarketAtlas.model.template.tmdl`, `tests/test_powerbi_contract.py`, and `reports/t015-powerbi-source-package.md`.

### [x] T-016 — Add restricted revision-quality source context

Owner: Josh / project owner. Dependencies: T-001, T-004C.1. Maps: REQ-001, REQ-006, NFR-001 → AC-001, AC-006, AC-013.

Promote a current revision-quality interface only after an explicit local-owner and restricted-use decision. Verify schema drift and source read-only access; extract only configured IDs in bounded batches and never treat a missing summary as zero revisions.

Completed 2026-10-26. `gold.v_series_revision_summary` is the sixth supported-live source contract. The read-only verification passed with no write privileges, and the configured three-series extract returned three summaries and no missing IDs. The output is a generated ignored file; nothing was loaded to `atlas` or published. Evidence: `docs/t016-revision-quality-spec.md`, `reports/t016-source-governance-discovery.md`, `docs/source-onboarding-decision.md`, and `tests/test_revision_summary_contract.py`.

### [x] T-017 — Publish restricted revision-quality context

Owner: Josh / project owner. Dependencies: T-016, T-004C.3–.5. Maps: REQ-006, REQ-010, REQ-011, NFR-001, NFR-003, NFR-005 → AC-006, AC-010, AC-011, AC-013, AC-015, AC-017.

Completed 2026-10-26 for the configured local internal-only scope. Migration 011
adds captured quality versions and a separate snapshot-pinned publication.
Checksum/contract/rights/temporal validation precedes writes. Missing source
summaries produce explicit unknown rows with null metrics. The selected-series
API reads only report surfaces; the live workspace shows quality and separate
snapshot/input/build provenance. A three-series extract published successfully
and an identical rerun reused its snapshot. Rollback-isolated PostgreSQL tests
prove idempotency, missingness, failure retention/recovery, old snapshot replay,
publication isolation and reader permissions. Browser checks cover metrics,
provenance, unselected coverage and outage/recovery. No source interface or
public redistribution right was added. Evidence:
`docs/t017-revision-quality-publication-spec.md`,
`reports/t017-revision-quality-publication-validation.md`,
`tests/test_revision_quality_publication.py`,
`tests/test_revision_quality_database.py`.

### [x] T-018 — Generate portable Power BI data packs and report guides

Owner: Josh / project owner; implementation: Codex. Dependencies: T-003,
T-011, T-016/T-017 for the optional live quality surface. Maps: REQ-002,
REQ-009, REQ-010, REQ-011, NFR-001/002/003/005/006 → AC-002/009/010/011/013/014/015/017/018.

Completed 2026-10-30 for local export and source-guide scope. The credential-free
job calculates the canonical fixture's 32 estimates and exports dimensions,
relationship/context facts and provenance. The published-data job reads only
allowlisted report snapshot tables under the report-reader role in one
repeatable-read, read-only transaction. Immutable CSV packs include typed schemas,
hashes, counts and primary keys; validation rejects mixed snapshots, corrupt
files, duplicate/orphan keys, missing core provenance and invalid null/numeric
states. A Power Query loader, model/DAX/report recipes and synthetic-only GitHub
workflow source accompany the jobs. The four local publications passed a
read-only export smoke test. Power BI authoring snippets and GitHub execution
remain unexercised; no scheduler or service refresh was configured. T-015 and
AC-009 remain open. Evidence: [T-018 validation](../reports/t018-powerbi-data-jobs-validation.md),
[data jobs](../powerbi/guides/data-jobs.md), [report recipes](../powerbi/guides/report-recipes.md),
and `tests/test_powerbi_export.py`.

### [x] T-019 — Name the synthetic publication explicitly and document access

Owner: Josh / project owner; implementation: Codex. Dependencies: T-010, T-018.
Maps: REQ-009/010/011, NFR-001/005/006 → AC-009/010/011/013/017/018.

Completed 2026-10-30. Producers, export selections, Power BI source and current
documentation use `synthetic_fixture`. Migration 012 renames only the legacy
publication pointer, rejects collisions and prevents legacy-name recreation;
it preserves retained snapshots/builds and publication timestamps. Local
application preserved all four snapshot IDs/timestamps and the three real-data
publications. Rollback-isolated database tests cover repeat application,
collision refusal and reader access; published exports pass with the new name.
The [access guide](publication-access.md) and
[read-only SQL](../sql/queries/publications.sql) locate the registry and report
views. Evidence: [T-019 validation](../reports/t019-publication-rename-validation.md).
T-015/AC-009 remains open.

### [x] T-020 — Orchestrate daily real-data PostgreSQL refreshes with Dagster

Owner: Josh / project owner; implementation: Codex. Dependencies: T-004B/C,
T-016–T-019. Maps: REQ-006/009/010/011, NFR-001/002/003/005/006 →
AC-006/009/010/011/013/014/015/017/018.

Completed 2026-10-30 for local orchestration/runtime scope. The optional pinned
Dagster environment exposes the 13-stage real refresh and a separate synthetic
smoke job. Dates roll by the New York run date; source contracts gate reads,
retries reuse captured inputs, and PostgreSQL lock exclusion prevents overlapping
refreshes. A successful live run refreshed three publications and validated a
real Power BI pack. The local development UI/daemon is running; the daily
18:30 schedule is defined and stopped. Upstream FRED ingestion, Power BI service
refresh, alerts and production service installation remain outside this work.
See [the runbook](dagster-orchestration.md),
[T-020 evidence](../reports/t020-dagster-orchestration-validation.md), and
`tests/test_orchestration.py`. T-015/AC-009 remains open.

### [x] T-021 — Recover native Dagster downstream re-execution

Owner: Josh / project owner; implementation: Codex. Dependencies: T-020.
Maps: REQ-010/011, NFR-002/003/005 → AC-010/011/014/015/017.

Completed 2026-10-30 for local recovery scope. Parent checkpoints restore verified
captures and completed prerequisites, preserve original dates, and retain child/root
lineage. Database/publication changes and incompatible/missing captures fail safely.
Native Dagster failure-to-child re-execution passed against the real PostgreSQL
pipeline without repeating the completed seven stages. Evidence:
[T-021 validation](../reports/t021-dagster-recovery-validation.md).

### [x] T-022 — Author native report projects and provide browser access

Owner: Josh / report owner; implementation: Codex. Dependencies: T-018, T-020.
Maps: REQ-009/011 → AC-009/011 (supplementary; AC-009 remains partial).

Completed 2026-10-30 at source-generation and local-browser scope. A reproducible
PBIP/PBIR/model generator authors five pages for fixture or actual macro packs.
Both native projects passed official report JSON schemas and binding checks.
An actual-data browser report passed concept/quality filter-reset and evidence
checks and runs locally without a Power BI account. No native Power BI engine
execution or cross-page drill-through is claimed. Evidence:
[T-022 validation](../reports/t022-report-project-validation.md),
[usage instructions](../powerbi/guides/generated-reports.md). T-015 remains open.

## Completion rules and coverage

A task is complete only when its deliverable exists, required review/validation evidence is retained, relevant acceptance rows are updated, and documentation matches actual behavior. Downstream code may progress against fixture contracts while optional upstream integrations remain unavailable; do not collapse those statuses.

The plan's requirement matrix maps all 12 functional and 6 non-functional requirements to these tasks and all 18 acceptance criteria. Acceptance evidence belongs in `docs/acceptance.md`, with links to permitted reports, manifests, or artifacts. All v0.1 Must criteria require passing evidence or an explicitly reviewed scope revision before a completed-release claim. Maintain one exact next task and owner in the handoff after each work session.
