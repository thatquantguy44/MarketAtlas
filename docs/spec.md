# MarketAtlas — Product Specification

Status: candidate v0.1 specification, prepared for review on 2026-10-24. Implementation, database discovery, and acceptance execution have not started. This document is the source of truth for scope and acceptance; [plan.md](plan.md), [tasks.md](tasks.md), [handoff.md](handoff.md), and [roadmap.md](roadmap.md) describe proposed delivery.

## Request and purpose

Build a general market knowledge graph on PostgreSQL, reuse the user's MacroMedallion / EcoMedallion work where verified, and expose useful market, macro, and relationship views through Power BI before adding securities-finance domains.

MarketAtlas helps a quant follow relationships across instruments, issuers, classifications, and economic series while inspecting where each connection came from and when it was known. Its public demonstration should make that value understandable without access to a private repository, database, or licensed dataset.

The engineering deliverable is a reusable graph foundation and report-ready outputs. The research question is whether relationship context reduces manual joins and improves explainability. Investment alpha, causal transmission, and decision performance require separate research and are not acceptance claims for this project.

## Users and initial questions

| User | Question | Expected outcome |
| --- | --- | --- |
| Quant or data scientist | Which instruments share an issuer, sector, country, currency, or index? | Inspect a sourced path and distinguish missing mappings from confirmed links. |
| Macro researcher | Which economic series describe a selected country or economic concept, and which instruments have a curated relevance link? | Explore contextual mappings with units, freshness, and mapping rationale. |
| Analyst | Which configured instrument pairs changed their rolling return correlation? | Compare dated estimates with sample counts, methodology, and source lineage. |
| Power BI consumer | Why does this connection or number appear? | Drill through from a displayed relationship to its source and build. |

## Scope and release boundary

The v0.1 pilot includes a market entity map, curated macro context, one bounded family of rolling instrument-return correlations, PostgreSQL serving outputs, a reproducible synthetic demonstration, and a Power BI semantic/report specification with a report implementation when the supported authoring environment is available. A PostgreSQL demo does not depend on Power BI being installed; Power BI acceptance remains a separate, unpassed criterion until exercised in Power BI.

Proposed sizing envelope, subject to discovery: up to 50 instruments, 25 macro series, two years of daily market history, and at most 300 configured instrument pairs. These are design targets, not verified current coverage or performance. Macro history may have a lower frequency and different revision structure.

Later scope includes beta estimation, timestamped event context and event studies, broader asset coverage, and securities-finance views. The first pilot excludes arbitrary report-time graph traversal, causal claims, trading execution, dense all-pairs estimation, and restricted bank/client/counterparty/position data in the public demonstration.

## Existing systems and evidence status

The user identified **MacroMedallion / EcoMedallion** and a **PostgreSQL database** as integration assets. Repository URLs, exact names, whether these are separate repositories or related versions, contents, data ownership, access, source licenses, database schemas, and deployment conventions have not been inspected. Discovery must resolve them before an upstream integration is represented as working.

The public fixture path is independently runnable. Verified upstream integrations consume existing interfaces or tables under explicit contracts; adaptation choices belong in the plan. Missing dependencies must produce an honest fixture-only or blocked integration status.

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
| Analytical connection | Canonical pair, method/version, transformation, window, information cutoff, aligned observation dates or their reproducible identity, estimate/undefined reason, sample count, quality status, and run/input snapshot. |
| Serving publication | Snapshot identity, publication time, input/run identities, view grain and keys, completeness and quality state, freshness measures and provenance references. |

Business effective time answers when a relationship applies. Availability time answers when the underlying information became usable. Record time answers when this system captured or changed it. These timestamps are not interchangeable. Historical membership and historical macro vintages are required for a historical-as-known claim; where unavailable, the output must say current/latest-context or unsupported history.

Reference, curated-context, and analytical connections must be visibly distinguishable. A numerical correlation must not inherit the truth status of a sourced issuer relationship. Repeated values introduced by forward filling low-frequency macro series must not be treated as fresh independent observations in the v0.1 return-correlation family.

## Dependencies and ownership

Roles below are proposed assignments, not confirmations of actual people or approval.

| Dependency | Owner role | Required before |
| --- | --- | --- |
| Repository identity and accessible interfaces | Project maintainer / upstream maintainer | Upstream adapter implementation |
| PostgreSQL scope, roles, and migration convention | Database owner | Any integration writes |
| Source redistribution and usage terms | Source owner / project maintainer | Public real-data fixture or publication |
| Identity, ontology, and curated mapping rules | Quant/data owner | Reference-map acceptance |
| Returns, timing, and correlation methodology | Quant owner | Analytical acceptance |
| Power BI authoring, gateway, and semantic model environment | BI owner | Power BI execution acceptance |
| Synthetic fixture and public repository packaging | Project maintainer | Public demonstration acceptance |

## Constraints & Risks

| ID | Risk | Required response |
| --- | --- | --- |
| RISK-001 | Named repositories or database tables differ from assumptions or are unavailable. | Record verified interfaces first; retain independent fixture execution and report integration status truthfully. |
| RISK-002 | Latest classifications or revised macro values create historical leakage. | Retain validity/availability history; reject unsupported historical-as-known claims. |
| RISK-003 | Correlations in raw levels, stale data, asynchronous closes, or mixed return definitions mislead consumers. | Restrict v0.1 to compatible instrument returns with explicit alignment and diagnostic rules. |
| RISK-004 | Multi-valued classifications or membership links multiply Power BI facts. | Declare grain and key rules; validate counts against source populations and make filter semantics explicit. |
| RISK-005 | Private data or connection metadata enters a public portfolio repository. | Use labeled synthetic examples; require documented redistribution rights for any real-data artifact. |
| RISK-006 | A graph visualization becomes the only demonstration of utility. | Demonstrate explainable SQL/report questions and provenance paths using standard Power BI visuals and tables. |
| RISK-007 | Planning documents are mistaken for a working or production-ready system. | Maintain explicit lifecycle status and unpassed acceptance evidence; make public claims match completed work. |

## Success measures and definition of done

Track resolved identity coverage, invalid/quarantined relationships, orphan/duplicate counts, freshness, successful/failed builds, input reproducibility, and report latency. Measure usefulness by completing the three user questions against declared examples with inspectable provenance; record observed task duration and user feedback without inventing a baseline benefit.

The documentation package is complete when its requirements, proposed plan, tasks, handoff, roadmap, and public claims agree. The implemented v0.1 is complete only when all Must acceptance criteria below have actual passing evidence, open blocking risks have an owner/resolution, and the maintainer records release review. Documentation completion does not advance the implementation or validation gates.

## Open Questions

| ID | Question | Proposed owner | Timing |
| --- | --- | --- | --- |
| Q-001 | Are MacroMedallion and EcoMedallion distinct repositories, versions, or one project, and what are their exact URLs? | Project maintainer | Discovery |
| Q-002 | What interfaces, canonical IDs, PostgreSQL objects, privileges, and refresh patterns exist? | Upstream/database owners | Discovery |
| Q-003 | Which data retain historical identifier/classification states and macro vintages, and when were they available? | Data/quant owner | Before historical claims |
| Q-004 | Which sources and derived outputs may be redistributed publicly? | Source owner | Before real-data publication |
| Q-005 | Which pilot universe, eligible pair list, calendars, and return definitions are supported? | Quant owner | Method design |
| Q-006 | Which Power BI authoring/connectivity options and standard visuals are available? | BI owner | BI design |
| Q-007 | Who accepts performance targets and retains build artifacts/input snapshots? | Maintainer/database owner | Pilot setup |

## Acceptance Criteria

All criteria are **planned / not executed** as of this document. “Evidence” means a retained output or inspection from implementation; the statements below are instructions for future validation.

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
