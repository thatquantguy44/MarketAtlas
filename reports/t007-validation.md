# T-007 observation-version validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials, connection coordinates, or source payloads are retained here.

## Migration result

- Applied `sql/migrations/003_observation_versions.sql` with SHA-256 `81bc7bdd06806fc5cfa5d3b2c56e5676218c9fcd7b8a79b08ae92b8225dae43d`.
- The local migration ledger now contains three migrations; the prior identity and temporal migrations were skipped unchanged.
- The migration adds `input_manifest`, `market_calendar_session`, `market_observation_version`, and `macro_observation_version`, plus cutoff-aware market and macro selectors.

## Observation fixture result

`market-atlas graph validate-observation-fixture` returned `status=valid` for every check:

| Check | Result |
| --- | --- |
| Early cutoff selects the initial macro vintage; later cutoff selects the revision | Passed |
| Market observation before its availability timestamp is excluded | Passed |
| Unsupported adjusted-history input is explicitly labeled | Passed |
| Stored input manifest reproduces the fixture SHA-256 | Passed |

The fixture loaded 75 calendar sessions, 222 market observations, and two macro releases. At the 2024-02-10 cutoff the January macro value is vintage `initial` with value `101`; at the 2024-03-10 cutoff it is vintage `revision` with value `101.4`. The unsupported-adjustment check uses a savepoint and rollback, so no validation-only observation remains in `atlas`.

Role-boundary validation and the read-only MacroMedallion adapter verification also passed after the migration. This evidence is limited to synthetic observation inputs; it does not claim upstream source-run lineage, analytical estimates, publication, or Power BI behavior.
