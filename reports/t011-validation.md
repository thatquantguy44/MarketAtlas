# T-011 reporting and provenance validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials, connection coordinates, or restricted source payloads are retained here.

## Migration result

- Applied `sql/migrations/007_reporting_provenance.sql` with SHA-256 `79fa472a683b442dfc998be011d276d718452ca4c2a3a97f5aa7dc7193dc9a76`.
- The local migration ledger now contains seven migrations; prior migrations are skipped unchanged on repeat.
- The migration adds snapshot-pinned node, relationship, macro-context, bounded-path, and provenance reporting tables plus current views that join through the one publication pointer.

## Fixture reporting result

`market-atlas report validate-fixture` returned `status=valid`:

| Output | Snapshot count |
| --- | ---: |
| Nodes | 15 |
| Relationship facts | 14 |
| Macro-context facts | 3 |
| Bounded paths (depth ≤ 4) | 24 |
| Correlation facts | 32 |
| Provenance records | 49 |

The validator confirms every current reporting view resolves to the same snapshot. Joining each correlation fact to its low/high node dimensions preserves 32 distinct correlation estimate versions and 32 rows, demonstrating no pair multiplication under the fixture’s multi-membership relationships.

Drill-through is demonstrated for `synthetic-fixture:A11` (sourced series-to-concept relationship), `synthetic-fixture:CTX3` (curated sector context with support assertion), and a rolling-correlation estimate (input manifest, method version, configuration hash, input-selection hash, cutoff, and build). See [reporting.md](../docs/reporting.md) for declared view grains and join keys.

This is PostgreSQL fixture evidence. It does not substitute for a Power BI semantic-model/report test; AC-009 remains partial until that environment is exercised.
