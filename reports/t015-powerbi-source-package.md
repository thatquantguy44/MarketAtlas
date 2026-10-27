# T-015 Power BI source package

Date: 2026-10-26. Scope: source-controlled semantic-model preparation for the
fixture Power BI report. This is not Power BI acceptance evidence.

## Delivered

- `powerbi/MarketAtlas.model.template.tmdl` declares six import queries:
  snapshot metadata, nodes, relationships, macro contexts, rolling
  correlations, and provenance.
- All queries use the same explicit `pSnapshotId`; fact/dimension queries read
  immutable `atlas_report.*_snapshot` tables instead of resolving the moving
  `current_*` facts independently.
- `powerbi/README.md` provides a five-page report design and fixture
  reconciliation script: 15 nodes, 14 relationships, 3 contexts, and 32
  correlation estimates, plus filter/reset and provenance checks.
- Power BI local cache/settings paths are ignored.

## Validation

`PYTHONPATH=src python3 -m unittest tests.test_powerbi_contract -v` passed
three checks: one explicit snapshot parameter is used by all six imports,
only approved snapshot tables appear, no secret/default source identifier is
tracked, and the handoff remains explicit that a real Power BI reconciliation
is required.

## Remaining execution gate

The local macOS environment has no Power BI Desktop application. The Power BI
service endpoint presented a sign-in page and no authorized workspace was
available in this session. Therefore no PBIX/PBIP/PBIR, visual screenshot,
refresh result, filter/reset test, or Power BI drill-through has been claimed.
T-015 and AC-009 remain open until a BI engineer runs the template in an
authorized Windows/Desktop or Power BI service environment.
