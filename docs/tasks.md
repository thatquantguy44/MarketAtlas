# MarketAtlas — Implementation Tasks

Status: active task plan, 2026-10-24. T-005 through T-012 are complete for the synthetic fixture track. T-001 and T-004 remain in progress; T-002 and T-003 have partial implementation evidence. A checked task is not a release claim; shared downstream acceptance criteria may remain partial.

Role names are proposed responsibilities. Record the actual person/agent on assignment. Each task must preserve the mapped specification IDs and attach evidence in [acceptance.md](acceptance.md). Read [plan.md](plan.md) for contracts and design decisions.

## Phase A — Establish a portable foundation

### [ ] T-001 — Discover source assets and record scope

Owner: integration engineer. Dependencies: none. Maps: REQ-001 → AC-001.

Identify exact MacroMedallion / EcoMedallion URL(s)/commits and relationships, owners, PostgreSQL interfaces, grains, permissions, history, and redistribution terms. Produce `reports/discovery.md` with reusable components and unresolved gaps. If access is unavailable, record the limitation and select the independent fixture track; never mark upstream verification passed. Evidence: actual inspected metadata or an explicit unresolved-status inventory, reviewed pilot defaults, and source-owner decisions.

Progress: the local PostgreSQL interface, relevant series/vintage objects, keys, columns, and effective privileges have been inspected. Repository identity, owners, redistribution terms, and a least-privilege source role remain unresolved.

### [ ] T-002 — Scaffold repository and isolated runtime

Owner: implementation engineer. Dependencies: T-001 scope decision; fixture-only decision is sufficient. Maps: REQ-002, NFR-001, NFR-006 → AC-002, AC-013, AC-018.

Create package/configuration/migration layout, a documented PostgreSQL prerequisite or optional local container, dependency lock, non-secret example configuration, and CLI entry point. Separate source reader and graph writer configuration. Evidence: a clean environment installs and reports configuration without printing secrets; no upstream connection is required for fixture mode. Document real commands only after implementation.

### [ ] T-003 — Build deterministic synthetic fixtures

Owner: data engineer / quant. Dependencies: T-002. Maps: REQ-002, NFR-002 → AC-002, AC-014.

Define mock instruments/listings, issuer/classification/index nodes, macro series, and synthetic observations. Include ticker changes, multi-membership, late corrections, macro revisions, disputed mappings, missing/constant returns, and a known correlation example. Label every fixture and output synthetic. Evidence: reproducible seed/checksums, data dictionary, expected outcomes, and a fixture adapter manifest; no copied private records.

### [ ] T-004 — Implement canonical adapter contracts

Owner: integration engineer. Dependencies: T-001, T-003. Maps: REQ-001, REQ-006, NFR-001 → AC-001, AC-006, AC-013.

Implement normalized contracts for entities, assertions, observations, and manifests. Map verified upstream objects when available; record optional adapter status separately from working fixtures. Validate required metadata, schema drift, rights, timestamp coverage, and source read permissions. Evidence: fixture contract checks plus inspected upstream mappings and read-only role checks for each activated adapter. Unavailable upstream adapters remain pending, not advertised as implemented.

Progress: a bounded MacroMedallion adapter verifies and extracts macro-series metadata and point-in-time observation versions through an enforced read-only source role. Role-boundary evidence and graph loading now pass. Rights review and complete manifest/run lineage remain pending.

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

Completed 2026-10-24 for the fixture demo. The independent `frontend/` application uses React, TypeScript, Vite, React Router, Zustand, and Tailwind in the QuantMeridian scaffold pattern. It renders five routes—overview, market map, macro context, correlations, and provenance—from a labeled fixture snapshot adapter and prohibits browser-to-PostgreSQL access. Typecheck, two frontend fixture tests, and production build pass. Evidence: `reports/t012-validation.md`, `frontend/README.md`. AC-009 remains partial because Power BI has not been exercised.

## Phase D — Validate and hand off

### [ ] T-013 — Execute release validation and performance checks

Owner: validation engineer / quant reviewer. Dependencies: T-010, T-011; T-012 for BI evidence. Maps: NFR-001, NFR-002, NFR-003, NFR-004, NFR-005 → AC-013, AC-014, AC-015, AC-016, AC-017.

Run meaningful role-scope, integrity, temporal, reproducibility, numerical, publication-failure, and recovery checks. Benchmark the documented fixture envelope on declared hardware; retain build time and at least 20 runs per prepared query with cache policy and p95. Proposed targets: build under 5 minutes and query p95 at most 2 seconds. Evidence: actual results/defects in the acceptance register; adjust targets explicitly before release if justified. Never fabricate passing evidence.

### [ ] T-014 — Finish contributor demo, extension design, and handoff

Owner: maintainer / implementation engineer. Dependencies: T-011, T-013; T-012 for a release claiming Power BI completion. Maps: REQ-002, REQ-012, NFR-001, NFR-005, NFR-006 → AC-002, AC-012, AC-013, AC-017, AC-018.

Replace planned setup commands with exercised commands; complete clean-room fixture walkthrough, actual screenshots, license/data notices, owner/refresh/recovery details, and synthetic securities-finance extension contract. Update README, roadmap, and handoff with real status. Evidence: new-contributor walkthrough and reviewed mappings/permissions; all public claims match implemented capabilities.

## Completion rules and coverage

A task is complete only when its deliverable exists, required review/validation evidence is retained, relevant acceptance rows are updated, and documentation matches actual behavior. Downstream code may progress against fixture contracts while optional upstream integrations remain unavailable; do not collapse those statuses.

The plan's requirement matrix maps all 12 functional and 6 non-functional requirements to these tasks and all 18 acceptance criteria. Acceptance evidence belongs in `docs/acceptance.md`, with links to permitted reports, manifests, or artifacts. All v0.1 Must criteria require passing evidence or an explicitly reviewed scope revision before a completed-release claim. Maintain one exact next task and owner in the handoff after each work session.
