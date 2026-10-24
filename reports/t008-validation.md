# T-008 curated macro-context validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials, connection coordinates, or restricted source payloads are retained here.

## Migration result

- Applied `sql/migrations/004_curated_macro_context.sql` with SHA-256 `892218780ecacd475daf96e66fc513cbee8950738a307b83533303fef1c212b2`.
- The local migration ledger now contains four migrations; the prior migrations were skipped unchanged.
- The migration adds versioned curated macro-context mappings, a typed source/target validation trigger, and the `curated_macro_context_as_of` query function.

## Curated-context fixture result

`market-atlas graph validate-curated-context-fixture` returned `status=valid` for every check:

| Check | Result |
| --- | --- |
| Source-backed country and concept mappings plus a curated sector mapping are present | Passed |
| Every returned mapping has the mandatory context-only/non-causal semantic label | Passed |
| Owner, source reference, taxonomy provider, and taxonomy version are present | Passed |
| A country mapping with an instrument target is rejected | Passed |

The synthetic fixture has three inspectable mappings for `M-GROWTH`: country coverage and economic concept are source-backed by the existing reference assertions; sector relevance is an explicitly curated mapping. Each retains effective/availability/record time, a supporting assertion, the fixture input manifest, and a mapping owner. No mapping is presented as measured sensitivity or causality.

The invalid-target probe is executed in a savepoint and rolled back, so no validation-only context mapping remains in `atlas`. Role-boundary validation and the read-only MacroMedallion adapter verification also passed after the migration. This evidence is fixture-only; it does not claim an approved real-world market relevance mapping or a statistical estimate.
