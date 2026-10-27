# Source onboarding decision — revision-quality interface

Status: approved and validated for restricted internal use on 2026-10-26. The
contract permits a bounded read-only extract only; it does not authorize public
redistribution, screenshots, raw extracts, or derived-data publication.

## Refreshed catalog evidence

On 2026-10-26, the read-only source catalog found 102 upstream objects: six
`supported_live`, 85 `discovered_not_onboarded`, and 11 intentionally
unavailable to the source role. The post-promotion catalog fingerprint was
`983c665d16384309fe3c8ef7b3d9dbd15ab8423e0e87ad0ec3886d633929999e`.

## Recommended next contract

`gold.v_series_revision_summary` is the recommended candidate.

| Property | Observed metadata |
| --- | --- |
| Relation | `gold.v_series_revision_summary` view |
| Grain | One current summary row per `series_id` |
| Fields | `observation_count`, average/max revision count, average/max absolute revision percentage |
| Column fingerprint | `a1d56f56f798e39225e47026f12e87691f4212caea5d837732d524074f258a51` |
| View fingerprint | `ea26b587ad4c8d0ccd4ef153478c7108` |
| Intended use | Revision-risk/quality context beside an already-approved series identity |
| Temporal limit | Current aggregate quality only; not point-in-time revision history or an as-of reconstruction |

The bounded adapter must accept only configured series IDs that also exist in
`gold.dim_series`, request them in explicit batches, and preserve an empty or
missing summary as unknown rather than a zero-revision claim. It must not scan
the full summary view or `gold.fred_revision_stats`, whose metadata estimate is
20,501,276 rows.

## Rejected for this slice

- `gold.v_point_in_time` has the same column and view fingerprints as already
  supported `gold.fred_point_in_time`; it adds no independent contract value.
- `gold.fred_revision_stats` contains valuable history but needs a separately
  designed bounded temporal workload before it can be considered.
- `gold.fomc_probability` is small but is a model output; it needs a model
  owner, methodology contract, and distinct analytical semantics.
- ECB eligible-security interfaces are large, restricted securities-finance
  domain candidates and belong behind the separate restricted-extension
  boundary, not this public macro slice.

## Approval record

Josh, the project and source owner, accepted source/data, database,
report, quant/methodology, refresh/recovery, and incident accountability for
this manual local pilot. The interface is classified `restricted_internal_only`
and its redistribution status is `restricted`: no external sharing is
authorized. The adapter has a 1–1,000 ID batch ceiling, treats a missing
summary as unknown, and labels its output current-only quality context. The
live validation returned three configured, approved summaries with no missing
IDs; its generated payload is ignored.
