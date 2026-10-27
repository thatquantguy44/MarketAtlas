# MarketAtlas — Roadmap

Version labels describe intended scope, not published releases. T-014 completed the portable contributor-demo and design handoff portions of v0.1 on 2026-10-26; Power BI, named pilot operations, and real-data rights remain open.

## v0.1 — Broad market proof of concept

The first release must demonstrate one coherent path: sourced or synthetic entities, an inspectable relationship, a time-bounded estimate, and a Power BI view with traceable evidence.

| Milestone | Capability | Exit evidence | Dependencies |
| --- | --- | --- | --- |
| M0: discover and contract | Identify MacroMedallion / EcoMedallion assets, PostgreSQL conventions, public data rights, and environment | Completed source mapping and configuration/fixture contracts; assumptions resolved or explicit | Authorized source access for upstream mode; fixtures do not require it |
| M1: map the market | Canonical nodes, identifiers, temporal reference assertions, curated macro contexts | Repeatable fixture graph; source/known-time details on bounded paths; no orphan accepted links | M0 contracts or documented fixture-only track |
| M2: measure relationships | Configured rolling Pearson correlations on eligible, transformed series | Hand-checkable values, full sample/window metadata, withheld invalid estimates, historical availability checks | M1 and observation contract |
| M3: serve and explain | Power BI dimensions, facts, explicit bridges, quality and provenance details | Report filtering/drill-through and reconciliation evidence; view performance measured | M1–M2 serving outputs |
| M4: release the demo | Repeatable demonstration and operational handoff | T-014 clean-room fixture walkthrough, local screenshot evidence, validation evidence, license/data notices, extension boundary, and manual recovery record; named pilot owners/scheduling remain open | M0–M3 acceptance evidence |

The fixture track supports a portable public demonstration. An upstream integration can be part of v0.1 only when its source contracts are verified. A fixture-only release must explicitly say which upstream adapters remain planned.

## v0.2 — Richer macro and event context

Add timestamped event calendars, revisions/vintages where licensed and available, release observations, and clearer event-to-series context. Support event-window charts with explicit market calendars. Measured event responses require a documented sampling, timestamp, and estimation design; curated relevance links remain visibly distinct.

Exit evidence: event availability and vintage tests, timezone/calendar checks, worked examples, and report reconciliation. Without release-vintage metadata, show descriptive latest-vintage context with a clear label and withhold historical availability claims.

## v0.3 — Quant relationship research

Add directional beta estimates, controlled lead/lag experiments, edge stability diagnostics, and graph features such as degree or connected groups. Investigate whether graph-derived features improve a defined research decision against simple baselines. Pre-register the comparison, use chronological evaluation, and account for estimation error and multiple comparisons.

Exit evidence: versioned methodology, reproducible inputs, sensitivity analysis, a baseline comparison, and limitations. A visually dense network is not evidence of alpha or economic causality.

## v0.4 — Securities-finance demonstration

Extend shared market entities with synthetic borrowers, lenders, agreements, collateral assets, loans, and settlement contexts. The completed [extension contract](securities-finance-extension.md) requires stable instrument references plus a separately authorized restricted deployment. Begin with collateral eligibility explanations or exception dependencies. Represent conditions, limits, effective dates, and unknown facts explicitly; a simple path must not be mistaken for a fully evaluated eligibility decision.

Exit evidence: a synthetic domain contract, a worked rule explanation, rule/unknown-state checks, and proof that the extension preserves broad market identifiers and reporting grains. Restricted real client/trade data belongs in a separately authorized deployment.

## Internal pilot — Operational readiness

Advance an implemented demonstration to a scheduled internal pilot only with approved source access, dataset ownership, monitored refreshes, tested recovery, workload-specific capacity evidence, Power BI access design, and a named support owner. Keep any public fixture example separate from private configuration and data.

Exit evidence: measured reliability and performance against the recorded operating targets, reviewed access controls, alert/rollback exercise, and acceptance evidence for the selected pilot scope.

## Expansion decisions

- Add a graph database only after measured traversal requirements exceed the PostgreSQL approach and justify the operating cost.
- Add an API or natural-language interface only after the curated queries and provenance are dependable; answers must preserve as-of constraints and cite graph evidence.
- Add machine-extracted relationships only with an evidence model and review path. Extraction confidence cannot replace source reliability or statistical uncertainty.
- Expand the instrument universe only after coverage, quality, and reporting performance are measured on the pilot.

Maintain the roadmap when evidence changes scope. Move incomplete capabilities forward explicitly rather than calling a milestone complete because its documents exist.
