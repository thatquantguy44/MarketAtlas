# MarketAtlas — Handoff

Updated: 2026-10-25. This is an early implementation handoff, not a completed pilot or production release.

## Current state

The original market knowledge graph specification has been reviewed and reorganized into specification, architecture plan, tasks, roadmap, and traceability documents. The product name is MarketAtlas. The repository is [thatquantguy44/MarketAtlas](https://github.com/thatquantguy44/MarketAtlas), default branch `main`.

MacroMedallion and EcoMedallion are interchangeable names for the same upstream asset. Operators may configure an optional local checkout for discovery and lineage in git-ignored `configs/local.toml`; MarketAtlas neither requires a remote repository pin nor imports its source code. The fixture implementation provides a Python CLI, deterministic synthetic records, validation, manifest, and availability-cutoff inspection. The authorized local `macro_medallion` PostgreSQL database is the primary integration contract, connected through a scoped source-reader role. T-004B loads `meta.fred_series` plus `gold.fred_point_in_time` into `atlas` as 3 macro identities and 151 versioned observations under one immutable input manifest; an identical rerun writes zero rows. T-004C.1 adds `contracts/source_contracts.toml` and a metadata-only verifier. T-004C.2 promotes `gold.dim_series`, `gold.release_calendar`, and `gold.v_source_coverage` as read-only, bounded macro-context interfaces. T-004C.3 stores their latest approved records only in dedicated `atlas` current-context tables and publishes a separate immutable `macro_context` report snapshot. T-004C.4 projects the approved current taxonomy into three source-backed `measures` assertions between six macro-series/economic-concept nodes and publishes the separate `macro_economic_graph` snapshot. The local report API reads only its report views under `marketatlas_report_reader`; the React workspace has an explicit Live macro graph mode. This is descriptive current taxonomy, not historical taxonomy, causality, or sensitivity. Evidence: `reports/t004c-live-economic-graph-validation.md` and the T-004C.1–.3 reports.

T-002, T-003, and T-005 through T-012 are complete for the fixture track. T-002 established the credential-free CLI/configuration path and T-003 established the deterministic synthetic fixture contract. Migration `001_identity_ontology.sql` created the `atlas` and `atlas_report` schemas, three scoped NOLOGIN roles, identity/ontology tables, endpoint constraints, identifier-overlap protection, and quarantine storage. Migration `002_temporal_assertions.sql` adds correction/retraction versions, effective/knowledge/system cutoff queries, and bounded traversal. Migration `003_observation_versions.sql` adds input manifests, calendar sessions, and market/macro observation versions with cutoff-aware selectors. Migration `004_curated_macro_context.sql` adds versioned series-country/concept and market-context mappings with owner, evidence basis, taxonomy version, and mandatory context-only semantics. Migration `005_rolling_correlation_estimates.sql` adds versioned fixed-window rolling correlations with explicit undefined states and cutoff/input metadata. Migration `006_build_publication.sql` adds immutable build/snapshot identities, a pinned correlation serving fact, and transactional publication. Migration `007_reporting_provenance.sql` adds snapshot-pinned report dimensions, facts, and drill-through provenance. The React fixture demo provides the evidence-first workspace. Power BI remains unimplemented.

## Gate Status

**Satisfied for documentation handoff:** the package defines a candidate scope, downstream design, task dependencies, and required evidence. The documents are reviewable planning artifacts.

**Implementation readiness established through T-012 for fixtures:** the two upstream objects, vintage semantics, dedicated write schemas, role boundaries, temporal reference replay, versioned observation selection, curated context semantics, bounded analytical estimates, atomic fixture publication, report/provenance contract, and React demo are verified. Repository identity, source ownership/redistribution rights, full adapter run-lineage, Power BI validation, and dependency-major upgrade decisions remain open. This is not an end-to-end release gate pass.

## Next Action

**Owner: validation engineer / integration engineer.** The next highest-priority slice is **T-013 — release validation and performance checks**, beginning with the completed bounded live contracts as well as the fixture workflow. It should exercise role scope, source-contract drift, current-context publication/recovery, report-reader access, repeatability, and measured query performance. Broader source onboarding remains gated by owner, rights, grain, and temporal approvals; do not promote additional catalog objects merely because they are readable. Power BI acceptance remains separately unpassed unless it is exercised.

Inputs for T-013 are the completed identity, temporal, observation, context, analytical, publication, reporting, and frontend artifacts, `spec.md`, `plan.md`, `tasks.md`, `reporting.md`, ADR-001, the verified adapter contract, and the fixture contract. Do not write into `meta`, `silver`, `gold`, `bronze`, or `audit`; upstream access remains through `marketatlas_source_reader`.

The frontend baseline is now decided: [ADR-001](decisions/001-quantmeridian-react-scaffold.md) adopts the QuantMeridian React/Vite/TypeScript/Tailwind/Router/Zustand scaffold pattern for the separate MarketAtlas demo app. T-011 must provide snapshot-pinned report/provenance contracts for that frontend; T-012 will implement it without copying QuantMeridian source modules or exposing database credentials.

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

These are required future artifacts. They have not been produced by this documentation task.

## Operations handoff requirements

Before a scheduled pilot, name the pipeline owner, database owner, report owner, and quant methodology owner. Record source freshness expectations, quarantine rules, serving snapshot selection, alert destination, and recovery procedure. On failed refresh, preserve the last successfully published snapshot, display its as-of time and stale status, and retain failed-run diagnostics. Never promote a partially built graph to reporting views.

Recovery should disable the graph job and restore the prior serving snapshot or migration state without altering upstream MacroMedallion / EcoMedallion tables. Demonstrate this on fixtures or an isolated environment before scheduling.

## Resuming after a handoff

The next implementer should record the last completed task ID, code commit, migration level, fixture/data snapshot hash, run ID, serving snapshot, open defects, and exact next task. Replace proposed commands with actual commands only after they exist and work.
