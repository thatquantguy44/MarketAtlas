# T-018 — Power BI data jobs and report guides

Validated locally on 2026-10-30. This evidence covers data-pack generation and
report-authoring source. It does not establish Power BI rendering/refresh,
GitHub Actions execution, scheduled operation or an AC-009 pass.

## Delivered behavior

`powerbi export` generates a credential-free synthetic pack or reads selected
existing PostgreSQL report publications. It emits immutable UTF-8 CSV tables and
a manifest containing typed schemas, primary keys, file SHA-256s, counts, source
mode and redistribution classification, plus Python version, Git base revision
and a fingerprint of the actual Python source tree. Pack identity hashes the manifest body;
identical content reuses its folder. No mutable latest-pointer is used by the
Power Query loader. A failed job leaves prior complete packs intact.

Published exports use a dedicated report configuration, the report-reader role,
a read-only repeatable-read transaction, one resolution of the selected
publication pointers, and allowlisted snapshot-table queries bound to those
snapshot IDs. Requested missing publications and row-limit overflows fail rather
than produce partial packs. Extraction/migrations/builds/publication writes are
outside this job. Internal live output remains ignored and restricted.

The report package includes `powerbi/queries/fnLoadPack.pq`, a data-job/ingestion
guide and six report recipes with model keys, DAX, layouts and checks. GitHub
workflow source generates synthetic packs only, on manual dispatch and relevant
pull requests after it is pushed.

## Exercised checks

```sh
PYTHONPATH=src python3 -S -m unittest discover -s tests -v
PYTHONPATH=src python3 -S -m market_atlas powerbi export --output data/generated/powerbi
```

The complete credential-free suite ran 76 tests: 74 passed and two opt-in
database tests were skipped. The new export tests cover:

- CSV round-trip and exact table grains; supported numerical estimates and
  undefined estimates preserved as null, never zero.
- Repeat-run identity/reuse, multiline/quoted strings and all-null numerical
  column types.
- Rejected checksums, duplicate keys, orphan endpoints, missing core provenance,
  mixed publication IDs and invalid unknown-quality metrics.
- Rejected invalid exports leave the previous valid folder unchanged, with
  staging directories cleaned up.
- CLI execution without configuration; dedicated report-role validation and
  safe configuration diagnostics.
- One pointer resolution and fixed-snapshot SQL, row-limit failure, and a
  read-only repeatable-read connection/role contract.

An initial focused run of the eight then-existing export tests also passed
against the local database with the opt-in report-only test enabled. The final
schema/export implementation was then exercised by generating and validating
the durable four-publication pack below. That smoke check used the existing
authorized local connection and assumed the report-reader role; it did not
provision or claim to validate a new dedicated Power BI login.

## Generated artifacts

Synthetic output:

`data/generated/powerbi/133a1194411c820e386f3a98810c199b2f79a0a009aee98215a6ce2aac080cee/`

| Table | Validated rows |
| --- | ---: |
| publications | 1 |
| nodes | 15 |
| relationships | 14 |
| contexts | 3 |
| correlations | 32 |
| provenance | 49 |
| pairs | 2 |
| dates | 16 |

Correlations comprise 16 supported estimates and 16 zero-variance/undefined
estimates calculated from the canonical synthetic input. The current
relationship selection retains A15's retraction and excludes superseded A6.
The input SHA-256 remains
`15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da`.
This file pack does not invent a database build or publication timestamp.
The final Ruff lint/format checks passed for the changed Python files.

Restricted internal output:

`data/generated/powerbi-internal/05bffee5f62337a07dd0184cf6fb61accb7055549b69d85ac55a4dfd38d965ef/`

| Additional surface | Validated rows |
| --- | ---: |
| publications (including default) | 4 |
| macro_nodes | 301 (290 series, 11 concepts in the retained catalog baseline) |
| macro_edges | 290 |
| macro_graph_provenance | 290 |
| source_context | 48 |
| source_context_provenance | 48 |
| revision_quality | 3 |
| quality_provenance | 3 |

The default publication also exports the same core report counts as above.
All 32 standalone correlation estimates reconcile with this published fixture
by canonical pair and endpoint, status and paired-return count; numerical
values agree within absolute tolerance `1e-10`.
Validation passed for all 16 tables. These are observations of the existing local
publications, not newly refreshed source captures. The exporter did not query
source schemas or change serving pointers. No restricted row payload,
connection coordinate, credential or screenshot is included in this report.

## Remaining work

An additional actual-data-only export on 2026-10-30 omitted `default` and passed
validation for eight tables across the three live macro publications. It retains
301 catalog nodes, 290 edges, 48 source-context rows and 3 quality summaries,
with their publication/provenance tables. The ignored local starter archive is
`data/generated/powerbi-real/marketatlas-real-data-1eb65542df03.zip`; it includes
the immutable pack, M loader and report guide, with no synthetic default tables
or credentials. ZIP integrity passed. This remains a data/authoring starter,
not an executed Power BI report.

The Power Query function and DAX recipes have not been run in Power BI. The
workflow has not been committed/pushed or executed on GitHub. A scheduler,
service gateway and service refresh are not configured. Dedicated report-login
provisioning remains a database-owner task. T-015 remains the next acceptance
slice: exercise the PostgreSQL synthetic template/report against one pinned
snapshot and retain actual refresh, visual/filter/distinct-count and provenance
evidence. AC-009 stays partial.
