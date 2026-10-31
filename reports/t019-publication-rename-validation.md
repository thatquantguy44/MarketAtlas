# T-019 — Explicit synthetic publication name and PostgreSQL access

Validated locally on 2026-10-30. The user requested renaming the synthetic
publication and instructions for accessing all PostgreSQL publications.

## Change and database application

The fixture producer, export allowlist/default selection, CLI, Power BI TMDL
parameter and current operational/specification guides use `synthetic_fixture`.
Migration `012_rename_synthetic_fixture_publication.sql` renames the legacy
`default` entry in `atlas.publication` without updating its snapshot ID or
publication time. A collision raises an exception before replacement. A check
constraint prevents an older producer from silently recreating the legacy name.
Existing build configuration/history and immutable report data are retained.
Previously applied migrations 001–011 were not edited.

The standard migration runner applied only migration 012 to the existing local
database. A before/after comparison verified that all four publication snapshot
IDs and original timestamps were unchanged, with only the synthetic name
renamed. The registry now contains:

- `synthetic_fixture`
- `macro_economic_graph`
- `macro_context`
- `macro_revision_quality`

No source-schema writes, data refreshes or report rebuilds were performed.
No login or new access grant was provisioned. The reader role continued to
resolve the renamed publication. Historical validation reports and generated
packs retain the labels they recorded at creation.

## Verification

```sh
PYTHONPATH=src python3 -S -m unittest discover -s tests
MARKETATLAS_TEST_DATABASE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_p*.py' -v
```

The full credential-free suite ran 78 tests: 75 passed and three opt-in database
tests were skipped. All 15 focused Power BI/export/rename tests passed with
database checks enabled after applying the migration. Those include an export
of all four actual local report publications using the renamed fixture selection.

The new rename integration test always rolls back. It recreates the legacy
pointer inside that transaction, verifies rename and repeat application, checks
snapshot count and pointer/timestamp preservation, verifies reader-role access,
rejects legacy-name recreation, and proves that a name collision leaves both
pointers in place. The export and rename code passed Ruff checks.

## Access handoff

`docs/publication-access.md` explains connecting with local configuration,
browsing **Schemas → atlas_report → Views**, reader login versus the NOLOGIN
role, snapshot pinning, and the view mapping for all four publications.
`sql/queries/publications.sql` is a read-only registry/view-discovery script.
It contains no credentials or private connection coordinates.

Existing saved Power BI templates need their publication parameter changed to
`synthetic_fixture`. Actual Power BI report execution remains T-015 / AC-009;
this rename does not change that partial acceptance status. The dedicated
`[report_database]` profile is still an operator setup step.
