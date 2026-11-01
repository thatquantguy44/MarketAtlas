# MarketAtlas — Product Specification

Status: candidate v0.1 specification, prepared for review on 2026-10-24; reconciled with the current handoff on 2026-11-01 against retained evidence through 2026-11-01. T-001–T-003, T-005–T-014, T-016–T-030 are complete at their stated fixture, design, restricted-local or research scope. Broader T-004 adapters and T-015 Power BI execution remain open; the v0.1 release is incomplete. This document is the source of truth for scope and acceptance; [plan.md](plan.md), [tasks.md](tasks.md), [handoff.md](handoff.md), and [roadmap.md](roadmap.md) describe delivery status and proposed work. Actual acceptance status is recorded in [acceptance.md](acceptance.md).

## Request and purpose

Build a general market knowledge graph on PostgreSQL, reuse the user's local MacroMedallion (also called EcoMedallion) asset where verified, and expose useful market, macro, and relationship views through the React demonstration and documented Power BI outputs before adding securities-finance implementations. The React delivery decision is recorded in [ADR-001](decisions/001-quantmeridian-react-scaffold.md); Power BI execution remains required for AC-009.

MarketAtlas helps a quant follow relationships across instruments, issuers, classifications, and economic series while inspecting where each connection came from and when it was known. Its public demonstration should make that value understandable without access to a private repository, database, or licensed dataset.

The engineering deliverable is a reusable graph foundation and report-ready outputs. The research question is whether relationship context reduces manual joins and improves explainability. Investment alpha, causal transmission, and decision performance require separate research and are not acceptance claims for this project.

## Users and initial questions

| User | Question | Expected outcome |
| --- | --- | --- |
| Quant or data scientist | Which instruments share an issuer, sector, country, currency, or index? | Inspect a sourced path and distinguish missing mappings from confirmed links. |
| Macro researcher | Which economic series describe a selected country or economic concept, and which instruments have a curated relevance link? | Explore contextual mappings with units, freshness, and mapping rationale. |
| Analyst | Which configured instrument pairs changed their rolling return correlation? | Compare dated estimates with sample counts, methodology, and source lineage. |
| Report consumer (React / Power BI) | Why does this connection or number appear? | Drill through from a displayed relationship to its source and build. |

## Scope and release boundary

The v0.1 pilot includes a market entity map, curated macro context, one bounded family of rolling instrument-return correlations, PostgreSQL serving outputs, a reproducible synthetic demonstration in the React workspace, and a Power BI semantic/report package to be exercised in an authorized authoring environment. The React fixture demonstration and restricted-local live macro graph are implemented. The Power BI package includes a TMDL template, a five-page PBIP/PBIR project generator and a verified local actual-data browser report. Generated native source remains unexecuted in Power BI. Fixture and React execution are independent of Power BI availability; AC-009 remains partial until actual Power BI execution supplies the required evidence.

The proposed analytical sizing envelope remains up to 50 instruments, 25 macro series, two years of daily market history, and at most 300 configured instrument pairs. These are design targets, not verified analytical coverage. Macro history may have a lower frequency and different revision structure. The validated synthetic report has 15 nodes, 14 relationship facts, 3 curated contexts, and 32 correlation estimates. Separately, the restricted descriptive catalog has 290 series and 11 taxonomy concepts; the expanded point-in-time observation ingestion has evidence for 267 series and 127,907 versions, and captured-current revision-quality publication for 268 selected summaries. Eligibility and exclusions are recorded in [series coverage](series-coverage.md). Catalog membership does not imply observation ingestion, analytical eligibility, or quality-summary selection for every series. See [tasks](tasks.md), [Power BI reconciliation](../powerbi/README.md#ac-009-reconciliation-script), and [the handoff](handoff.md).

Later scope includes beta estimation, historical event/revision reconstruction and event studies, broader analytical asset coverage, and securities-finance implementations. Current scheduled-release context and captured-current revision-quality summaries are already supported at their documented restricted-local scope; neither establishes historical event reconstruction or measured market responses. The securities-finance extension contract is complete at design scope only. The first pilot excludes arbitrary report-time graph traversal, causal claims, trading execution, dense all-pairs estimation, and restricted bank/client/counterparty/position data in the public demonstration.

## Existing systems and evidence status

MacroMedallion and EcoMedallion are interchangeable names for one upstream economic-data asset. An operator may point MarketAtlas at a local checkout for discovery and lineage through the git-ignored `configs/local.toml`; MarketAtlas neither clones nor imports that checkout and does not require a remote URL, commit, or branch pin. The primary integration contract is the authorized local `macro_medallion` PostgreSQL database. Six approved live interfaces have verified read-only source contracts and bounded adapters. T-001 is complete for the local restricted scope: Josh owns the manual local pilot's source/data, database, report, methodology, refresh/recovery, and incident roles; source outputs are restricted internal-only and public sharing remains unauthorized. Broader source onboarding, public redistribution approval, and scheduled deployment remain open. See [the source catalog](source-catalog.md) and [the ownership and rights decision](source-onboarding-decision.md).

The completed fixture implementation covers canonical identities and ontology, temporal relationship replay, cutoff-aware observation versions, curated macro context, bounded rolling correlations, atomic snapshot publication, reporting/provenance outputs, release-validation evidence, and a contributor walkthrough. The implemented demonstration uses the React workspace selected in [ADR-001](decisions/001-quantmeridian-react-scaffold.md). The restricted-local live graph has retained validation for a descriptive catalog of 290 series and 11 taxonomy concepts; this catalog does not establish historical taxonomy or analytical coverage at that scale. T-017 adds an independent current revision-quality publication and selected-series UI with capture/input/build provenance; retained validation covers three configured summaries, repeat-run reuse, and failure recovery. These are recorded results through 2026-10-26, not a new live-environment validation. See [the handoff checkpoint](handoff.md#start-here-next-session) and [T-017 evidence](../reports/t017-revision-quality-publication-validation.md).

The next acceptance task is T-015 / AC-009, owned by Josh / project owner: exercise the existing Power BI source package in an authorized authoring environment and retain report, refresh, filtering/count reconciliation, and provenance evidence. AC-009 remains partial; React, SQL, and template checks do not satisfy the Power BI exercise. Broader T-004 adapters, public source-rights/artifact review, and scheduled deployment/operational readiness also remain open. Completion of the scoped tasks above does not establish a completed pilot or production release.

The public fixture path is independently runnable. Verified upstream integrations consume existing interfaces or tables under explicit contracts; adaptation choices belong in the plan. Missing dependencies must produce an honest fixture-only or blocked integration status.

T-018 adds portable Power BI CSV data jobs and report guides on 2026-10-30.
Credential-free fixture packs and read-only exports of existing report
publications include typed schemas, checksums, row counts, keys and provenance.
Local file validation and a four-publication database export passed; the M/DAX
guides and synthetic GitHub workflow remain unexecuted in their target hosts.
No scheduler or Power BI service refresh was configured. See [data jobs](../powerbi/guides/data-jobs.md),
[report recipes](../powerbi/guides/report-recipes.md), and
[T-018 evidence](../reports/t018-powerbi-data-jobs-validation.md). These outputs
support REQ-002/009/010/011 and the existing acceptance chain; AC-009 remains
partial pending T-015.

T-019 names the synthetic database publication `synthetic_fixture`. Migration
012 preserves the existing pointer's snapshot and timestamp; the three actual
macro publications are unchanged. [Publication access](publication-access.md)
documents the report registry and view mapping. Historical build manifests and
export packs retain the names recorded at their creation.

T-020 adds optional Dagster orchestration for the existing PostgreSQL sources:
rolling observation/release windows, contract gates, a full-catalog graph refresh,
selected revision quality, and a validated real Power BI pack. A local 13-stage
run passed on 2026-10-30. The development UI/daemon is available with a stopped
18:30 New York schedule definition; upstream API ingestion, Power BI service
refresh and production scheduling remain separate. See [the runbook](dagster-orchestration.md)
and [evidence](../reports/t020-dagster-orchestration-validation.md).

T-021 validates native Dagster recovery from a failed stage using verified parent
captures and completed prerequisites. T-022 authors native fixture/actual-data
report projects and provides an actual-data browser report without requiring a
Power BI account. Native JSON Schema and browser checks passed; Power BI refresh,
rendering and drill-through remain unexecuted. See [recovery evidence](../reports/t021-dagster-recovery-validation.md)
and [report evidence](../reports/t022-report-project-validation.md).

T-023–T-025 add local report delivery, supervised macOS Dagster operation and
all eligible approved FRED selections. The 14-stage job updates the existing
report only after pack validation, preserves the previous report on failure and
shows refresh/source status. The local daily schedule is verified running at
18:30 New York; a service-launched refresh passed. Observation eligibility is
94 series with valid source-vintage dates; current coverage/quality includes 268
FRED series. The descriptive graph remains 290 series. No upstream APIs or source
writes were added. Production hosting and native Power BI execution remain open.
See [local automation](local-automation.md), [series coverage](series-coverage.md)
and [evidence](../reports/t023-t025-automation-series-validation.md).

T-026 adds a read-only source-health CLI/manual Dagster job and separately scoped
execution-audit contracts. It reconciles source-age flags, polling attempts and
intentional current-only vintage policy. T-027 completes the explicitly authorized, reversible upstream repair for the
2024–October 2026 window. Validated admission is 267 series / 127,907 versions;
one series remains current-only because FRED has no ALFRED history. All 23 remaining
period-age flags matched current provider periods. Corrections retain old system-time
versions, and repeated ingestion inserts/corrects zero after exact Decimal binding. See [recovery](source-health-recovery.md).

## Macro research extension

T-028/T-029 add an independent, user-authorized macro research path alongside
the v0.1 instrument-return family. Ten explicitly configured monthly/daily series
produce source-date-cutoff panels and immutable local JSON/CSV packs with rolling
correlation, correlation distance/change, standardized group dispersion and node
divergence. Read-only validation captured 19,963 versions and produced 2,264
supported relationship estimates and 640 supported group dispersions; missing
samples and unknown vintages remain withheld. Monthly history is usable from
2010; Treasury history before 2024 remains unavailable. These results reconstruct
source histories using current metadata and fixed operator groups, not historical
taxonomy or MarketAtlas record-time replay. No new PostgreSQL publication,
browser integration, schedule, predictive validation or Power BI execution is
claimed. See the [method spec](t028-t029-macro-analytics-spec.md),
[runbook](macro-analytics.md) and [validation](../reports/t028-t029-macro-analytics-validation.md).

T-030 adds the browser **Relationship research** tab at restricted-local scope.
It consumes a separately validated macro analytics pack, with heatmap, dispersion
timeline, divergence ranking and source/window investigation. Missing results and
independent dates remain explicit. Existing publication refreshes retain the
last research pack rather than regenerating it. Normal/narrow browser checks
passed; native Power BI and predictive acceptance remain open. See
[T-030 evidence](../reports/t030-browser-analytics-validation.md).

## v0.1 review scenario

The first demonstration uses one labeled synthetic instrument and a fixed information cutoff. A reviewer selects the instrument, follows its listing and issuer/classification links, opens one curated macro-context link to see its rationale and source, then views a configured rolling return-correlation pair at two endpoint dates. The result displays the pair, return definition, scheduled-session window, valid paired count, estimate or undefined reason, cutoff, method version, and input/build identity. The reviewer can drill from each displayed connection to its evidence and distinguish business effective time from source availability and MarketAtlas record time.

The same fixture includes a later correction or macro revision. Moving the knowledge cutoff before that availability must remove the later information from the historical-as-known view; a current-context view may show it with its later timestamp. Fixture validation and walkthrough evidence for these behaviors is retained under AC-002, AC-004–AC-008, and AC-011 in [the acceptance register](acceptance.md). The React demonstration exposes the fixture report and provenance; it does not complete the separate Power BI exercise.

T-015 must exercise the five pages in [the Power BI package](../powerbi/README.md): snapshot/quality, market map, macro context, correlation monitor, and provenance. Resolve the current synthetic `synthetic_fixture` publication immediately before refresh and pin every import to that same snapshot UUID. Reconcile the fixture counts above, prove filter/reset and distinct-count behavior, and retain provenance evidence for relationship `A11`, context `CTX3`, and one correlation. The template and SQL checks alone cannot pass AC-009.

The separate restricted-local React walkthrough selects a live macro series, follows its current taxonomy provenance, and opens revision-quality context. Graph and quality snapshots and dates are displayed independently. An unavailable quality publication, a series outside the quality selection, and a selected series with an unknown summary remain distinguishable; unknown metrics remain null. Quality outages must leave the graph usable. This walkthrough supplies current-context evidence under T-017 and does not establish historical source availability or expand Power BI acceptance.

## Functional requirements

Must means required for the v0.1 release. Should means a separately evidenced enhancement that does not silently expand v0.1. Later means roadmap scope with no v0.1 completion claim.

| ID | Priority | Requirement and purpose | Acceptance |
| --- | --- | --- | --- |
| REQ-001 | Must | Inventory the named integration assets and document exact identity, owners, interfaces, grains, refresh timing, available history, licenses, reuse decisions, and unresolved gaps. | AC-001 |
| REQ-002 | Must | Provide a self-contained synthetic demonstration with deterministic fixtures, explicit synthetic labels, provenance, and documented prerequisites; access to private upstream systems must be optional. | AC-002 |
| REQ-003 | Must | Give each entity a stable canonical identity and retain effective-dated source identifier mappings; distinguish instrument identity from exchange listing identity, and do not use ticker alone as a global identity. | AC-003 |
| REQ-004 | Must | Define supported node and relationship types, allowed endpoints, direction, and semantics; support the market map with explicit unknown and disputed mappings. | AC-004 |
| REQ-005 | Must | Preserve provenance, business validity, and knowledge history for sourced and curated relationships so current-state and historical-as-known questions are distinguishable. | AC-005 |
| REQ-006 | Must | Consume observations through contracts that identify measure, unit, frequency, calendar, adjustment/transformation, source, observation period, release/availability time, revision or vintage, and extraction time; historical claims must respect actual information availability. | AC-006 |
| REQ-007 | Must | Provide curated macro context linking series to countries/economic concepts and, where justified, instruments or classifications; expose mapping rationale, owner, source, and dates. Context links must not imply measured sensitivity or causality. | AC-007 |
| REQ-008 | Must | Produce versioned rolling correlations for a configured set of comparable instrument return pairs with documented sampling, alignment, missing-data policy, estimation window, cutoff, and diagnostics; show undefined estimates explicitly. | AC-008 |
| REQ-009 | Must | Expose bounded, documented outputs for Power BI with declared grain, keys, relationships, measures, quality/freshness indicators, and usable provenance drill-through; counts must avoid inflation from multi-valued relationships. | AC-009 |
| REQ-010 | Must | Support repeatable builds with declared adapter inputs, validated outputs, run status, and atomic publication of one consistent report snapshot; rerunning identical inputs must not duplicate business records. | AC-010 |
| REQ-011 | Must | Let consumers explain a selected edge or estimate through a source path, mapping/method version, input cutoff, input snapshot, quality result, and build identifier. | AC-011 |
| REQ-012 | Must | Document a domain extension contract that reuses canonical market entities while isolating future securities-finance entities and permissions; later domains must not require changing existing public relationship meanings. | AC-012 |

## Non-functional requirements

| ID | Priority | Requirement | Acceptance |
| --- | --- | --- | --- |
| NFR-001 | Must | Upstream integration access is read-only. Graph writes are confined to an explicitly designated PostgreSQL schema/database. Public artifacts contain synthetic or demonstrably redistributable data and no private connection details or bank records. | AC-013 |
| NFR-002 | Must | Every published analytical build is reproducible from retained input identity/checksums, configuration, transformation/method version, code revision, and dependency environment; same inputs give equivalent outputs within declared numeric tolerance. | AC-014 |
| NFR-003 | Must | Quality validation rejects or quarantines invalid identifiers, endpoints, temporal intervals, units, and unsuitable analytical inputs; published outputs have zero orphan endpoints and zero duplicate active business keys. | AC-015 |
| NFR-004 | Must | The pilot demonstrates bounded resource use at its documented sizing envelope. Proposed local targets are a complete fixture build within 5 minutes and individual prepared PostgreSQL report queries with p95 at most 2 seconds, on declared hardware and query cases. | AC-016 |
| NFR-005 | Must | A failed build leaves the previous complete serving snapshot available and records a failure reason; recovery and retirement of retained snapshots have documented owners and procedures. | AC-017 |
| NFR-006 | Must | A new contributor can follow the README and handoff to run the fixture workflow, identify remaining integration gaps, and find the spec-to-task-to-acceptance chain without institutional knowledge. | AC-018 |

## Required information contracts

These contracts define information that must survive integration; physical tables and implementation details belong in the plan.

| Contract | Required semantics |
| --- | --- |
| Entity | Type, canonical identity, display label, source identifiers, entity status, provenance; history for materially changing attributes. Include defined types for any referenced index/basket, country, currency, or economic concept. |
| Reference or curated connection | Endpoint identities, controlled relationship, provenance, source fact or curated rationale, business effective interval, source availability/knowledge timing, record history, quality status. Missing evidence is not a negative fact. |
| Market observation | Instrument, timestamp/trading date and calendar, measure, value/unit, adjustment basis, publication/availability cutoff, source record and input snapshot. Currency conversion, return and corporate-action handling are explicit. |
| Macro observation | Series, reference period, value/unit, frequency, release/availability timestamp, revision/vintage identifier and validity, source record and extraction time. Latest revised history cannot be represented as an earlier vintage. |
| Current revision-quality context | Selected series identity, supplied summary metrics or explicit unknown/nulls, source contract/record, capture time, input manifest, build and independent publication snapshot, quality/coverage status, and restricted/current-only labels. Capture time does not establish source availability or a historical vintage. |
| Analytical connection | Canonical pair, method/version, transformation, window, information cutoff, aligned observation dates or their reproducible identity, estimate/undefined reason, sample count, quality status, and run/input snapshot. |
| Serving publication | Snapshot identity, publication time, input/run identities, view grain and keys, completeness and quality state, freshness measures and provenance references. |

Business effective time answers when a relationship applies. Availability time answers when the underlying information became usable. Record time answers when this system captured or changed it. These timestamps are not interchangeable. Historical membership and historical macro vintages are required for a historical-as-known claim; where unavailable, the output must say current/latest-context or unsupported history.

Snapshot consistency applies within each publication. The synthetic `synthetic_fixture`, current `macro_context`, `macro_economic_graph`, and `macro_revision_quality` publications are independent. Consumers pin one snapshot per publication and retain its own input/build identity and dates; a combined UI must not imply a shared snapshot or capture time. The browser accesses report APIs backed only by `atlas_report` under the report-reader role and never receives database credentials. See [the reporting contract](reporting.md). Category `contains` links are navigation aids; only the returned source-backed `measures` edges are taxonomy assertions.

Reference, curated-context, and analytical connections must be visibly distinguishable. A numerical correlation must not inherit the truth status of a sourced issuer relationship. Repeated values introduced by forward filling low-frequency macro series must not be treated as fresh independent observations in the v0.1 return-correlation family.

## Dependencies and ownership

Josh accepted the roles below for the manual local pilot in [the ownership decision](source-onboarding-decision.md#approval-record) and [operations responsibility record](operations.md#responsibility-record). These assignments do not establish production readiness or authorize public redistribution. Scheduled operation still requires explicit hosting, access, backup/restore, method-change approval, freshness expectations, and alert/escalation arrangements.

| Dependency | Accountable local owner | Recorded scope / remaining gate |
| --- | --- | --- |
| Optional local upstream checkout and approved PostgreSQL interfaces | Josh / project and source owner | Six approved interfaces; any additional interface needs a separate contract and approval. Checkout is optional. |
| PostgreSQL scope, roles, and migration convention | Josh / database owner | Read-only source access and dedicated `atlas`/`atlas_report` writes verified locally; scheduled backup/restore and migration arrangements remain open. |
| Source redistribution and usage terms | Josh / source and data owner | Restricted internal-only use; public real-data publication remains unauthorized pending rights review. |
| Identity, ontology, and curated mapping rules | Josh / data and methodology owner | Fixture evidence retained; broader source mappings require their own review. |
| Returns, timing, and correlation methodology | Josh / methodology owner | Synthetic configured-pair evidence retained; analytical expansion requires method approval and eligible inputs. |
| Power BI authoring, gateway, and semantic model environment | Josh / report owner | T-015 / AC-009 remains open; authorized authoring access and a dedicated report login are required. |
| Synthetic fixture and public repository packaging | Josh / project owner | Contributor walkthrough complete; public release-artifact review remains open. |
| Refresh/recovery and incident response | Josh / local operator and incident owner | Manual execution only; scheduler, alert destination and escalation path remain undefined. |

## Constraints & Risks

| ID | Risk | Required response |
| --- | --- | --- |
| RISK-001 | Named repositories or database tables differ from assumptions or are unavailable. | Record verified interfaces first; retain independent fixture execution and report integration status truthfully. |
| RISK-002 | Latest classifications or revised macro values create historical leakage. | Retain validity/availability history; reject unsupported historical-as-known claims. |
| RISK-003 | Correlations in raw levels, stale data, asynchronous closes, or mixed return definitions mislead consumers. | Restrict v0.1 to compatible instrument returns with explicit alignment and diagnostic rules. |
| RISK-004 | Multi-valued classifications or membership links multiply Power BI facts. | Declare grain and key rules; validate counts against source populations and make filter semantics explicit. |
| RISK-005 | Private data or connection metadata enters a public portfolio repository. | Use labeled synthetic examples; require documented redistribution rights for any real-data artifact. |
| RISK-006 | A graph visualization becomes the only demonstration of utility. | Demonstrate explainable report questions, tables and provenance in the React workspace; retain the separate standard-visual and reconciliation exercise in Power BI. |
| RISK-007 | Planning documents are mistaken for a working or production-ready system. | Maintain explicit lifecycle status and unpassed acceptance evidence; make public claims match completed work. |

## Success measures and definition of done

Track resolved identity coverage, invalid/quarantined relationships, orphan/duplicate counts, freshness, successful/failed builds, input reproducibility, and report latency. Measure usefulness by completing the three user questions against declared examples with inspectable provenance; record observed task duration and user feedback without inventing a baseline benefit.

[T-013 evidence](../reports/t013-release-validation.md) meets the build/query targets for the documented synthetic fixture and current catalog using a warm local PostgreSQL connection and 20 prepared executions per query. AC-016 passes at that local envelope only; the larger analytical design targets, production concurrency, and cold-cache performance are not established. A daily Dagster schedule is defined and stopped; no automated freshness SLA or production service is configured.

The documentation package is complete when its requirements, proposed plan, tasks, handoff, roadmap, and public claims agree. The implemented v0.1 is complete only when all Must acceptance criteria below have actual passing evidence, open blocking risks have an owner/resolution, and the maintainer records release review. Documentation completion does not advance the implementation or validation gates.

## Discovery decisions and open questions

Question IDs are retained for traceability. Resolutions below are limited to the recorded local scope.

| ID | Status and decision / remaining question | Owner | Timing / evidence |
| --- | --- | --- | --- |
| Q-001 | Resolved: MacroMedallion and EcoMedallion name the same upstream asset. Optional local-checkout discovery does not require a remote URL or revision pin. | Josh / project owner | [Source catalog](source-catalog.md) |
| Q-002 | Resolved for the six approved interfaces and local role scope. Additional objects need explicit contracts; broader adapters and scheduled refresh arrangements remain open. | Josh / source and database owner | Before additional onboarding; [catalog](source-catalog.md), [contract registry](../contracts/source_contracts.toml) |
| Q-003 | Partial: fixture temporal replay and bounded live macro vintages are evidenced. Current taxonomy and captured quality do not establish historical classification or revision-event reconstruction. What additional historical coverage can an approved source support? | Josh / data and methodology owner | Before broader historical claims; [acceptance](acceptance.md), [reporting contract](reporting.md) |
| Q-004 | Local decision recorded: source-derived outputs are restricted internal-only; public examples use synthetic fixtures. Which provider terms would permit any future public real-data or derived-output publication? | Josh / source owner | Before public real-data publication; [rights decision](source-onboarding-decision.md) |
| Q-005 | Fixture universe, configured pairs, synthetic weekday calendar and adjusted-price inputs are documented. Which real-market universe, holiday calendars and return definitions may be approved for broader analytics? | Josh / methodology owner | Before analytical expansion; [fixture contract](fixtures.md), [plan](plan.md) |
| Q-006 | Open: which authorized Power BI Desktop or suitable service authoring environment and dedicated report login can execute T-015? The last recorded macOS session had neither Desktop nor an authenticated service workspace. | Josh / report owner | Next acceptance task; [handoff](handoff.md#execute-t-015-next), [Power BI package](../powerbi/README.md) |
| Q-007 | Local owner assigned and performance evidence retained. What hosting, input/artifact retention, backup/restore and alert/escalation arrangements are required before scheduling? | Josh / project and database owner | Before scheduled operation; [performance evidence](../reports/t013-release-validation.md), [operations](operations.md) |

## Acceptance Criteria

Criteria below define release-level passing conditions. Actual status and retained implementation evidence are recorded in [acceptance.md](acceptance.md); specification text alone is not evidence.

| ID | Maps to | Passing condition and evidence |
| --- | --- | --- |
| AC-001 | REQ-001 | Inventory names verified assets and interfaces, grains, owners, license/history gaps, and reuse decisions; unresolved items remain explicit. |
| AC-002 | REQ-002 | A contributor runs the documented fixture workflow without upstream credentials or live vendor calls; deterministic fixture manifest and outputs are retained and marked synthetic. |
| AC-003 | REQ-003 | Repeated fixture loads preserve canonical IDs; a fixture with changed source ticker resolves to one intended entity across valid intervals; ambiguous mappings are flagged. |
| AC-004 | REQ-004 | Every pilot relationship has documented semantics and valid endpoint types; invalid type cases are rejected; the market-map questions return expected fixture paths and unknown/disputed states. |
| AC-005 | REQ-005 | A late-arriving or corrected reference fact produces different current and prior knowledge-cutoff answers without rewriting history; missing historical coverage is visibly unsupported. |
| AC-006 | REQ-006 | A macro revision fixture selects the vintage available at each cutoff, rejects latest-only historical inference, and retains units/calendars/return-adjustment metadata; later releases cannot enter earlier calculations. |
| AC-007 | REQ-007 | Macro context exposes series-to-country/concept mappings and selected curated market links with rationale, source/owner, dates, and a context label; none is represented as a measured sensitivity. |
| AC-008 | REQ-008 | Configured valid return-pair estimates match an independent calculation within a declared tolerance; insufficient sample/zero variance/missing-data cases give explicit statuses and preserve window, sample count, and cutoff. |
| AC-009 | REQ-009 | Power BI exercise demonstrates entity/macro/pair filters, as-of/freshness, and provenance drill-through; a fixture with multiple classifications does not inflate instrument counts or analytical facts. Retain semantic model/report evidence separately from SQL-only evidence. |
| AC-010 | REQ-010 | Rerunning a successful identical input snapshot preserves business results without duplicate active records; readers see only a complete published snapshot, never mixed failed/successful output. |
| AC-011 | REQ-011 | At least one sourced edge, one curated mapping, and one correlation can each be traced from a serving row to source/input snapshot, rule or method version, cutoff, and run. |
| AC-012 | REQ-012 | Extension design shows how restricted client/agreement/loan/collateral entities reference existing instruments while preserving public outputs and independent permission boundaries. |
| AC-013 | NFR-001 | Role inspection and negative write checks demonstrate upstream read-only access and scoped graph writes; public artifact review finds no private records, credentials, or unapproved data. |
| AC-014 | NFR-002 | A retained run manifest rebuilds equivalent outputs from the same fixture or permitted snapshot using declared versions, seed and numeric tolerance. |
| AC-015 | NFR-003 | Invalid fixture cases are rejected/quarantined with reasons; published orphan and duplicate-active-key counts are both zero; unsuitable analytical inputs are not silently used. |
| AC-016 | NFR-004 | Document hardware, scale, query cases, cache conditions, and timings; at least 20 executions per report query meet the proposed p95 target and the fixture build meets its target, or record an accepted target revision before release. |
| AC-017 | NFR-005 | An induced failed build leaves the prior serving snapshot unchanged, records a useful failure state, and can be recovered using the handoff procedure. |
| AC-018 | NFR-006 | A contributor follows the README/handoff fixture steps and can locate every requirement's plan/task/evidence mapping; record any corrections needed and keep unfinished commands clearly labeled planned. |
