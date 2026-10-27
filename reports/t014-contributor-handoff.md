# T-014 contributor demo, extension design, and handoff

Run date: 2026-10-26  
Scope: portable fixture walkthrough, frontend demo presentation, extension
boundary design, and operational handoff. This report does not claim a Power BI
exercise, real-data redistribution approval, or production operations.

## Exercised clean-room fixture walkthrough

An archive of the current committed repository was extracted into a fresh
temporary directory with `git archive`; no local configuration or upstream
database was used. From that checkout, these commands succeeded:

```bash
PYTHONPATH=src python3 -m market_atlas fixture build --output /tmp/marketatlas-t014-fixture
PYTHONPATH=src python3 -m market_atlas fixture validate --input /tmp/marketatlas-t014-fixture
PYTHONPATH=src python3 -m market_atlas fixture inspect --knowledge-cutoff 2024-02-10T00:00:00Z
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Results: the fixture was marked `synthetic: true`, had SHA-256
`15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da`,
and all 49 Python tests passed. The cutoff inspection returned only the
`initial` macro vintage for `2024-01`, as expected.

## Browser evidence and presentation adjustment

The local browser walkthrough captured the fixture graph, live catalog summary,
and live Regional category view. The live publication reported 290 approved
series and 11 concepts; Regional reported 120 matching series. The original
50-node visual category page obscured cards and links, so the React display now
requests 12 visual nodes per page, grids them across three columns, and omits
repeated labels from individual `measures` lines. This changes presentation
only: the API still accepts 1–100 rows and the T-013 50-series query benchmark
is unchanged. The screenshots are retained in the task execution record rather
than committed as binary assets because only the synthetic fixture is approved
for public artifact reuse.

Frontend verification after this adjustment: the targeted Vitest suite passed
(3 tests) and `npm run build` completed successfully.

## Mapping and permission review

The walkthrough and extension design were reviewed against the documented
source/report boundary: source discovery remains through
`marketatlas_source_reader`, writers remain confined to `atlas`, and the local
report API uses `marketatlas_report_reader` against snapshot-pinned
`atlas_report` views. The browser has no connection string or source-schema
path. The extension contract preserves that boundary by allowing only stable
instrument node IDs to cross into a future restricted deployment and giving
public/report roles no restricted-object grants. Source-owner and
redistribution decisions remain unassigned, so this is a technical boundary
review rather than a data-rights approval.

## Handoff deliverables

- [Contributor walkthrough](../docs/contributor-demo.md) records the exercised
  credential-free commands and the browser/API boundary.
- [Data and license notice](../docs/data-and-license-notice.md) distinguishes
  MIT-licensed code from data rights and prohibits public source extracts.
- [Operations handoff](../docs/operations.md) records unassigned scheduled
  responsibilities, safe manual refresh, and controlled recovery.
- [Securities-finance extension contract](../docs/securities-finance-extension.md)
  defines separate restricted entities, stable instrument references, access
  boundaries, and non-inferential eligibility semantics.

## Open release limits

Power BI acceptance, source-owner/redistribution approval, named pilot owners,
scheduling, alerts, and a real restricted-data deployment remain uncompleted.
Those limits are reflected in the acceptance register and must not be hidden by
the completed fixture handoff.
