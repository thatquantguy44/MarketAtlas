# Reports worth building

Start with **Market relationship explorer** and **Correlation regime monitor**
using a synthetic pack. With an internal published-data pack, add **Macro research
coverage**, **Release calendar and freshness**, and **Revision-quality watch**.
Keep a **Why this result?** provenance page in every report. Each page should
answer a question before adding decorative visuals.

Use Import mode for these bounded packs. Keep raw keys hidden in the main page,
but available in drill-through and tooltips. Show a synthetic/internal label,
publication snapshot, capture/cutoff where available, and publication time on
each applicable page. File export time is not source freshness. Keep unknown
values visible as unknown. Avoid red/green-only encodings; pair color with
text or shape.

## Model before visuals

Load the tables as described in [data jobs](data-jobs.md). Remove automatically
detected relationships that conflict with this model. Use one-to-many,
single-direction dimension-to-fact relationships:

| Dimension / key | Fact / foreign key | Use |
| --- | --- | --- |
| `SourceNode[node_id]` | `relationships[source_node_id]` | Outgoing connections |
| `TargetNode[node_id]` | `relationships[target_node_id]` | Incoming endpoint filters |
| `ContextSeries[node_id]` | `contexts[macro_series_node_id]` | Macro context |
| `ContextTarget[node_id]` | `contexts[target_node_id]` | Context target |
| `pairs[pair_id]` | `correlations[pair_id]` | Pair selection |
| `dates[date]` | `correlations[endpoint_session_date]` | Endpoint selection |
| `MacroSeries[node_id]` | `macro_edges[source_node_id]` | Series taxonomy |
| `MacroConcept[node_id]` | `macro_edges[target_node_id]` | Concept taxonomy |
| `MacroSeries[node_id]` | `revision_quality[series_node_id]` | Independent quality selection |
| `MacroSeries[node_id]` | `Coverage[series_node_id]` | Source coverage |

Create `SourceNode`, `TargetNode`, `ContextSeries`, and `ContextTarget` as
separate reference copies of `nodes`; for `ContextSeries`, filter `node_type`
to `macro_series`. `MacroSeries` and `MacroConcept` are reference copies of
`macro_nodes` filtered to `macro_series` and `economic_concept`. These role
copies allow separate active endpoint filters without ambiguous paths. Keep
`nodes` disconnected for whole-universe inventory measures. Keep `publications`
as a disconnected status table; use a separate card/row for each publication.

Create `Coverage` and `Releases` as Power Query references to `source_context`:

```powerquery
// Query name: Coverage
= Table.SelectRows(source_context, each [context_kind] = "source_coverage")
```

```powerquery
// Query name: Releases
= Table.SelectRows(source_context, each [context_kind] = "release_event")
```

Do not aggregate the mixed `source_context` table directly as a time series.
Use release tables independently: a release may have only a representative
series, and its key is the release occurrence, not every series in that release.

For initial inspection, leave provenance tables disconnected and select subject
kind and ID directly on the evidence page. To enable cross-page drill-through,
add the shared evidence dimension described under page 6. IDs alone are not
globally unique across kinds. Do
not join fact tables to each other or enable bidirectional relationships to make
a measure "work". For a selected source node, count target IDs in the
relationship fact rather than counting all rows of the disconnected universe.

These choices follow Microsoft's guidance on
[star schemas and role-playing dimensions](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)
and [active relationships](https://learn.microsoft.com/en-us/power-bi/guidance/relationships-active-inactive).

## 1. Market relationship explorer

**Question:** What connects this instrument to its issuer, country, index or
macro context, and which links are disputed or retracted?

- Left: `SourceNode[display_label]` slicer and relationship-type/status slicers.
- Center: relationship table with source/target display labels, edge type,
  status, kind, and rationale. Use `RELATED(SourceNode[display_label])` and
  `RELATED(TargetNode[display_label])` as calculated columns if helpful.
- Right: cards for visible connections, distinct targets and disputed/retracted
  counts. Include a details tooltip with source record and assertion ID.
- Bottom: separate macro-context table with series, target, evidence basis,
  rationale and owner. Add its own series/target slicers; this table does not
  automatically inherit an instrument selection through a fact-to-fact join.

```dax
Visible Connections = DISTINCTCOUNT(relationships[assertion_id])
Distinct Targets = DISTINCTCOUNT(relationships[target_node_id])
Disputed Connections =
    CALCULATE([Visible Connections], relationships[assertion_status] = "disputed")
Retracted Connections =
    CALCULATE([Visible Connections], relationships[assertion_status] = "retracted")
Universe Instruments =
    CALCULATE(DISTINCTCOUNT(nodes[node_id]), nodes[node_type] = "instrument")
```

Label context as **context only, not measured sensitivity or causality**. Keep
retracted versions visible for explanation but exclude them from a visual
purporting to show active accepted links. The fixture's A15 is a retraction;
showing it as an active technology link would be wrong. A static pack's date
slicer does not replay historical graph state.

**Check:** clearing source/target/status slicers yields 14 relationship versions
and 3 universe instruments for the fixture. Selecting a source changes fact
counts, while `Universe Instruments` intentionally remains a whole-universe
count. Adding target classifications must not multiply correlation rows.

## 2. Correlation regime monitor

**Question:** How has a configured pair's return correlation moved, and is the
estimate usable?

- Top: single-select `pairs[pair_label]` slicer and endpoint date range.
- Main: line chart, `dates[date]` on the axis and `Correlation` as the value.
- Below: paired-return counts and a status table using raw endpoint, method,
  sample count and estimate status. Keep zero-variance/undefined rows visible.
- Optional matrix: pair label × endpoint date colored by correlation; preserve
  blank values and use a fixed -1 to +1 diverging color scale.

```dax
Estimate Count = DISTINCTCOUNT(correlations[rolling_correlation_estimate_version_id])
Supported Estimates =
    CALCULATE([Estimate Count], correlations[estimate_status] = "supported")
Correlation =
    IF(HASONEVALUE(pairs[pair_id]) && HASONEVALUE(dates[date]),
       SELECTEDVALUE(correlations[correlation]))
Paired Returns =
    IF(HASONEVALUE(pairs[pair_id]) && HASONEVALUE(dates[date]),
       SELECTEDVALUE(correlations[paired_return_count]))
Latest Correlation =
    VAR Endpoint = CALCULATE(MAX(correlations[endpoint_session_date]), REMOVEFILTERS(dates))
    RETURN IF(HASONEVALUE(pairs[pair_id]),
        CALCULATE([Correlation], REMOVEFILTERS(dates), dates[date] = Endpoint))
Previous Correlation =
    VAR Endpoint = CALCULATE(MAX(correlations[endpoint_session_date]), REMOVEFILTERS(dates))
    VAR PreviousEndpoint = CALCULATE(MAX(correlations[endpoint_session_date]),
        REMOVEFILTERS(dates), correlations[endpoint_session_date] < Endpoint)
    RETURN IF(HASONEVALUE(pairs[pair_id]),
        CALCULATE([Correlation], REMOVEFILTERS(dates), dates[date] = PreviousEndpoint))
Latest Change =
    IF(NOT ISBLANK([Latest Correlation]) && NOT ISBLANK([Previous Correlation]),
       [Latest Correlation] - [Previous Correlation])
```

The latest cards intentionally ignore the date-range slicer and compare the
last two available endpoints for the selected pair; label them accordingly.
The line respects the date range. Do not average correlations across pairs or
sum estimates across time. The method uses 60 scheduled sessions and at least
45 paired returns, without filling missing prices. The synthetic weekday
calendar omits real market holidays.

**Check:** with all pairs/endpoints visible, the fixture has 32 estimate rows:
16 supported and 16 zero-variance. Constant-share estimates stay blank, not
zero. Single-pair/endpoint tooltips agree with the exported numerical value and
paired count. An undefined latest endpoint must remain undefined rather than
falling back silently to an earlier supported estimate.

## 3. Macro research coverage

**Question:** What economic concepts does the approved catalog cover, and where
are the research gaps?

- Horizontal bar chart: `MacroConcept[display_label]` with distinct series count
  from `macro_edges[source_node_id]`. Sort by coverage, not alphabetically.
- Searchable series table: `MacroSeries[display_label]`, frequency, units,
  source, temporal status and source record. Available `details_*` attributes
  depend on the publication and are enumerated in the manifest.
- Frequency distribution and count cards, with concept/series search controls.
- A page note distinguishes **cataloged** from **observations ingested**,
  **analytically eligible**, and **selected for quality**.

```dax
Catalog Series = DISTINCTCOUNT(MacroSeries[node_id])
Series In Concept = DISTINCTCOUNT(macro_edges[source_node_id])
```

A concept filters the edge fact, not the separate series dimension through a
bidirectional path. For a concept-filtered series list, use a table of series
and apply a visual filter `Series In Concept > 0` rather than changing global
relationships. Count distinct IDs rather than summing per-concept counts when
series may belong to multiple concepts.

**Check:** the retained local catalog baseline is 290 series and 11 concepts;
reconcile the current exported pack rather than hard-coding those as live
constants. The graph represents descriptive current taxonomy. UI `contains`
navigation links are not source-backed assertions and are not exported as such.

## 4. Release calendar and freshness

**Question:** What releases are scheduled, and which approved series have stale
or incomplete source coverage?

- Upcoming-release table: `Releases[effective_date]`, release name, category,
  importance and representative series. Use a relative-date filter on the
  actual release date. Show the source capture date beside the schedule.
- Stale-coverage table: series, latest observation date, source, observation
  count and supplied stale flag. Use `details_is_stale = true` as a filter.
- Bar chart of stale coverage records by source or frequency. Label the unit
  **source/series records**; one series can appear under multiple sources.

Use the source's stale flag rather than inventing a universal threshold that
would misclassify monthly/quarterly series. `details_days_since_last` and
`details_is_future` describe the capture, not today's recalculation. If adding
an age-in-days measure, explicitly label its clock and retain the source value.
Scheduled dates are not realized announcement times or market-impact signals.

**Check:** separate `series_taxonomy`, `release_event` and `source_coverage`
grains; blank representative series must not remove a release from the table.
A newly exported old publication must still show its original capture date.

## 5. Revision-quality watch

**Question:** Which selected series show material historical revisions in the
source's current summary, and where is quality coverage unknown?

- Select exactly one `MacroSeries` in a slicer.
- Show selected-series summary metrics: observation count, average/maximum
  revision count, and supplied average/maximum absolute revision percentage.
- Add a scatterplot for available summaries: average revision count versus
  average absolute revision percentage, details by series ID. Observation count
  can size markers; use tooltips for metrics/capture/source.
- Display one of three states: **not selected for quality**, **selected but
  summary unknown**, or **available**. Never turn the first two into zero risk.

```dax
Quality Selection State =
    IF(NOT HASONEVALUE(MacroSeries[node_id]), "Select one series",
       IF(COUNTROWS(revision_quality) = 0, "Not selected for quality",
          SELECTEDVALUE(revision_quality[details_quality_status], "Unknown")))
Average Revision Count =
    IF(HASONEVALUE(MacroSeries[node_id]),
       SELECTEDVALUE(revision_quality[details_avg_revision_count]))
```

No quality publication in the pack means this page is unavailable, rather than
all catalog series being not selected. A header-only selected publication has
its own publication metadata even when it has no rows.

Keep revision percentage values in their supplied units. Do not apply Power BI
percentage formatting (which multiplies fractions by 100) until the source's
scale is confirmed. Do not invent a risk score, common threshold, historical
vintage claim or causal sensitivity from these summaries. Graph and quality
captures are independent; put their two publication timestamps side by side.

**Check:** the retained local baseline selected 3 summaries; the rest of the
catalog was not selected. Confirm each summary's source/input/build lineage,
and test an unknown summary with null numerical fields. Do not use a missing
quality row to filter a series out of the catalog inventory.

## 6. Why this result? / publication status

**Question:** Where did this number or connection come from, and how current is
it?

Use a provenance table with subject kind/ID, source record, input identity,
method version, cutoff and build identity. Add a publication table listing each
snapshot independently, including capture dates where supplied. A drill-through
selection must identify both subject kind and ID; the user should be able to
copy them to locate the corresponding row. In the synthetic pack, database
build/publication time is intentionally blank.

For actual core-report drill-through, add these calculated columns:

```dax
// In relationships
EvidenceKey = relationships[publication_name] & "|relationship|" & relationships[assertion_id]
// In contexts
EvidenceKey = contexts[publication_name] & "|macro_context|" & contexts[curated_macro_context_version_id]
// In correlations
EvidenceKey = correlations[publication_name] & "|rolling_correlation|" & correlations[rolling_correlation_estimate_version_id]
// In provenance
EvidenceKey = provenance[publication_name] & "|" & provenance[provenance_kind] & "|" & provenance[subject_id]
```

Then create a calculated dimension:

```dax
EvidenceSubject =
    DISTINCT(SELECTCOLUMNS(provenance, "EvidenceKey", provenance[EvidenceKey]))
```

Create one-to-many, single-direction relationships from
`EvidenceSubject[EvidenceKey]` to the four tables' `EvidenceKey` columns. Put the
dimension's `EvidenceKey` on the provenance page's drill-through field well and
include that same dimension field in each source detail table. Right-click one
detail row to drill through. The common dimension filters the matching
provenance row without a fact-to-fact or bidirectional relationship. Catalog,
source-context and quality evidence can use the same pattern with their own
publication/kind/subject keys; keep their independent timestamps visible.

**Check:** trace A11, CTX3, and one selected correlation in the synthetic pack.
Published packs use UUID subject IDs; find A11/CTX3 through the corresponding
`source_record` suffix, not by comparing the UUID directly to the literal A11.
A source-backed edge, curated mapping and numerical estimate retain distinct
labels. Reconcile synthetic fixture report facts within the synthetic_fixture publication and
quality facts within the quality publication.

## Acceptance evidence to retain

These recipes and the M function are unexecuted authoring guides. After building
a report, retain its permitted model/report source, synthetic screenshots,
refresh outcome, filter/reset checks, reconciled counts and provenance examples.
For T-015 / AC-009, use the pinned synthetic PostgreSQL `synthetic_fixture` snapshot and
the five-page checklist in [the original Power BI package](../README.md).
Standalone file-pack rendering is useful additional evidence, but it does not
by itself exercise the existing PostgreSQL template/refresh contract. Keep
internal live-data screenshots and source-derived files out of public artifacts.
