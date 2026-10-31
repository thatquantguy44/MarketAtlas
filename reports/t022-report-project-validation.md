# T-022 — Native report source and usable local browser report

Date: 2026-10-30. Scope: generate editable reports and provide actual-data access
without a Power BI account. T-015 / AC-009 remains open.

## Delivered

- `market_atlas.reporting.project.build_project` and `scripts/build-report-project.py`
  author PBIP/PBIR + TMSL model source from one validated immutable pack.
  Fixture and actual-data models each have five pages, explicit typed imports,
  active single-direction dimension relationships and distinct-count measures.
- Fixture source covers snapshot status, market map, curated context, correlation
  diagnostics and evidence. Actual-data source covers independent publication
  status, economic catalog coverage, release/coverage context, selected revision
  quality and evidence. Undefined metrics remain blank; timestamps are UTC.
- `powerbi/browser/DashboardContent.jsx`, `market_atlas.reporting.browser` and
  `scripts/build-browser-report.sh` provide an optional editable local browser
  report through the installed Data runtime. Its four views use the actual
  PostgreSQL pack from the successful final T-021 recovery run.
- Generated private artifacts remain ignored under `data/generated/reports/`:
  `fixture-project/MarketAtlas.pbip`, `real-project-validated/MarketAtlas.pbip`,
  and `browser/`. Source code and reproduction instructions are tracked.

## Source and browser checks

The fixture project's 23 and actual-data project's 21 schema-bearing files passed
Microsoft's official PBIP/PBIR JSON schemas with `jsonschema==4.25.1`. The retained
validator downloads only official Microsoft schema URLs. All real report visual
fields also resolved against the generated model. Unit tests validate fixture
visual/model/relationship bindings, role-playing dimensions, UTC normalization,
explicit source-only status and refusal to overwrite projects or consume corrupt
packs. Full suite results are retained in [T-021](t021-dagster-recovery-validation.md).

The local report runs at http://127.0.0.1:60114/. The Data preview helper registered
a loopback-only user login service. It serves a frozen pack and does not schedule
data refreshes. The app ID is `dashboard:b31d5d91-39e6-4d2a-8719-4888de544244`.

Chrome checks exercised all four views and inspected visible charts/tables:

| Check | Observed result |
| --- | --- |
| Catalog default/reset | 290 distinct series and 11 concepts; chart and table populated |
| Inflation selection | 18 series, one concept; reset restores 290/11 |
| Releases/coverage | 32 captured release rows and three coverage rows, including supplied stale flags |
| Quality selection/reset | GDP produces one summary and the matching version's evidence; All restores three of each |
| Publications/evidence | Three independent snapshots; graph/context/quality source and build evidence visible |
| Narrow layout | 390px layout wraps controls; chart labels render; wide tables scroll internally |
| Source inspection | Exact immutable pack ID, input checksums, distinct-count definition and taxonomy join visible |
| Browser errors | No captured error-level console messages |

A discovered quality-evidence join defect was corrected before delivery: subject
IDs identify quality **versions**, not series nodes. The GDP interaction above
verified the corrected version-key join. Unknown cutoff values display as missing;
publication/export times are not treated as upstream freshness.

## Startup documentation

The [front-end runbook](../docs/report-frontend-runbook.md) and
`scripts/report-preview.sh` provide repeatable start/status/stop commands,
login/reboot behavior, new-pack rebuilds and clean-checkout recovery. Existing
preview start/status were checked without replacing the project or changing
its registered port. Builder and launcher shell syntax checks passed.

## Unexecuted Power BI gate

This Mac has no Power BI Desktop authoring runtime. The Power BI integration was
found and suggested but is not installed/connected; there is no authorized
workspace/account in this session. No Power BI refresh, DAX result, screenshot,
filter/reset or drill-through execution is claimed. JSON Schema validation does
not validate engine execution. Native evidence pages have direct subject/kind
selection; cross-page drill-through is not configured. The CSV fixture project
does not replace the required pinned PostgreSQL fixture refresh exercise.

The browser report is usable now, while native source awaits Power BI execution.
[Instructions](../powerbi/guides/generated-reports.md) describe both routes. The
restricted actual data were not uploaded or published externally.
