# T-028/T-029 — Macro analytics validation

Validated 2026-10-31, restricted-local research scope. User requested priorities
1 (comparable series) then 2 (analytical relationships) on a new branch.
Branch: `feat/macro-relationship-analytics`, from merged main `9548eef`.
MarketAtlas #14 and EcoMedallion #95 were already merged before this work.

## Implemented result

Tracked [settings](../configs/macro_analytics.toml) declare ten approved FRED
series in three groups, exact expected metadata, transformations/orientations,
windows, sample minima and comparison lags. The existing source adapter captures
bounded history from 2010 through the October 31 cutoff, using the source-reader
role and read-only sessions. No source rows or report publication pointers were
written. Each output date selects only source validity intervals containing that
date, with explicit unknown/ambiguous/missing states and no forward filling.

The implementation creates immutable retained preparations and typed JSON/CSV
research packs through three new `analytics` CLI commands. Correlations/distances,
exact-lag changes, standardized group dispersion and node divergence retain
sample, date and source evidence. It does not reuse the instrument-price return
transform or turn statistical results into taxonomy assertions.

## Actual source capture and output

The final CLI prepare/build/replay/check sequence completed in 15.602 seconds
locally with Python 3.12. This is one local observation, not a performance SLA.
Capture record time is `2026-11-01T02:36:01.721818+00:00` (October 31 in New York).
The source knowledge cutoff remains **2026-10-31**; capture and availability are
distinct. Capture contained **19,963 versions**, ten series and 808 evaluation
panels. All ten matched their expected source metadata.

| Group | Evaluation panels | Pair/date rows | Supported pairs | Supported group dispersions |
| --- | ---: | ---: | ---: | ---: |
| Inflation | 34 | 204 | 134 | 21 |
| Labor conditions | 34 | 102 | 63 | 21 |
| Treasury yields | 740 | 2,220 | 2,067 | 598 |
| Total | 808 | 2,526 | 2,264 | 640 |

The pack also contains 2,458 node/date rows and ten series eligibility rows.
There are 262 `insufficient_sample` pair rows and 168 `incomplete_group` rows;
undefined estimates remain null. These are not numerical failures or zero values.

All seven monthly members have usable source-dated history from 2010. Each
Treasury series has 3,651 undated pre-2024 versions in the retained lookback;
all 10,953 remain excluded. Its earliest usable dated period is 2024-01-02, and
the first supported daily pair estimates appear on 2024-03-12 after warmup.

Five monthly members mark October 2025 as source-missing. Both October's change
and the next adjacent change are withheld. The current strict monthly 24-change
windows/12-change baselines therefore withhold affected relationships and complete
group dispersion. This source gap was preserved; no source repair or threshold
relaxation was used to make these results appear supported. The latest Treasury
group at knowledge date October 30 is supported. Current source age flags and
the existing report remain separate from these analytical eligibility checks.

## Independent numerical check

[scripts/verify-macro-analytics.py](../scripts/verify-macro-analytics.py) does not
import the production preparation/relationship implementation. It reconstructs
changes and standardization from retained raw source vintages, uses 50-digit
Decimal logarithms/arithmetic and the independent sum-product Pearson formula,
and checks estimates at absolute tolerance **1e-10**.

Passed against the final pack:

- 127,624 supported transformed points, including adjacent-period/source-date checks.
- All 2,264 supported correlations and their correlation distances.
- All 1,957 supported z-scores with preceding-only baselines.
- All 640 supported group means and sample dispersions.

Focused closed-form tests additionally check correlation 0.5/distance 1,
correlation -1/distance 2, z-score orientation, sample dispersion 2 for
`[2, 0, -2]`, and mean peer distance 1.5. These are synthetic numerical examples,
not real economic values. Large finite inputs do not silently turn norm overflow
into zero correlation.

## Integrity, temporal and regression checks

The 23 new focused tests pass. They cover:

- Later revisions excluded from earlier panels; inclusive interval boundaries and
  expired intervals; gaps, unknown/conflicting vintages and no synthetic adjacent
  change across a missing period.
- Exact metadata checks, nonpositive log inputs, nonfinite/invalid value states,
  constant baselines, monthly leap/partial dates, weekday/holiday gaps, bounded
  configuration/capture and rejection of unapproved catalog identities.
- Canonical pair ordering, shared fixed grids, insufficient/constant samples,
  incomplete groups and peers, exact prior-evaluation comparison without jumping
  over an unavailable prior result.
- Offline preparation without credentials, CLI build/validate, typed CSV keys,
  exact reuse, input/derived-panel tampering, corrupt existing pack rejection and
  staged-build failure preserving the previous completed pack.

The final live retained-input replay returned the identical pack response and
unchanged manifest bytes. `build-macro` reconstructed and validated artifacts
before final directory rename; the exact rerun validated the existing pack.

Full pinned-environment suite: **143 tests, 138 passed, five opt-in PostgreSQL
skips**. Standard-library-only `python -S` suite: **143 tests, 129 passed, 14
optional/database skips**. Ruff passes on every changed Python file; diff checks
pass. Repository-wide Ruff reports **11 pre-existing findings in five untouched
files**. Every affected file was compared byte-for-byte with `origin/main`
`9548eef` and is unchanged; these findings are not represented as a clean whole-
repository lint pass. See the private baseline proof below. No new SQL migration
or database writer path requires opt-in database writes for this feature.

## Retained local evidence

Restricted row-level artifacts remain ignored under `data/generated/`:

- Summary: `data/generated/macro-analytics/validation-summary.json`.
- Final preparation: `data/generated/macro-analytics/prepared/ddb682876521e92a3393ff161c4f76ee4c2e0e69fedd5b6b89b323220b4801e1/prepared.json`.
- Final pack: `data/generated/macro-analytics/packs/a56bd8f7591762d8664a7c03eefe4e0d9406469d421c56808f48c6cf589d56d1/`.
- Source-row hash: `db87078354ab859bcb1edcf6086357e6f2962fc82d15fbdd8aaa804e96ea23b5`.
- Final manifest file hash: `913bd43964662878eb4dbf7e5b3a300f5cfaa9e29218f4a48d4b8e1f44fa57a1`.
- Numerical proof: `data/generated/macro-analytics/independent-numerics.json`.
- Test logs: `data/generated/macro-analytics/full-tests.log` and `core-tests.log`.
- Baseline lint proof: `data/generated/macro-analytics/baseline-lint.json`.

The earlier prototype capture/pack remains local; the final CLI summary identifies
the authoritative validated run. No credentials or source rows are in this report.

## Limits and next task

These are descriptive research features. Sample thresholds are method choices,
not a predictive validation or statistical significance guarantee. Standardization
does not establish stationarity. Pairwise missingness may prevent a shared metric
embedding. Current metadata and fixed operator groups do not establish historical
taxonomy or a survivor-free universe. Source dates have day precision; the result
reconstructs source history and does not claim past MarketAtlas possession.

No pre-2024 upstream repair, external API capture, new Dagster schedule, PostgreSQL
analytical publication, browser/report integration, cloud publication or predictive
backtest was added. Power BI execution remains open. The next product task is to
consume the validated pack in the browser with a relationship heatmap, dispersion
timeline and divergence ranking while preserving unavailable rows and evidence.
See [runbook](../docs/macro-analytics.md) and
[method spec](../docs/t028-t029-macro-analytics-spec.md).
