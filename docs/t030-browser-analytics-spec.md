# T-030 — Browser relationship research

Status: implemented and locally validated, 2026-11-01. User authorized shipping
T-028/T-029 and adding the three browser views. Foundation commit `bd607df` is
pushed in PR #15; browser changes are a separate commit in the same PR. See
[validation](../reports/t030-browser-analytics-validation.md).

## Scope and review path

Add one **Relationship research** tab to the existing local macro report, keeping
its app identity, URL, four existing views, source inspection and user presentation.
Use the validated macro research pack independently of the publication report
pack; show its cutoff/capture and preserve nulls. No new source queries, predictive
claims, upstream schedule or Power BI acceptance.

- Relationship heatmap: one group/date, signed Pearson correlation on fixed
  `[-1, 1]` colors; symmetric display of canonical pair rows, omitted diagonal,
  unavailable cells remain gaps. Expose sample counts, distance and change.
- Dispersion timeline: the same group through the selected knowledge date, with
  null gaps, complete-member requirement and date-specific status. No drawing
  through unavailable intervals.
- Node-divergence ranking: selected group/date, absolute deviation from the group
  mean in standardized units; retain unavailable members in supporting details.
  Explain standardized changes and labor orientation at their relevant controls.
- Pair investigation: explicit heatmap mark action or pair selector opens the
  exact estimate, source/method identity and aligned transformed observations with
  source records and unavailable reasons. A compact shared point cache retains
  exact observation evidence without duplicating each rolling window.

Default to Treasury yields/latest evaluation. Group/date/pair selections use
named runtime section scopes so app-generated links reproduce them. Switching
groups restores that group's own selection. A missing monthly result never
silently falls back; an explicit action may select the latest complete date.

## Integration

Add a validated analytics-to-browser adapter and typed reviewed queries. Preserve
separate pack IDs and dates, with metric definitions and recorded reproduction
steps in source inspection. Do not embed secrets, absolute machine paths or an
unnecessary copy of the complete raw source capture in the browser snapshot.

Extend the existing atomic report refresh with optional `--analytics-pack` and
explicit `--update-content`. Stage the new authored files and snapshot together,
verify the compiled assets, retain old sidecars and commit HTML last. Build or
commit failure restores prior source/metadata and leaves the working report.
Ordinary daily refreshes preserve the last attached independent analytics queries
without claiming to regenerate them. Automatic analytics generation is later work.
Fresh report builds accept an optional third analytics-pack argument.

Authored JSX/helpers live in `powerbi/browser/` and deploy only to the existing
app's editable `src/content/dashboard/`. Use shared EvidenceChart/DataTable,
source actions, controls and sortable layout. No protected-runtime changes or new
JavaScript dependencies. Python adapter/refresh checks use unittest; pure browser
selectors have deterministic Node tests. Verify the local built report in Chrome
at normal/narrow widths, representative filters/reset, pair investigation,
source inspection, supported and unavailable states, and absence of runtime errors.

## Acceptance

All three views render actual reviewed values and reconcile to the retained pack.
Source/copy rows share the visible scope. Dates do not admit future panels;
missing values are not zero, fabricated self-correlations or interpolated marks.
Existing report views/identity survive installation and normal refresh. Retain
test/browser evidence, update the runbook/handoff and finish PR #15 with a separate
browser commit. Do not merge without a user request.
