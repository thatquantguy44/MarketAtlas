# T-017 — Revision-quality publication validation

Date: 2026-10-26 (America/New_York). Scope: configured, restricted internal-only
local pilot. This is not a public-data, scheduled-deployment or Power BI release.

## Delivered behavior

Migration 011 adds `atlas.macro_revision_quality_version` and
`atlas_report.macro_revision_quality_snapshot`, plus the report-only current view.
The separate publication is `macro_revision_quality`. Its one-row-per-selected-
series grain includes explicit unknown rows with null metrics when the source
summary is missing. Current taxonomy supplies already onboarded node identities;
the publisher creates no graph assertions or historical observation vintages.

The publisher checks the source selection and row hashes, contract fingerprint
and registry gate, restricted rights, temporal semantics, numeric fields,
duplicate keys and complete missing-ID accounting before writing. Manifest
identity includes capture time; a fresh capture remains distinct even if source
metrics are unchanged. Existing manifest/version rows are never overwritten.
Build identity includes configuration, code revision and publisher content hash.
One transaction and a publication-specific advisory lock serialize publication;
a materialization savepoint allows failed diagnostics to survive while partial
version/report/provenance rows roll back.

The selected-series API uses one report-reader SQL statement to pin metadata
and data to the same quality snapshot. The live workspace shows metrics,
capture time, unsupported historical availability and expandable independent
snapshot/input/build/source provenance. Percentages retain source units.

## Executed checks

| Check | Result |
| --- | --- |
| `MARKETATLAS_TEST_DATABASE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 66 tests passed, including the real PostgreSQL test |
| `PYTHONPATH=src python3 -S -m unittest discover -s tests -v` | 65 tests passed with site packages disabled; only the opt-in database test skipped |
| `npm --prefix frontend test` | 11 tests passed |
| `npm --prefix frontend run build` | TypeScript and Vite production build passed |
| Ruff on the new publisher, report API and new/changed Python tests | Passed |
| `git diff --check` | Passed |
| Migration runner | Migration 011 applied; prior ten migrations retained |
| Approved three-series read-only extraction | Three summaries, zero missing IDs; payload kept only under ignored `data/generated/` |
| Restricted live publication and exact rerun | Three report rows; identical rerun reused the snapshot and output checksum |

The first validated live snapshot was
`e38357ad-8d33-5885-9e16-fa48d08eb711`; its output SHA-256 was
`a8265353122167f2d5fd7d81baf79e7d501f872a0c9c8a67d6082cda3be3b970`.
The input-selection SHA-256 was
`0210e390d6f96c46c0fbadfc9f03f7a58fb9297050d6e64894add5de00cd8530`.
Final local pointer/checksum reconciliation is retained in ignored
`data/generated/t017_validation.json`; implementation changes can produce a
later build of the same captured input without modifying retained snapshots.

The PostgreSQL test uses synthetic identities inside an outer forced rollback.
It proves exact rerun reuse, null unknowns, matching provenance grain, rollback
after all materialization rows were written, failed-run retention, recovery on
the same failed identity, preservation of older snapshot contents, no automatic
republishing of a superseded identity and independence of other publication
pointers. All synthetic database changes roll back. Report-reader writes are
denied and the role has no `atlas` schema usage.

Unit tests distinguish unpublished quality, a series outside the selection and
a selected unknown summary. They reject tampered selection/source hashes,
duplicate rows, false missing-ID accounting, booleans masquerading as counts,
nonfinite/negative metrics, averages above maxima, unverified gates, unsupported
history and broader rights claims. Frontend tests cover bounded requests,
zero-versus-unknown formatting, percentage units, wrong-series responses and
unavailable quality.

## Browser verification

Chrome exercised the local Vite proxy and report API at the normal desktop
viewport: fixture entry → live catalog → category neighborhood → selected
approved series → quality metrics → expandable provenance. Capture time and
the quality snapshot were visibly separate from graph provenance. Selecting a
series outside the configured quality selection displayed its coverage status.
Stopping the report API produced a recoverable quality-unavailable panel while
the already loaded graph remained usable; restarting the API and pressing
Refresh restored the metrics. Console warnings/errors were absent during the
normal metrics/provenance flow. The intentional outage produced an expected
failed request. A screenshot was inspected locally; restricted source metrics
and screenshots were not added to tracked artifacts.

## Reproduction and limits

From the repository root with the authorized ignored local configuration:

```sh
PYTHONPATH=src python3 -m market_atlas database migrate
PYTHONPATH=src python3 -m market_atlas adapter extract-revision-summary --output data/generated/revision_summary_t017.json
PYTHONPATH=src python3 -m market_atlas revision-quality publish --input data/generated/revision_summary_t017.json
PYTHONPATH=src python3 -m market_atlas revision-quality publish --input data/generated/revision_summary_t017.json
PYTHONPATH=src python3 -m market_atlas report serve-macro-economic-graph
npm --prefix frontend run dev -- --host 127.0.0.1
```

No upstream object was changed or newly onboarded. These current-quality
summaries do not supply historical source availability, reconstruct revision
vintages, define a statistical risk score or imply causality. The local manual
pilot has no scheduled freshness SLA. Public redistribution and Power BI
execution acceptance remain outside this completed slice.
