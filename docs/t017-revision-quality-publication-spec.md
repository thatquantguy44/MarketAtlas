# T-017 — Restricted revision-quality publication

## Objective and scope

Carry the approved T-016 extract into a separate internal publication named
`macro_revision_quality`. Show a selected live macro series' current revision
summary, missing/unknown status, extraction time, snapshot and input provenance.
This is descriptive current quality context: no historical-as-known, causal or
sensitivity claim. Maps to REQ-006, REQ-010, REQ-011 and NFR-001/003/005
(AC-006/010/011/013/015/017). Power BI acceptance remains separate.

## Contract and boundaries

- Accept only restricted, checksum-valid, contract-verified T-016 extracts.
- Resolve selected series against the already onboarded current taxonomy. Reject
  missing identities rather than inventing a source or matching by display label.
- Retain one append-only quality version per manifest and series, including an
  explicit `unknown` version with null metrics for a missing source summary.
- Publish exactly one report row per selected series in one transaction, with an
  immutable input manifest, build identity, output checksum and provenance.
- An identical input reuses its snapshot. Failed materialization rolls back all
  report/version rows, retains a failed-run diagnostic and preserves the prior
  publication. Other publications are independent.
- The local API uses only `atlas_report` views under the report-reader role.
  Select at most one series per request; a missing publication, an unselected
  series and a selected series with an unknown summary remain distinguishable.
- Source reads stay with `marketatlas_source_reader`; writes stay within `atlas`
  and `atlas_report`. No new dependency, upstream interface or public data right.

## Implementation slices

1. Validate extraction checksums, temporal/rights gates and complete missing-ID
   accounting; add migration 011 and atomic publisher/CLI.
2. Add the bounded report endpoint and a selected-series context panel. Fetch
   quality separately from graph topology and show its own publication times.
3. Verify synthetic invalid/missing cases, real PostgreSQL idempotency and failure
   retention, API role boundaries, frontend build and browser behavior. Retain
   safe evidence and update tasks/acceptance/handoff.

## Commands and structure

Python code follows existing typed functions in `src/market_atlas/publishing/`;
SQL lives in `sql/migrations/011_revision_quality_publication.sql`; UI changes
belong to `frontend/src/`. Tests use unittest and Vitest, without new libraries.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run build
PYTHONPATH=src python3 -m market_atlas database migrate
PYTHONPATH=src python3 -m market_atlas revision-quality publish --input data/generated/revision_summary_catalog.json
```

## Success criteria

Reject tampering, unsupported history, unverified inputs and invalid metrics
before writing. Prove snapshot grain, missing-is-unknown, provenance, exact rerun
reuse, later input isolation and rollback after an injected materialization
failure. Show quality with its own dates and restricted/current context label;
keep the graph usable when quality is unavailable. Retain no restricted source
payload or screenshot in tracked evidence.
