# Macro series preparation and relationship research

Use this workflow to compare changes within explicit inflation, labor-condition
and Treasury-yield groups. It reads PostgreSQL and produces private, immutable
JSON/CSV packs. It does not modify upstream data, existing report publications,
the browser report or the daily Dagster job.

## Run it again

Run from the repository root with the existing `.venv-dagster` environment and
ignored `configs/local.toml`. PostgreSQL must be reachable and the configured
source role must remain `marketatlas_source_reader`. A fresh environment can use
the setup in [the orchestration runbook](dagster-orchestration.md#start-the-local-runtime);
the calculations themselves use only Python's standard library.

1. Edit [configs/macro_analytics.toml](../configs/macro_analytics.toml) to select
   the approved groups, lookback and sample rules. The default source lookback is
   2010; output starts in 2024. Choose an explicit cutoff for reproducibility.
2. Prepare the source capture and date-specific analytical panels:

   ```sh
   PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics prepare-macro \
     --settings configs/macro_analytics.toml --as-of 2026-10-31 \
     --output data/generated/macro-analytics/prepared
   ```

   The JSON response gives `prepared_file`. Copy that path into the next command
   in place of `PASTE_PREPARED_FILE_HERE`.
3. Calculate and validate the research pack:

   ```sh
   PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics build-macro \
     --input "PASTE_PREPARED_FILE_HERE" \
     --output data/generated/macro-analytics/packs
   ```

   The response gives `pack_directory`, row counts and estimate-status counts.
   An unavailable estimate is a valid explicit result, not a failed build.
4. Copy `pack_directory` into these independent checks:

   ```sh
   PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics validate-macro \
     --input "PASTE_PACK_DIRECTORY_HERE"
   .venv-dagster/bin/python scripts/verify-macro-analytics.py \
     --input "PASTE_PACK_DIRECTORY_HERE"
   ```

The first check reconstructs the pack and compares hashes, method outputs, table
grains and CSV bytes. The second uses independent 50-digit Decimal arithmetic
against the retained raw inputs, with absolute tolerance `1e-10`.

Rebuilding the same retained preparation returns the same validated pack. A fresh
database capture has its own record timestamp and preparation identity, even
when source values are unchanged. Corrupt existing artifacts are rejected rather
than overwritten. An interrupted build leaves earlier completed packs intact;
retry the command. The CLI returns a nonzero exit code for invalid settings,
source access failures or artifact integrity failures.

## Read the outputs

Each pack directory contains:

| File | Grain and use |
| --- | --- |
| `series_eligibility.csv` | One group/series: expected and observed metadata, raw/unknown/invalid vintage counts, usable period count and earliest usable period at the final cutoff |
| `relationships.csv` | One group/knowledge date/canonical pair: fixed-window Pearson correlation, correlation distance, coverage and distance change |
| `group_dispersion.csv` | One group/knowledge date: cross-member sample standard deviation of standardized changes, group completeness and dispersion change |
| `node_divergence.csv` | One group/knowledge date/series: standardized change, signed/absolute deviation from the complete group mean, mean peer distance and its change |
| `schema.json` | Stable column types, primary keys, row counts and CSV null encoding |
| `prepared.json` | Frozen settings, raw source capture, eligibility, per-date transformed panels, baseline diagnostics and source-record lineage |
| `results.json` | The analytical rows and method/source identities |
| `manifest.json` | Pack identity, input/method hashes, per-file checksums/byte counts, row/status counts and use restrictions |

`series_eligibility.status` describes metadata compatibility. Sample eligibility
is separate: inspect the prepared member's `usable_change_count`,
`point_status_counts`, `baseline_count` and `zscore_status`, plus the corresponding
relationship/group status. A compatible series can still have insufficient data.

CSV blanks mean null, never zero. Filter `estimate_status = supported` for pair
and group numeric views, and inspect `zscore_status`/`peer_distance_status` for
nodes. Keep the unavailable rows for coverage reporting. All CSVs carry method,
preparation, settings and source hashes, cutoff, capture time and redistribution
status. Join rows only within the same pack; use the declared keys. Group/date
and `input_sha256` locate full source-record evidence in `prepared.json`.

These are a separate `macro-analytics-pack-v1` contract, not the existing
publication-based Power BI pack. They can be imported as typed CSVs using
`schema.json`. The browser's **Relationship research** tab now consumes the
validated pack independently; follow the
[front-end runbook](report-frontend-runbook.md#relationship-research-views) to
attach it while retaining the existing report URL. Native Power BI generator
integration remains future work. Source captures and packs remain ignored under `data/generated/` and are
restricted internal-only. They are not public repository artifacts.

## Interpret the method

Monthly windows contain 24 calendar months and require 24 paired changes. Their
z-score baselines require all 12 preceding monthly changes. Daily Treasury windows
contain 63 weekdays and require at least 45 paired changes; baselines use the
preceding 63 weekdays with at least 45 usable changes. No window widens to find
more observations. No series is forward filled or interpolated.

Inflation uses `100 * log(current / previous)`, not annualized inflation. Rates
and labor ratios use percentage point differences. Labor unemployment measures
have negative orientation, while employment-population has positive orientation.
Thus positive labor changes mean strengthening by this explicit research
convention. Inspect the configured orientation before interpreting signs.

Distance is `sqrt(2 * (1 - correlation))`, between 0 and 2. Strong positive movement
is close; strong negative movement is far. It is not a screen distance, causal
relationship or measure of predictive value. Pairwise missingness can prevent
the whole distance table from having a common metric embedding.

Dispersion compares each member's latest transformed change after standardizing
against its own preceding baseline (sample standard deviation, excluding the
current point). High dispersion means disagreement in those standardized changes.
Every configured member must be usable; members are not dropped to produce a
number. Standardization does not guarantee stationarity or forecast usefulness.

Changes compare exactly 3 monthly or 21 daily prior evaluations and retain the
actual comparison date. Missing/undefined prior results remain unavailable;
the workflow does not jump to the nearest successful estimate. A partial final
month is an additional evaluation, explicitly dated.

## Time and coverage limitations

Each result selects source real-time intervals at its own `knowledge_date`, with
inclusive boundaries. Monthly reference windows end in the preceding month;
daily windows end on the preceding weekday. Publication lags may still leave the
last period unknown. Weekdays are a conservative grid, not a verified holiday
calendar: missing holidays also withhold the next adjacent change.

Date precision supports availability by that date, not intraday release timing.
This reconstructs source history from a later retained capture; it does not claim
that MarketAtlas possessed the data on the historical result date. Current source
metadata and a fixed operator-defined research universe are used throughout;
historical taxonomy and survivor-free universe construction are not established.

The October 31 validation found usable monthly history back to 2010. Treasury
history before 2024 has unknown source-vintage dates and stays excluded. Several
monthly series mark October 2025 as missing; October and November changes are
therefore unavailable. The strict current monthly windows/baselines withhold
affected estimates rather than bridging this gap. See the retained
[validation evidence](../reports/t028-t029-macro-analytics-validation.md).

Adding a member requires an approved FRED catalog identity, matching metadata,
an explicit transformation/orientation, compatible group frequency and adequate
source-dated history. Quarterly, weekly, mixed-frequency, cross-group estimation
and automatic all-pairs catalog expansion are unsupported. Configurations are
bounded to 50 unique series, 100 configured within-group pairs, 250,000 source
versions, a 25-year capture span, 10,000 panels and 2 million preparation cells.

Method changes require a new reviewed configuration/method version and fresh
validation. Source repair, automatic analytics scheduling and predictive research
remain separate tasks. The [feature specification](t028-t029-macro-analytics-spec.md)
records the full contract and primary method references.

## Replay without PostgreSQL

Extract the retained raw capture from a completed preparation, then pass it to
`prepare-macro --capture`. The cutoff and source start must match that capture:

```sh
python3 - <<'PY'
import json
from pathlib import Path
prepared = json.loads(Path("PASTE_PREPARED_FILE_HERE").read_text())
Path("data/generated/macro-analytics/retained-capture.json").write_text(
    json.dumps(prepared["capture"], sort_keys=True) + "\n"
)
PY
PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics prepare-macro \
  --capture data/generated/macro-analytics/retained-capture.json \
  --settings configs/macro_analytics.toml --as-of 2026-10-31 \
  --output data/generated/macro-analytics/prepared
```

This path requires no database configuration. To change the source start or
capture cutoff, make a new bounded source capture.
