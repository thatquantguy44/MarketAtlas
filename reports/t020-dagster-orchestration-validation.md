# T-020 — Dagster PostgreSQL refresh orchestration

Validated on 2026-10-30, America/New_York. The user selected MarketAtlas refresh
from existing PostgreSQL data, excluding upstream FRED ingestion.

## Implementation

An optional Dagster 1.13.27/webserver 1.13.27 environment and resolved dependency
lock define `fred_daily_refresh`, with 13 ordered stages, and the credential-free
`synthetic_powerbi_smoke`. Importing definitions makes no database connection.
The existing CLI also provides `refresh plan` and `refresh run` using the same
plan/execution service, without importing Dagster into the core CLI.

The run date rolls observation/cutoff dates and the release window (7 days back,
60 ahead). Existing three-series selections/history start are retained; the
full approved catalog supplies the graph. Source access is read-only, writes
stay in MarketAtlas schemas, and report exports run under the reader role.
A PostgreSQL advisory lock excludes concurrent refresh sessions. Dagster runs
in process and allows two retries for transient failures; validation failures
stop downstream operations. Per-run input captures and safe checkpoints are
retained in ignored local storage. Each publication is atomic independently;
the whole refresh does not claim a cross-publication rollback transaction.

The daily schedule is 18:30 America/New_York, initially STOPPED. The local
webserver/daemon was started and HTTP/GraphQL verified at 127.0.0.1:3001, exposing
both jobs and the stopped schedule. This is a development runtime, not an
installed reboot-persistent service. No upstream ingestion, Power BI service
refresh, mail/webhook alert or production deployment was configured.

## Verification

- Python 3.12.0, pinned Dagster/webserver installed into isolated `.venv-dagster`;
  `pip check` reported no broken requirements.
- `Definitions.validate_loadable` passed; definitions loaded under a patched
  database connector that would fail any connection attempt.
- Core-only suite: 91 tests, 82 passed and nine optional/database skips.
- Dagster-environment suite: 91 tests, 87 passed and four opt-in database skips.
- Focused orchestration suite with the database flag: all 13 tests passed.
- Tests cover rolling dates across DST, safe output paths, fresh/stale/failed
  upstream markers, exact stage sequencing, failure propagation, sanitized
  errors, retry capture reuse, actual Dagster retry events, synthetic CSV pack
  creation, queue concurrency configuration and live advisory-lock exclusion/
  release with two independent database connections.
- Ruff checks, launcher shell syntax, definition validation, and the synthetic
  Dagster job passed. CI workflow source runs the credential-free optional suite;
  GitHub Actions execution is not claimed.

## Live run

Dagster run: `dc8d2735-a568-409b-99c9-a1f83ee99d30`.
All 13 stages completed successfully in the local database. Dagster reported
8.59 seconds of step execution. The run used the New York date 2026-10-30;
UTC capture/publication timestamps fall on October 31. Source API ingestion
was not invoked, and upstream freshness was explicitly `not_verified`.

| Surface | Observed result |
| --- | --- |
| Observations | 151 versions seen, zero newly inserted, three series; a fresh capture manifest retained |
| Macro context | Three taxonomy records, 32 scheduled releases, three coverage records; 38 report rows |
| Full graph | 290 series, 11 concepts, 290 source-backed measures edges |
| Revision quality | Three selected summaries, zero missing IDs |
| Power BI pack | Eight validated tables across the three actual-data publications |

The new context count differs from the earlier 48-row fixed-window snapshot
because this run used the configured rolling release window, 2026-10-23 through
2026-12-29. Prior snapshots remain retained. The synthetic publication was not
rebuilt or republished.

| Publication | Serving snapshot |
| --- | --- |
| macro_context | `e98b634d-0571-5406-a3fc-5d56e8d2c43f` |
| macro_economic_graph | `0428f123-c947-51ef-884a-91ad7672aca4` |
| macro_revision_quality | `0782c4b0-b090-59cc-bd3c-6f73fdedea69` |

Run artifacts are in ignored `data/generated/daily/<run-id>/`.
The validated Power BI pack is
`data/generated/powerbi-real/f8130b91601b18a60a16ddfdc167ebb2f75aa1fe5ca64a46321252af664d4264/`.
No source rows, credentials or private connection coordinates are retained here.

## Remaining operating steps

The local daily schedule must be enabled to launch future automatic runs. The
process/machine must stay running; production operation additionally needs a
service host, restart policy, metadata backup and independent monitoring/alerts.
Power BI consumers must select the validated pack and refresh their report;
service parameter/refresh integration remains separate. T-015/AC-009 still
requires actual Power BI report execution and reconciliation.
