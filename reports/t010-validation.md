# T-010 build and publication validation

Date: 2026-10-24. Environment: authorized local PostgreSQL 16.15 instance. No credentials, connection coordinates, or restricted source payloads are retained here.

## Migration result

- Applied `sql/migrations/006_build_publication.sql` with SHA-256 `87add4dc4f8bf19ae2efc93536e8c2e46b18c55719443cad190dd9dad000174a`.
- The local migration ledger now contains six migrations; existing migrations are skipped unchanged on repeat.
- The migration adds build runs, serving snapshots, a singleton publication pointer, snapshot-pinned correlation facts, and a reader view that resolves through exactly that pointer.

## Fixture publication result

`market-atlas build validate-fixture` returned `status=valid`:

| Check | Result |
| --- | --- |
| Same fixture/input/configuration reuses one snapshot without duplicate output | Passed |
| Reader view resolves exactly one published snapshot | Passed |
| Published snapshot contains its expected 32 correlation rows | Passed |
| Injected failed build has zero snapshot rows and does not move publication | Passed |

Each build run records the input manifest, knowledge cutoff, canonical configuration and hash, code revision (including dirty state when applicable), Python version, output hash, and validation summary. A successful build first writes and validates an isolated snapshot, then updates the publication pointer in the same database transaction. Prior published snapshots are retained as `superseded`; failed snapshots remain `failed` with their reason and are never selected by the reader view.

This validates the synthetic fixture serving path only. It does not implement Power BI refresh orchestration, retention cleanup policy, or production upstream scheduling.
