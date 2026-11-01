# T-028/T-029 — Comparable macro series and analytical relationships

Status: implemented and validated at restricted-local research scope, 2026-10-31.
Evidence: [T-028/T-029 validation](../reports/t028-t029-macro-analytics-validation.md).
User authorized priorities 1 then
2 on a new branch. Branch: `feat/macro-relationship-analytics`, from merged main
`9548eef`. This is an additive research workflow, separate from the existing
instrument-return estimator, taxonomy publication and daily report refresh.

## Capability map and build order

| Module | Responsibility | Depends on |
| --- | --- | --- |
| macro-series | Bounded PostgreSQL capture, explicit transformations, cutoff-aware panels and eligibility | Existing approved source adapter |
| macro-relationships | Rolling correlations, distances, distance changes, standardized dispersion and portable evidence | macro-series |

Build macro-series first, verify temporal and numerical behavior, then build
macro-relationships and exercise a real read-only capture. Existing `docs/tasks.md`
is the task list. These two capabilities implement the user's selected priorities;
browser views, source writes, API ingestion, scheduling and predictive validation
are separate work.

## Objective and initial universe

Answer: which indicators within a declared economic group are moving together,
and where do their standardized changes disagree? These are descriptive research
features, with no alpha, causal or predictive acceptance claim.

Tracked TOML settings declare every series, expected source frequency and unit,
transformation and orientation. Initial groups:

- Inflation: CPI/core CPI/PCE/core PCE, monthly log changes, positive orientation.
- Labor conditions: unemployment/U-6/employment-population, monthly percentage
  point changes; unemployment measures inverted so positive means strengthening.
- Treasury yields: 2/10/30-year yields, daily percentage point changes.

No cross-frequency pairs or automatic all-catalog estimation. Groups are a fixed
operator research selection using current metadata, not historical taxonomy.

## Preparation contract

Read only approved `meta.fred_series`, `gold.fred_point_in_time` and approved
catalog identities from `gold.dim_series`, using the existing source-reader role.
Start the capture in 2010 to assess older history already in PostgreSQL; do not
repair older source rows or infer their vintage dates. Results start in 2024.
Hard limits bound series, pairs, source rows, date spans and panel counts.

Every result has a knowledge date (end-of-day, date precision). Select only raw
versions whose inclusive source real-time interval contains that knowledge date.
Unknown dates, conflicting versions, missing/nonfinite values, unsupported metadata
and absent periods yield explicit unavailable states. Do not replace availability
with ingestion/capture time. Later revisions cannot alter an earlier result.
This is a reconstruction from the captured source histories, not a claim that
MarketAtlas had captured those histories at the historical date.

Monthly knowledge dates are month ends plus the final cutoff if it is a partial
month; their reference window ends in the preceding month. Daily knowledge dates
are weekdays and their reference window ends on the preceding weekday. The daily
grid is conservative weekdays, not a verified Treasury holiday calendar: holidays
remain missing and changes on either side of a missing grid point are withheld.
Never forward fill, interpolate, mix frequencies or widen a fixed window.

Transform adjacent grid observations with either `100 * log(current / previous)`
(positive levels only) or a first difference. Apply declared +1/-1 orientation.
Monthly defaults: 24-period correlation window, 24 paired changes, 12 preceding
changes for standardization. Daily defaults: 63-weekday window, 45 paired changes,
63 preceding weekdays with at least 45 usable changes for standardization.
Standardization uses the preceding baseline only, sample standard deviation
(ddof=1), and no current value in the baseline. Constant baselines are undefined.
These are exploratory method parameters, not statistically proven optimal windows.

Preparation retains the raw capture, selected source records, per-period statuses,
available dates, metadata checks, usable-history counts, settings and hashes.

## Relationship contract

For each configured within-group canonical pair and fixed window, publish Pearson
correlation and `sqrt(2 * (1 - correlation))` distance only with sufficient paired
changes and nonzero variance. Positive/negative correlation remain distinct;
absolute correlation is not substituted. Distance changes compare the exact
configured prior evaluation (3 monthly / 21 daily evaluations), never the nearest
successful result; retain both dates and explicit comparison status.

At the window's latest reference period, standardize each member's oriented
change against its own preceding baseline. Group dispersion is sample standard
deviation across those z-scores. Require every configured group member to be
usable. Publish each member's deviation from the group mean and, independently,
its mean peer distance only when all its configured pair estimates are usable.
Missing members do not silently change the group composition.

All results retain group/series IDs, knowledge/reference dates, sample sizes,
method/configuration identities, input/capture hashes, date-precision availability,
source-record lineage and explicit undefined reasons. Statistical outputs never
become sourced taxonomy assertions.

## Delivery, commands and structure

Python 3.11+ standard library; existing optional PostgreSQL extra only. New modules
live under `src/market_atlas/analytics/`, tests under `tests/`, settings under
`configs/`, private immutable JSON/CSV outputs under ignored `data/generated/`.
Follow existing plain functions, canonical JSON/hash helpers and unittest style.

```sh
PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics prepare-macro --settings configs/macro_analytics.toml --as-of 2026-10-31 --output data/generated/macro-analytics/prepared
PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics build-macro --input <prepared-directory>/prepared.json --output data/generated/macro-analytics/packs
PYTHONPATH=src .venv-dagster/bin/python -m market_atlas analytics validate-macro --input <pack-directory>
PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests -p 'test_macro_analytics*.py' -v
PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests
```

Build content-addressed packs with manifest, retained preparation, JSON results
and typed CSV tables for eligibility, relationships, group dispersion and node
divergence. Verify inputs and recomputed results, stage before final rename, reuse
exact outputs, and reject tampering without replacing an existing pack. File
artifacts are independent research outputs; no new PostgreSQL publication or
browser refresh is claimed.

## Acceptance and verification

- Preparation: independently checked transformations; source-date/interval and
  no-lookahead tests; gaps, ambiguity, unknown dates, metadata mismatch, nonpositive
  log inputs, holiday/weekend and warmup coverage cases; frozen selection hashes.
- Relationships: independent hand-calculated Pearson/distance/z-score/dispersion
  examples, insufficient/constant samples and missing members, exact-lag comparison,
  bounded pair counts, deterministic rerun and tamper/failure isolation checks.
- Live: retain an actual read-only capture, eligibility/exclusion accounting,
  source/input identities, numerical cross-check and validated immutable pack.
  Report how much older history is actually usable, rather than assuming that
  source row counts imply dated historical support.
- Run the full existing suite and repository lint checks; update handoff, task
  status, product scope and acceptance evidence to actual results.

Always preserve source/writer boundaries and explicit unknowns. Do not add
dependencies, modify upstream data, loosen existing age rules, publish private
data publicly, or claim historical metadata, intraday availability or predictive
validity. Wider source repair is separate from this read-only analytical scope.

## Method references

[FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
defines closed source validity intervals. Correlation-network distance follows
[Mantegna, Hierarchical Structure in Financial Markets](https://arxiv.org/abs/cond-mat/9802256).
The macro transformations, grouping, standardization and windows here are explicit
project choices; that paper does not validate this macro application.
