# MarketAtlas — Handoff

Updated: 2026-10-24. This is an early implementation handoff, not a completed pilot or production release.

## Current state

The original market knowledge graph specification has been reviewed and reorganized into specification, architecture plan, tasks, roadmap, and traceability documents. The product name is MarketAtlas. The repository is [thatquantguy44/MarketAtlas](https://github.com/thatquantguy44/MarketAtlas), default branch `main`.

The documentation package is on `main` at `f57d3c9423326f38cc060a38474614ff10ae6c8e`. The [EcoMedallion repository](https://github.com/thatquantguy44/EcoMedallion) and its README have been inspected for initial discovery; a distinct MacroMedallion repository has not been identified. A first fixture implementation slice now exists on `feat/fixture-foundation`: Python CLI, deterministic synthetic records, validation, manifest, and availability-cutoff inspection. [Initial discovery](../reports/discovery.md) records verified repository facts and remaining gaps. Live database tables, permissions, data rights, and the Power BI environment remain uninspected. No graph database migration, live adapter, rolling-correlation output, or Power BI report has been implemented or exercised. All 18 release acceptance criteria remain pending.

## Gate Status

**Satisfied for documentation handoff:** the package defines a candidate scope, downstream design, task dependencies, and required evidence. The documents are reviewable planning artifacts.

**Implementation readiness pending discovery:** upstream source contracts and the selected environment are unverified. The fixture generator supports independent contract work; it does not pass the end-to-end fixture or database acceptance gates. Candidate design and task documents may be refined as discovery supplies evidence. This is not a claim that lifecycle approval, source integration, validation, or release gates have passed. The QF Workflow SDK stage hook is not included in this package and has not been run.

## Next Action

**Owner: integration engineer or implementation agent.** Continue **T-001** by verifying approved EcoMedallion source objects, grains, availability/vintage fields, read-only access, and data rights; confirm whether MacroMedallion is a separate asset. Inputs: `spec.md`, `plan.md`, `tasks.md`, [discovery.md](../reports/discovery.md), an authorized EcoMedallion environment, and the intended PostgreSQL metadata. Do not wire an upstream adapter before this contract is checked.

Extend the discovery report with source ownership, schemas, grains, identifier conventions, available timestamps/vintages, row counts, data rights, and deployment constraints. Confirm whether MacroMedallion is a separate repository, former name, or alias for EcoMedallion; inspect approved interfaces rather than relying on the README alone. The synthetic fixture path can progress independently. The next fixture implementation step is T-004's typed adapter boundary, followed by T-005's PostgreSQL identity and ontology migration; keep all acceptance rows pending until their full evidence exists.

## Access and integration checklist

| Needed input | Owner role | Why it matters | Default until resolved |
| --- | --- | --- | --- |
| Repository identity and current commit(s) | Josh / repository owner | Prevent integration against guessed paths or stale APIs | No repository-specific import paths assumed |
| Approved source tables/views and grains | Data owner | Establish read contracts and source keys | Read-only discovery; fixture adapter available |
| PostgreSQL version, schema permissions, migration convention | Database owner | Select compatible migration and serving strategy | Dedicated graph/report schemas; no upstream DDL |
| Market adjustment and macro vintage metadata | Quant / data owner | Support historical and analytical claims | Unsupported estimates withheld; latest-only labeled descriptive |
| Source and redistribution rights | Data owner | Define public demo contents | Synthetic fixtures only in public artifacts |
| Power BI authoring/refresh environment | Report owner | Confirm Import/DirectQuery, gateway and visual constraints | Proposed Import pilot; standard visuals remain usable |
| Owner and runtime scheduling | Engineering owner | Make refresh and rollback accountable | Manual fixture run before scheduling |

Never record passwords, connection strings with credentials, internal hostnames, or restricted source samples in the public discovery report. Authorized environment details belong in the appropriate private configuration.

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
