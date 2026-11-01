# T-030 — Browser analytics validation

Completed 2026-11-01 at restricted-local scope on
`feat/macro-relationship-analytics`. User authorized shipping the foundation and
adding the three browser views. Foundation `bd607df` is pushed in
[PR #15](https://github.com/thatquantguy44/MarketAtlas/pull/15), with both foundation
CI workflows passed. Browser changes are a separate commit in that PR.

## Delivered result

The existing http://127.0.0.1:60114/ report now has a fifth **Relationship research**
tab. App ID remains `dashboard:b31d5d91-39e6-4d2a-8719-4888de544244`; the four
existing views, source inspection and user presentation are retained. No protected
runtime, dependencies, database schemas, source rows or schedules changed.

The tab provides signed-correlation heatmaps, group-dispersion history and a node
divergence ranking. Canonical pairs display symmetrically with omitted diagonal
and null gaps. History stops at the selected knowledge date; nulls are not
connected. Display alias `divergence` equals the supplied absolute deviation from
the complete group's mean. Pair investigation exposes exact transformed windows,
counts, source records, baseline diagnostics and method/input identities.
Named group/date/pair scopes restore from app-generated view links. Each group
retains its own date. Selecting a prior complete evaluation is an explicit action.

Independent analytics pack is
`a56bd8f7591762d8664a7c03eefe4e0d9406469d421c56808f48c6cf589d56d1`;
publication pack remains
`be93f9085a543d44b84c962f1d8af96bd4e88d1fa53aecabe691adf2d597befc`.
Reviewed queries contain three groups, 2,526 relationships, 808 dispersion rows,
2,458 node rows, 2,458 window records and 3,512 deduplicated transformed point
states. The raw PostgreSQL capture is not embedded. The private indented browser
snapshot is 14,822,769 bytes.

The atomic refresh accepts `--analytics-pack` and explicit `--update-content`.
It stages authored files/data/build together, retains old sidecars and commits
HTML last. Ordinary publication-only refresh retained all six research queries
with unchanged combined canonical hash
`3c5ce580dec068e9a2789cdea311ae36885306e5b8da1e970ae808f609e2d955`.
Its cutoff/capture remain visibly independent; this does not regenerate analytics.

## Verification

- Full pinned suite: **148 tests, 143 passed/five opt-in database skips**.
- Core `python -S`: **148 tests, 134 passed/14 optional/database skips**.
- Four Node cases pass for cutoff/group scope, symmetric null-preserving cells,
  measured-zero ranking inputs and exact point references. They run in the
  existing orchestration CI workflow.
- Adapter tests retain original estimates/nulls and every transformed window,
  reject tampering and keep publication/research contracts separate. Refresh
  tests cover retained research, explicit authored installation and rollback of
  changed/new content after build/checksum/HTML commit failures.
- Changed Python lint, shell syntax and diff checks pass. Eleven previously
  recorded whole-repository lint findings in untouched baseline files remain
  separate; no clean whole-repository lint claim is made.
- Installed prebuilt Data runtime compilation passed without protected changes.

Actual Chrome checks passed:

- Treasury latest visibly renders all three views with three supported pairs;
  representative numbers and 59/63 paired changes match retained research rows.
- Inflation latest preserves one supported pair out of six and unavailable
  dispersion/ranking. Explicit latest-complete selection moves to September 30,
  2025 with six supported pairs; history ends there without later evaluations.
- Heatmap investigation selects another pair and exact observation/source window.
  Source preview contains six canonical rows for that group/date, rather than
  twelve mirrored rows or the full universe. Group switching, latest reset and
  selected-view reload restoration pass. Catalog remains 290 series/11 concepts.
- At 390×844, controls wrap, cards stack, all plots remain visible and tables
  scroll internally; document width stays 390 pixels. A long heading and tooltip
  found during inspection were shortened and rechecked. Normal sizing was restored.
- No captured browser warnings/errors. Final `buildStatus` is `complete`; the
  verified research tab is left open and the existing runtime controls are active.

Private proof: `data/generated/macro-analytics/browser-tests.log`,
`browser-core-tests.log`, `browser-integration-proof.json`,
`browser-final-result.json`, and screenshot `browser-analytics.png`.

## Remaining scope

Analytics remain frozen until explicitly replaced; generating them through
Dagster is the next separate priority. Monthly source gaps and undated pre-2024
Treasury history stay excluded. No source ingestion, public/cloud publication,
predictive validation or Power BI execution was added. The existing loopback
preview remains login-supervised and needs this computer to serve its URL.
See [runbook](../docs/report-frontend-runbook.md#relationship-research-views).
