# T-026 — Source freshness and vintage diagnosis

This is the initial diagnosis, before the separately authorized [T-027 repair](t027-source-repair-validation.md).

Validated October 31, 2026 (America/New_York), on
`feat/source-freshness-vintages` from merged main `e6aa4d2`.

A fresh eight-contract gate passed, fingerprint
`9b367958ea5e82132765bcd573ddf43cb54c12d286220ae8874915c354d6f93c`.
The six publication interfaces are unchanged; two audit interfaces are scoped to
bounded read-only diagnostic status/timing/counts under separate contracts.
Source role was `marketatlas_source_reader`, with read-only sessions and no source
write privileges. No upstream schemas, credentials or source checkout were changed.

## Findings

- 181/268 supplied stale flags; zero unknown flags or rule/age mismatches.
- Latest attempts for 179 of the stale series were skipped as not due. Across all
  268 latest attempts: 209 skipped and 59 succeeded.
- Window population: 94 dated series, 170 deliberately current-only series with
  35,433 blank-date versions, four with no observations in the selected window.
  All 170 have upstream vintage tracking disabled; inspected normalization blanks
  both real-time dates for that policy. MarketAtlas now reports that explicit
  policy reason while continuing to quarantine unknown dates from PIT ingestion.
- ANFCI/NFCI/NFCICREDIT/NFCIRISK last successful extractions each returned exactly
  100,000 rows. The inspected upstream client performed a single observations
  request without row-offset pagination, including its vintage-window requests.
  This is strong evidence for the four truncated tails, not proof from count alone.
- Official provider spot checks showed newer AKUR, GDP and ANFCI periods than
  PostgreSQL. Read-only API probes recovered 65 dated AKUR versions and 10,115
  dated ANFCI versions in the requested 2024–October 2026 window. These responses
  remain private and were not ingested or presented as repaired PostgreSQL data.

## Deliverables and verification

`source_health.py` supplies an inspectable SQL/Python diagnosis, safe CLI and manual
Dagster job. It retains separate clocks, audit statuses, unknown values and queues
for source polling/vintage-policy review. Recovery manifests/config/argv validate
with the inspected upstream manifest/config loaders, contain no credentials, and
require explicit dry-run pilots before a write decision. Original false vintage
flags remain false in freshness manifests; recovery proposals explicitly set true.

The separately prepared upstream pagination patch applies cleanly and passed
26 targeted offline tests in an isolated copy: ordinary request tails, vintage
windows, cap fallback, missing/excessive counts, empty pages, count drift and
wrong offsets. The upstream source hash remained unchanged. No upstream patch or
warehouse repair was applied.

MarketAtlas tests cover source-policy versus malformed metadata, independent
clocks, stale-rule boundaries, unknown rules/flags, latest attempt failures,
page-limit suspicion, 25-ID batching, output/role/bounds protection, unexecuted
credential-free review plans and the native Dagster diagnostic operation.
Final suite and live job results are recorded in the handoff. Generated captures,
provider responses and detailed logs remain under ignored `data/generated/source-health/`.

[Runbook and source links](../docs/source-health-recovery.md) describe the exact
recovery decision. T-026 is complete at diagnosis/tooling scope. T-027 (upstream
freshness/vintage repair) remains pending explicit source-owner authorization and
post-repair validation. No increased PIT coverage or source freshness is claimed.

Live manual diagnostic job: `6399f461-aded-4d0f-bf83-593d330cb372`, success.
Full MarketAtlas suite: 118 tests, 114 passed/four opt-in database skips.
Read-only selection validation retained 94 PIT series / 35,576 versions and 268
current-context IDs, with explicit reasons for 170 current-only, four no-window
and 22 unsupported-source exclusions. The test suite does not certify a repaired
upstream warehouse.
