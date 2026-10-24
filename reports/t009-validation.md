# T-009 rolling-correlation validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials, connection coordinates, or restricted source payloads are retained here.

## Migration result

- Applied `sql/migrations/005_rolling_correlation_estimates.sql` with SHA-256 `2601abfa4717f2f331c2c1fdfc9b63b416b74ff0b29ffc39a5b12fa7da3a5439`.
- The local migration ledger now contains five migrations; the earlier migrations were skipped unchanged on repeat.
- The migration adds canonical instrument-pair rolling estimates with fixed window/minimum-sample controls, input and configuration hashes, cutoff metadata, and explicit supported/undefined statuses.

## Fixture result

`market-atlas analytics validate-fixture` returned `status=valid` for every check:

| Check | Result |
| --- | --- |
| Repeated calculation preserves the same estimates | Passed |
| Final `I-A`/`I-B` estimate matches an independent calculation within `1e-12` | Passed |
| Every estimate uses exactly 60 scheduled sessions and at most 59 paired returns | Passed |
| Missing prices do not expand a window | Passed |
| Historical cutoff cannot use later inputs | Passed |
| Constant `I-C` pair reports explicit zero variance | Passed |
| Unsupported-history input reports explicit unsupported history | Passed |

Current-context calculation produces 32 estimates: 16 supported `I-A`/`I-B` correlations and 16 `I-A`/`I-C` zero-variance outcomes. The last supported `I-A`/`I-B` result is `0.994545932823383` on 2024-04-15 with 55 paired returns. At the 2024-04-05T12:00:00Z knowledge cutoff, only 20 estimates exist (10 supported and 10 zero variance), and each retained input availability timestamp is at or before the cutoff.

The calculation stores the simple adjusted-close return definition, common calendar, adjustment basis, method version, configuration hash, input-selection hash, input manifest, window boundary, paired count, cutoff, and system record time. It is fixture-only and is not an atomic serving publication or an upstream production estimate.
