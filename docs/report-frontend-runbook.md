# Start and maintain the local report front end

This runbook manages the optional **MarketAtlas macro research** browser report.
The report is a React dashboard served on this computer by the Data plugin's
local preview service. It needs Node, Python 3.11 or newer, the installed Data
plugin runtime, and a compiled report project. Opening an existing report does
not need PostgreSQL, Dagster or Power BI running.

The existing report is [MarketAtlas macro research](http://127.0.0.1:60114/).
Its project directory is `data/generated/reports/browser/`. The URL works only
on the computer serving the report; it cannot be shared with another computer
as a hosted report.

## Relationship research views

Open **Relationship research** to use the heatmap, dispersion timeline and
indicator-divergence ranking. The initial research selection is Treasury yields
at its latest evaluation. Choose an **Economic group** and **Known by** date;
the heatmap/ranking use that date and the timeline ends at that date. Group/date/
pair selections travel in the app-generated view link and restore on reload.

Click a supported heatmap cell, then **Inspect pair observations**, to reach
**Pair evidence**. Its selector also changes the investigated pair. Read the
paired count/window, correlation/distance/change, exact comparison date, aligned
transformed observations and source records. Expand baseline diagnostics or use
the component's **View data source** action for scoped rows and method/input
identities. The heatmap shows each canonical pair symmetrically; its source
preview retains canonical rows without invented self-correlations.

Current monthly groups have missing-data states. Choose **Inflation**, then
**View latest complete date**, for an explicitly selected supported historical
example. **Latest date** resets to the group's newest evaluation, including its
unavailable results. A blank cell or unavailable ranking is not a zero or a
forecast. The research pack has its own cutoff/capture time, independent of the
daily publication report refresh.

To attach a validated research pack and install the repository's authored views
into the existing report, run from the repository checkout:

```sh
PYTHONPATH=src .venv-dagster/bin/python scripts/refresh-browser-report.py \
  --project data/generated/reports/browser \
  --pack "PASTE_VALIDATED_PUBLICATION_PACK_DIRECTORY" \
  --analytics-pack "PASTE_VALIDATED_MACRO_ANALYTICS_PACK_DIRECTORY" \
  --update-content --run-id manual-analytics-report
```

Use the `pack_directory` returned by `analytics build-macro` for the research
argument. The other `--pack` is the independent existing publication export,
not a macro research pack. See [macro analytics](macro-analytics.md) for preparing
and validating research inputs. Invalid inputs/builds retain the previous report.
`--update-content` deliberately installs tracked views; omit it for ordinary
data-only updates to preserve authored source edits. Presentation edits, app
identity, older immutable sidecars and the local URL remain retained.

Ordinary daily report refreshes retain the last attached research queries and
their original dates. They do **not** generate new analytics. To replace research
data, explicitly supply `--analytics-pack`; automatic analytics generation is a
separate follow-on task. Fresh builds accept a third optional argument:

```sh
./scripts/build-browser-report.sh "PUBLICATION_PACK_DIRECTORY" "NEW_REPORT_PROJECT_DIRECTORY" "MACRO_ANALYTICS_PACK_DIRECTORY"
```

## Open or restart the existing report

In Terminal:

```sh
cd "/Users/joshualutkemuller/Documents/Quant Sandbox/platforms/MarketAtlas"
scripts/report-preview.sh start
```

Open the `url` returned by the command. For the existing project, this is
`http://127.0.0.1:60114/`. A successful start reports `state: "running"` and
`registered: true`. Repeating `start` reuses the project's registered port.
You can close Terminal after successful startup.

The preview is registered as a user login service. It normally restarts after
you log in following a reboot. That starts the web server with its existing
files; it does not rerun the PostgreSQL pipeline or fetch newer data. Keep the
project and Node executable available on disk.

To check or stop just this report:

```sh
scripts/report-preview.sh status
scripts/report-preview.sh stop
```

`stop` unregisters this project's background service while preserving its files
and assigned URL. Run `start` to register/start it again. It does not stop Dagster
or any other application. Check the returned `state` and `registered` fields;
`status` returning successfully alone does not mean the report is running.

To manage a different generated report, pass its project directory:

```sh
scripts/report-preview.sh start data/generated/reports/my-browser-report
scripts/report-preview.sh status data/generated/reports/my-browser-report
scripts/report-preview.sh stop data/generated/reports/my-browser-report
```

Use the returned URL for that project; a new project may get a different port.
The launcher accepts absolute paths too and can be invoked from another working
directory using its absolute path.

## Recreate the report after a clean checkout

Generated apps and restricted exports under `data/generated/` are intentionally
ignored by Git. A fresh checkout therefore contains the report's source and
build scripts, but does not contain your local compiled report or its data.

1. Obtain one validated actual-data pack from a successful
   [Dagster refresh](dagster-orchestration.md), or retain a private copy of the
   existing immutable pack. This must contain the three real macro publications.
2. Build a new project with the command below. Replace `IMMUTABLE_PACK_ID` with
   the folder returned by the successful refresh.
3. Start that project's preview and open the returned URL.

```sh
scripts/build-browser-report.sh \
  data/generated/powerbi-real/IMMUTABLE_PACK_ID \
  data/generated/reports/my-browser-report
scripts/report-preview.sh start data/generated/reports/my-browser-report
```

The builder verifies the pack and refuses to overwrite an existing project.
It creates the React app, copies the repository's report content, and compiles
`dist/index.html` plus its required data sidecar. Serve the whole `dist/`
directory; copying only `index.html` is insufficient.

The report content is tracked in `powerbi/browser/DashboardContent.jsx` and its
reviewed-data transformation in `src/market_atlas/reporting/browser.py`.
[Generated-report instructions](../powerbi/guides/generated-reports.md) also
cover native Power BI project generation.

## Show newer pipeline data

The configured daily Dagster pipeline now updates the existing report after its
PostgreSQL publications and immutable pack pass validation. The report stays at
the same URL and preserves its app identity. The status panel shows the last
successful report update, source stale/unknown counts and failed attempts.
Already-open tabs offer **Reload report** when a newer pack is available;
reload after preserving unsaved edits. A failed update keeps the preceding report.

Use [the local automation runbook](local-automation.md) to start/check/restart
Dagster and inspect its 18:30 New York daily schedule. The report preview and
Dagster are separate user services: opening the report does not start a database
refresh. The Mac must be running and logged in for local daily automation.

To refresh manually from an already validated pack without rerunning PostgreSQL:

```sh
PYTHONPATH=src python3 scripts/refresh-browser-report.py \
  --project data/generated/reports/browser \
  --pack data/generated/powerbi-real/IMMUTABLE_PACK_ID \
  --run-id operator-refresh
```

The optional new-project build commands above remain available for an independent
pinned report. Starting/restarting a preview only serves its existing files.

The default Data plugin location used by the launch/build scripts is:

```text
~/.codex/plugins/cache/openai-curated-remote/data-analytics/1.1.0-exp-homepage
```

If the plugin was updated or moved, set its installed location before running
either script:

```sh
export MARKETATLAS_DATA_PLUGIN="/absolute/path/to/installed/data-analytics/version"
scripts/report-preview.sh start
```

If needed, locate installed candidates with this bounded search, then select the
version installed in your app:

```sh
rg --files --hidden "$HOME/.codex/plugins/cache/openai-curated-remote/data-analytics" \
  | rg '/scripts/data-app-preview[.]mjs$'
```

The runtime is a separate Data plugin dependency; installing the repository's
Python package alone does not install it. Keep generated app runtime files intact.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Browser cannot connect | Run `scripts/report-preview.sh status`, then `start`; open the returned URL. |
| No compiled report | Restore the complete ignored project privately or rebuild from a validated pack into a new directory. |
| Missing Node or Python | Make Node and Python 3.11+ available in Terminal's PATH, then retry. |
| Data preview runtime missing | Verify the Data plugin installation and set `MARKETATLAS_DATA_PLUGIN`. |
| Assigned port occupied | Inspect the specific listener with `lsof -nP -iTCP:60114 -sTCP:LISTEN` (use the reported port). Do not terminate an unrelated process or change the registered port blindly. |
| Login-service permission/startup failure | Read the error and the `logs` path returned by `status`. Retry `start` with the installed Node runtime; do not change machine security policies. |
| Page loads with old data | Check the last refresh/failure notice and Dagster run status. Reload when newer data are offered, or refresh from a validated pack; restarting the server alone does not refresh data. |
| Old appearance after a deliberate rebuild | Reload the existing browser tab after preserving any unsaved personal edits. |

If user login service registration is unavailable on another host, a temporary
loopback-only preview can serve an existing build:

```sh
python3 -m http.server 60115 --bind 127.0.0.1 \
  --directory data/generated/reports/my-browser-report/dist
```

Use this fallback only if port 60115 is free. Open `http://127.0.0.1:60115/`;
keep Terminal running and stop it with Ctrl-C. This temporary server does not
restart after logout/reboot. The normal registered preview remains preferred.

The actual-data report and all its exports are restricted internal-only. This
runbook starts a local preview; cloud publication and access changes require
their own approved sharing scope.
