# T-005 identity and ontology validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials or connection coordinates are retained here.

## Migration result

- Applied `sql/migrations/001_identity_ontology.sql` with SHA-256 `fb8961bf5c98cc02b05e1fc2559303941ad5591b0224ac1896d3b621d2c7ff5c`.
- A second migration run skipped the recorded checksum, demonstrating migration idempotency.
- Created dedicated `atlas` and `atlas_report` schemas without modifying upstream tables.
- Created three NOLOGIN roles: `marketatlas_source_reader`, `marketatlas_writer`, and `marketatlas_report_reader`.
- Seeded 12 node types, 9 edge types, and 15 allowed endpoint rules.

## Role-boundary result

`market-atlas database validate-roles` passed all checks:

- Source reader can read the two approved source interfaces, cannot write upstream, and cannot create in `atlas`.
- Writer can write `atlas` and cannot access upstream source objects.
- Report reader can read graph tables, cannot write them, and cannot create serving objects.
- The adapter's read-only session and negative write probe also passed.

## Fixture graph result

`market-atlas graph validate-fixture` loaded the fixture twice and returned `status=valid`:

| Check | Result |
| --- | --- |
| Stable deterministic identities on reload | Passed |
| Fixture nodes | 15 |
| Identifier intervals | 4 |
| Reference/curated assertions | 14 |
| `OLDX` and `NEWX` resolve to one listing | Passed |
| Invalid endpoint combination rejected | Passed |
| Overlapping accepted source identifier rejected | Passed |

The deliberate invalid records ran inside a rolled-back validation transaction and were not retained. The identifier guard uses a transaction-scoped advisory lock plus half-open PostgreSQL date ranges to prevent concurrent accepted overlaps for the same source identifier.

## Remaining acceptance scope

AC-003 passes for the fixture identity cases. AC-004, AC-013, and AC-015 remain partial because bounded temporal paths, release-wide artifact review, observation validation, analytics, and publication checks belong to later tasks.
