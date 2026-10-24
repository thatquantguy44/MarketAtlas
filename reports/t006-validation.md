# T-006 temporal reference assertion validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials or connection coordinates are retained here.

## Migration result

- Applied `sql/migrations/002_temporal_assertions.sql` with SHA-256 `fd23f10925848b3be8d93b24424048d5f4cee6ccaa3666df9024a6df5c34a0f9`.
- A repeat migration run skipped both recorded migrations.
- The migration adds a stable relationship business key, correction/retraction versioning, `relationships_as_of`, and `bounded_paths`.

## Temporal fixture result

`market-atlas graph validate-temporal-fixture` returned `status=valid` for every check:

| Check | Result |
| --- | --- |
| Late source fact differs by system cutoff | Passed |
| Correction preserves the prior accepted version | Passed |
| Bounded listing-to-sector path exists before retraction | Passed |
| Same path is hidden after retraction | Passed |
| Unknown availability is returned as `unsupported_history` | Passed |

`A14` is source-available on 2024-04-15 but has MarketAtlas record time 2024-05-01. With a 2024-04-20 source-knowledge cutoff and current MarketAtlas context it is visible; with a matching 2024-04-20 system cutoff it is absent. `A15` supersedes and retracts `A6` on 2024-04-03, closing the prior record-time interval while preserving the earlier accepted result for replay.

The unsupported-history check inserts a deliberate unknown-availability assertion inside a savepoint, observes its label, then rolls it back. No validation-only record remains in `atlas`.
