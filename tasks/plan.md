# Macro analytics implementation plan

Spec: [T-028/T-029](../docs/t028-t029-macro-analytics-spec.md).
Task list target: existing [docs/tasks.md](../docs/tasks.md), T-028 then T-029.

1. Add explicit settings and cutoff-aware preparation in `analytics/macro_series.py`.
   Verify transformations, history eligibility, alignment, revisions, gaps and bounds
   with focused unittest cases before proceeding to relationship calculations.
2. Add `analytics/macro_relationships.py` and independently checked numeric cases.
   Verify fixed windows, canonical pairs, undefined states, z-scores/dispersion and
   exact prior-evaluation comparisons.
3. Add immutable local pack delivery and CLI entry points. Verify deterministic
   reuse, integrity checks, typed CSVs and failed-build isolation.
4. Run read-only live preparation/build/replay and independent numerical checks.
   Retain private inputs under ignored generated storage. Run full suite/lint,
   record evidence, reconcile product scope/task status and update the handoff.

Risks: older rows may lack valid source dates (withhold, never infer); daily
holidays lack an approved calendar (conservative missing weekdays); current
metadata and operator groups are not historical taxonomy; pairwise missingness
means distance matrices need not be Euclidean (no metric-space claims).

The workflow adds no PostgreSQL schemas/dependencies and does not change existing
publication pointers, scheduling or report assets. Complete the user-authorized
implementation without adding intermediate approval gates.

## Completion checkpoint, 2026-10-31

All four implementation/verification steps completed. T-028 and T-029 are checked
in the designated task list. [Retained evidence](../reports/t028-t029-macro-analytics-validation.md)
records the live CLI run, exact replay and independent numerical proof. All 23
new tests pass; the full pinned suite has 138 passes/five opt-in database skips.
Changed-file lint passes; 11 untouched baseline lint findings remain separate.
No commit/push or browser integration was requested as part of this checkpoint.

## Browser follow-on checkpoint, 2026-11-01

User then authorized shipping the foundation and adding browser views. Foundation
`bd607df` is pushed in PR #15. T-030 adds validated independent-pack attachment,
scoped heatmap/timeline/ranking/pair evidence and atomic authored-content updates.
[Validation](../reports/t030-browser-analytics-validation.md) records 143 Python
passes/five skips, four Node passes and actual normal/narrow Chrome checks. The
normal daily refresh retains frozen research data; automatic research generation
is the next separate task. PR review/merge remains with Josh.
