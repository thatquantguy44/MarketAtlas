# Editable reports and a browser view

`build-report-project.py` creates a native Power BI project with a semantic
model, explicit columns/relationships/DAX, and five authored PBIR pages.
It validates the immutable CSV pack before creating a new output directory.
Existing projects are never overwritten. The project contains no credentials
or copied data rows; keep the selected pack available privately.

```sh
PYTHONPATH=src python3 -S scripts/build-report-project.py \
  --pack data/generated/powerbi-real/IMMUTABLE_PACK_ID \
  --output data/generated/reports/my-powerbi-project
```

Use the pack folder returned by the successful daily refresh, replacing
`IMMUTABLE_PACK_ID`. A fixture pack from `powerbi export` works too. Fixture
pages cover snapshot/quality, market map, context, correlation and provenance;
actual-data pages cover publication status, catalog coverage, releases/freshness,
revision quality and provenance. Both have five pages.

Open the generated `MarketAtlas.pbip` in an authorized Windows Power BI Desktop
environment with project/enhanced-report support enabled. Its Import model reads
one `pPackFolder`; when moving computers, copy that pack privately and change
this parameter before refresh. Time-zone-bearing timestamps are normalized to
UTC. Role-playing dimensions use active single-direction relationships.
Correlations remain blank when undefined; they are not averaged across pairs.
Evidence pages provide explicit subject/kind selection; cross-page drill-through
is not yet configured. Complete the [AC-009 checklist](../README.md#ac-009-reconciliation-script)
in Power BI before treating the source as an accepted report. The CSV fixture
project also does not replace T-015's PostgreSQL connector/refresh exercise.

The native source passed Microsoft's published PBIP/PBIR JSON schemas. This
checks file structure, not DAX evaluation, Power Query execution, connector
behavior or visual rendering. To repeat schema validation in an isolated Python
environment with `jsonschema==4.25.1` and system `curl` installed:

```sh
python scripts/validate-report-project.py data/generated/reports/my-powerbi-project
```

The validator fetches official Microsoft schemas and caches them in the system
temporary directory. See Microsoft's [report project files](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
and [semantic-model project files](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).

## Use the actual data without Power BI

For start, stop, reboot recovery and clean-checkout setup, use the
[report front-end runbook](../../docs/report-frontend-runbook.md).

The optional browser report has four views: catalog coverage, releases and
freshness, revision quality, and publication/source evidence. It needs no
Power BI account. It displays an immutable export, not a live database connection.
Concept filtering applies to the count, chart and series table; series selection
links a quality summary to its version's provenance. Dates, null metrics and
independent publication IDs remain available for inspection.

The current local preview is [MarketAtlas macro research](http://127.0.0.1:60114/).
It runs only on this computer. A user login service restarts the preview after
login. The configured daily Dagster job now updates this existing report after
pack validation; other independent generated projects remain pinned until refreshed.
See [local automation](../../docs/local-automation.md). No cloud hosting is configured.

To generate a new browser report from another validated actual-data pack, use
the installed Data plugin's bundled runtime (Node is required):

```sh
scripts/build-browser-report.sh \
  data/generated/powerbi-real/IMMUTABLE_PACK_ID \
  data/generated/reports/my-browser-report
```

Set `MARKETATLAS_DATA_PLUGIN` if the installed Data plugin is at a different
location. The script creates a new editable app, copies the tracked content
from `powerbi/browser/`, and builds `dist/` with the complete reviewed snapshot
and source metadata. It refuses to replace an existing project. To serve it,
run `scripts/report-preview.sh start REPORT_PROJECT_DIRECTORY`.
The source snapshot can also be generated independently with
`market_atlas.reporting.browser.browser_snapshot(pack)`.

The app and its exported files contain restricted internal data. Keep generated
projects/packs under ignored `data/generated/`. Public sharing remains
unauthorized. The browser report is useful local access; it does not establish
Power BI acceptance, upstream FRED freshness or historical source availability.
