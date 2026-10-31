# Supported PostgreSQL series and eligibility

The daily pipeline discovers **all eligible series in the approved catalog**.
It does not interpret every readable upstream object or identifier as an approved
integration. Discovery reads the existing contracts for `gold.dim_series`,
`meta.fred_series` and `gold.fred_point_in_time`; context and quality use their
existing approved views. No source tables are modified and no external API is
called. The bounded observation history starts January 1, 2024 and ends at the
New York run date with the same knowledge cutoff.

## Verified expansion, October 30, 2026

| Surface | Previous | Expanded validated scope |
| --- | ---: | ---: |
| Descriptive catalog | 290 series / 11 concepts | 290 series / 11 concepts |
| Point-in-time observation ingestion | 3 series / 151 versions | 94 series / 35,576 versions |
| Current source coverage | 3 series | 268 FRED series |
| Current revision-quality publication | 3 selected summaries | 268 selected summaries |

The expanded live run inserted 35,425 additional observation versions. The
catalog remains broader than the observation selection. These are macro
observations and descriptive/current-quality outputs; the change does not
create all-pairs correlations, historical taxonomy, causal estimates or investment
signals.

## Different eligibility rules

**Catalog:** retain all 290 approved `gold.dim_series` entries, including their
actual source labels and descriptive taxonomy. The graph has 301 nodes and
290 sourced edges.

**Current coverage and revision quality:** select active FRED catalog entries
with usable source metadata: identity, title, frequency and units. This produced
268 series. Captured-current quality is useful even when historical source-vintage
dates are unavailable. Missing summary metrics remain unknown rather than zero.

**Point-in-time observations:** additionally require usable observations within
the selected date window, consistent value/missing flags and known, ordered
source-vintage dates. The current selection contains 94 series and 35,576
observation versions. The chosen IDs are frozen into the run plan and retained
for native recovery. Each fresh run rediscovers eligibility under the same rules.

The initial wider probe stopped before any observation writes because 170 series
had blank source-vintage dates (35,433 rows in that candidate capture). Those
series remain usable for current-context/quality reporting, but do not enter the
point-in-time ingestion selection. MarketAtlas does not substitute record time
or extraction time for unknown availability. Four other FRED series had no usable
observations in the configured window: `ANFCI`, `NFCI`, `NFCICREDIT` and `NFCIRISK`.

The other 22 catalog entries are 20 ECB and two BLS entries. They remain visible
in the descriptive graph, but the FRED observation adapter must not assign them
FRED source identities. Source-specific observation adapters and eligibility
contracts are the next onboarding work for those series. Two BLS catalog entries
also have missing units, which need an authoritative upstream fix.

Other upstream identifiers exist outside this catalog. Expanding to them requires
catalog/source onboarding and valid temporal/metadata contracts; this change does
not silently promote them because they are readable.

## Bounds and freshness

Discovery is capped at 1,000 catalog entries and observation extraction at 250,000
versions per run. Source checks batch 25 series, extraction reads bounded pages,
and the pipeline fails before ingestion if its configured limits are exceeded.
All source queries use parameters, a read-only session and statement timeouts.
Full extract validation remains in force before opening the write transaction.

In the expanded source-coverage snapshot, 181 of 268 source/series records carry
the upstream stale flag; zero have an unknown stale flag. These are supplied
current-state flags, not a new universal age threshold. Daily MarketAtlas refreshes
do not update upstream APIs. The report explicitly shows source freshness beside
report refresh time and keeps historical availability limitations visible.

Private per-run `series_selection.json` records the catalog size, independent
observation/context ID lists, window, counts and every exclusion reason. Pack
manifests retain counts, hashes and independent publication IDs. Restricted source
captures and row-level profiles remain under ignored `data/generated/`.
