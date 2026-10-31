# Local daily refresh and report delivery

The local Dagster pipeline now includes browser-report delivery after publication
and pack validation. It refreshes the same app at http://127.0.0.1:60114/; a failed
candidate build leaves the previous report and its data available. Source access
remains read-only and writes remain confined to MarketAtlas schemas.

## Start, inspect, restart or stop Dagster

From the repository directory:

```sh
scripts/dagster-service.sh start
scripts/dagster-service.sh status
scripts/dagster-service.sh restart
scripts/dagster-service.sh stop
```

`start` registers a macOS user LaunchAgent, starts the existing local Dagster
stack and retains `.dagster/` run/schedule history. `status` reports registration,
process state, UI listening status and a log path. Registration alone is not a
health check. Open [Dagster](http://127.0.0.1:3001/) and confirm the code location
and daemon health. `restart` gracefully replaces this service and waits for its
port to clear. `stop` unloads this service and removes its login registration;
`start` recreates it. These commands do not stop the report preview or PostgreSQL.
Do not use `scripts/dagster-dev.sh` concurrently on the same port.

The service starts after user login and restarts after its process exits. It is
a supervised **local development/pilot stack**, not a production deployment.
The Mac must be running, logged in and able to reach PostgreSQL. It does not wake
the computer or run while powered off; review missed ticks after downtime.

The service entry point and non-secret path configuration live under
`~/.codex/plugin-data/marketatlas/dagster/`. The LaunchAgent is
`~/Library/LaunchAgents/com.marketatlas.dagster.plist`. Its Node supervisor starts
Python through the pinned environment's packages, with a runtime working directory
outside `Documents`. This avoids invoking the virtualenv's shell trampoline from
a protected working directory. No macOS privacy/security settings are changed.
Credentials remain in ignored `configs/local.toml`; the service stores paths only.
Keep this checkout, `.venv-dagster/`, Node and the installed Data plugin available.
The service executes this checkout's current files; after changing branches or
settings, restart it and verify the loaded definitions. After moving the checkout
or changing runtimes, stop/reinstall the service from
the intended checkout; a different checkout cannot silently take over ownership.

## Daily schedule

The existing local `fred_daily_schedule` is verified **RUNNING** at **18:30
America/New_York every day**. Schedule state is persisted in `.dagster/`; a fresh
instance still defaults to stopped. In the Dagster UI, open Schedules and enable
`fred_daily_schedule` after validating its credentials, source access and report
project. Stop it there to pause daily launches without stopping the UI.

The schedule consumes approved existing PostgreSQL interfaces. It does not launch
upstream FRED/API ingestion. A freshly built report can therefore still show stale
source flags; report refresh time and source freshness are separate.

## How delivery works

The 14 ordered stages end with `export_powerbi`, `validate_powerbi`,
`refresh_browser_report`, then `complete_refresh`. Settings:

```toml
refresh_browser_report = true
browser_report_directory = "data/generated/reports/browser"
series_selection_mode = "all_eligible"
max_series = 1000
max_observation_rows = 250000
```

These belong in `[pipeline]` in `configs/orchestration.toml`, or a selected ignored
local settings file. Set `refresh_browser_report = false` for a database/export-only
run. When enabled, the target must already be a compiled report project; recreate
it with the [front-end runbook](report-frontend-runbook.md) on a clean checkout.
The Data plugin's bundled runtime and Node must also be available to the service.
Set `MARKETATLAS_DATA_PLUGIN` before installing the service if using another plugin
location. The app, source files, credentials and runtime are not copied to a cloud.

Each update builds a candidate in an ignored temporary sibling directory,
validates its build checksums, retains the existing app ID/title/owner metadata,
and copies immutable assets before atomically replacing `index.html` last.
Previous data sidecars stay available to already-open tabs. A failure before
that commit point rolls back the source snapshot/build metadata; it never
replaces the visible report with a partial build. Avoid concurrent manual builds
or publishers for the same app. Old immutable sidecars are retained; no automatic
pruning is configured.

The report polls its operational status every 30 seconds. It shows the successful
report refresh time, supplied stale/unknown coverage counts and upstream-ingestion
verification status. A failed pipeline attempt keeps the previous report and adds
a failure notice. When a newer pack is available to an already-open tab, choose
**Reload report** after preserving unsaved edits. The app does not force a reload.
Filters and personal presentation remain tied to the same app ID and origin.

For a manual refresh from an already validated pack:

```sh
PYTHONPATH=src python3 scripts/refresh-browser-report.py \
  --project data/generated/reports/browser \
  --pack data/generated/powerbi-real/IMMUTABLE_PACK_ID \
  --run-id operator-refresh
```

A standalone builder failure leaves the report intact and returns an error;
Dagster additionally records failed-attempt status. Service logs are in the runtime
directory; per-run plans, captures, selection/exclusion decisions and checkpoints
remain under ignored `data/generated/daily/<run-id>/`.

Checkpoint format is now version 3 because report delivery and frozen series
selection change the stage/checkpoint contract. Start a fresh full run for older
checkpoints. Native re-execution of new checkpoints retains the original observation
and context selections, dates and verified captures.

[Series eligibility and coverage](series-coverage.md) explains the different
catalog, observation and current-context/quality populations.
