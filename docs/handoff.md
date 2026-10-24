# MarketAtlas — Handoff

Updated: 2026-10-24. This is an early implementation handoff, not a completed pilot or production release.

## Current state

The original market knowledge graph specification has been reviewed and reorganized into specification, architecture plan, tasks, roadmap, and traceability documents. The product name is MarketAtlas. The repository is [thatquantguy44/MarketAtlas](https://github.com/thatquantguy44/MarketAtlas), default branch `main`.

The [EcoMedallion repository](https://github.com/thatquantguy44/EcoMedallion) and its README have been inspected; a distinct MacroMedallion repository has not been identified. The fixture implementation provides a Python CLI, deterministic synthetic records, validation, manifest, and availability-cutoff inspection. An authorized local MacroMedallion PostgreSQL database is connected through a scoped source-reader role, and a bounded adapter verifies `meta.fred_series` plus `gold.fred_point_in_time`. The configured pilot extracted three macro series and 151 observation versions with selection hash `75f9edc270aabe7ed6604b9663b4a575dc6ce32bfbfa0ac0f31c0da936faf875`.

T-005 and T-006 are complete for the fixture track. Migration `001_identity_ontology.sql` created the `atlas` and `atlas_report` schemas, three scoped NOLOGIN roles, identity/ontology tables, endpoint constraints, identifier-overlap protection, and quarantine storage. Migration `002_temporal_assertions.sql` adds correction/retraction versions, effective/knowledge/system cutoff queries, and bounded traversal. Live validation loaded 15 nodes, 4 identifiers, and 15 assertions idempotently; it rejected invalid endpoint/identifier cases and passed all temporal replay cases. Observation storage, analytical estimates, serving snapshots, and Power BI remain unimplemented.

## Gate Status

**Satisfied for documentation handoff:** the package defines a candidate scope, downstream design, task dependencies, and required evidence. The documents are reviewable planning artifacts.

**Implementation readiness established through T-006 for fixtures:** the two upstream objects, vintage semantics, dedicated write schemas, role boundaries, and temporal reference replay are verified. Repository identity, source ownership/redistribution rights, and full adapter run-lineage remain open. This is not an end-to-end release gate pass.

## Next Action

**Owner: data engineer / quant implementation engineer.** The exact next implementation slice is **T-007 — observation versions and availability selection**. Add market and macro observation storage with units, calendar, adjustment, release/vintage, cutoff, and source-run fields. Load the synthetic macro revision and verify that each cutoff selects only its eligible vintage; explicitly withhold unsupported adjusted-history cases.

Inputs for T-007 are the completed identity and temporal schema, `spec.md`, `plan.md`, `tasks.md`, the verified adapter contract, and the fixture contract. Do not write into `meta`, `silver`, `gold`, `bronze`, or `audit`; upstream access remains through `marketatlas_source_reader`.

## Access and integration checklist

| Needed input | Owner role | Why it matters | Default until resolved |
| --- | --- | --- | --- |
| Repository identity and current commit(s) | Josh / repository owner | Prevent integration against guessed paths or stale APIs | No repository-specific import paths assumed |
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
