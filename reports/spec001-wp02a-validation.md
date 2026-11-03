# Spec 001 — WP-02A contract foundation validation

Validated 2026-11-03 on `feat/securities-finance-wp02a`, based on design commit
`afce9b6`. Scope is the first implementation slice in
[the plan](../specs/001/plan.md#ordered-work-packages-and-verification).

## Implemented boundary

Five source/test files add an isolated standard-library API:

- Frozen typed record keys, three-clock envelopes and timestamp evidence; schema,
  key, interval and duplicate-version validation with inspectable error codes.
- Exact scaled quantities/conventions, retaining unknown versus zero and rejecting
  fractional equities and incompatible units/currencies/precision.
- Minimum-origin bond proposal checks, distinct from validation of balances and
  partial-return quantities. No rounding or allocation generation.
- An immutable reference catalog reusing core share IDs/labels and declaring two
  known synthetic bonds using the existing ID generator. Wrong node types,
  duplicate IDs/keys, absent mappings and cross-instrument bindings fail.

The API validates normalized in-memory fields. It does not decode JSON/CSV/TOML,
validate every business payload table, select active versions at cutoffs, evaluate
eligibility, normalize inventory balances, apply events, solve allocations or
publish reports. Those remain WP-02B/C and later packages. Catalog references are
not assertions of existing database rows. No existing CLI, publication, database
role, migration, dependency or source connection changed.

## Verification

| Check | Result |
| --- | --- |
| Focused securities-finance tests with `python3 -S` | 22 passed, none skipped |
| Full standard-library suite with `python3 -S` | 170 discovered; 156 passed, 14 expected optional/database skips |
| Full `.venv-dagster` suite | 170 discovered; 165 passed, five opt-in database skips |
| Changed Python Ruff lint, including imports/upgrade/bugbear checks targeting Python 3.11 | Passed |
| Changed Python Ruff format check | Five files passed |
| Standalone `python3 -S` API smoke | 2,500 nominal under minimum 1,500/step 1,000 validates; 2,000 rejects as off-increment |
| Optional runtime imports in smoke process | No `psycopg`, `scipy` or `dagster` imported |
| Base fixture output | SHA-256 unchanged; existing validator passes |

Both full suites explicitly set `MARKETATLAS_TEST_DATABASE=0`. Ignored local logs
are retained in `data/generated/securities-finance-fixture/wp02a-validation/` as
`core.log` and `orchestration.log`. No database tests or solver benchmarks are
claimed. Code uses Python 3.11-compatible syntax/APIs; local runtime checks used
Python 3.12.

Focused cases cover exact normalization under a low ambient Decimal precision;
unknown/zero distinction; malformed, negative, nonfinite, exponent and numeric
literal inputs; fractional/over-precision values; mismatched currency/units;
minimum/step origins and residual quantities; unknown schema/fields; missing
normalized fields; source/version keys; duplicate/conflicting same-version
envelopes; precise/date-only evidence; naïve/invalid/over-precision times and
invalid offsets; invalid intervals; immutable catalog containers and documented
convention values. Date evidence without a timezone remains date evidence.
Cutoff/FIFO interpretation remains WP-02C.

The pinned pre-change/base fixture digest is:

```text
15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da
```

The catalog test pins share UUIDs and checks source labels/types, rather than
only comparing repeated generator calls. `SF-BOND-A` and `SF-BOND-B` remain absent
from `fixtures.build_fixture()` while present in the isolated catalog.

## Reproduce

```sh
PYTHONPATH=src python3 -S -m unittest discover -s tests -p 'test_securities_finance_*.py' -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src python3 -S -m unittest discover -s tests -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests -v
ruff check --select E4,E7,E9,F,I,UP,B --target-version py311 src/market_atlas/securities_finance tests/test_securities_finance_contracts.py tests/test_securities_finance_catalog.py
ruff format --check src/market_atlas/securities_finance tests/test_securities_finance_contracts.py tests/test_securities_finance_catalog.py
git diff --check
```

## Acceptance accounting

WP-02A is complete. SF-AC-003/004/015/017 have retained **partial** evidence for
their structural/type/quantity/identity subcases. Complete temporal, eligibility,
optimizer and reporting scenarios remain pending. SF-AC-016 adapter equivalence
is not claimed. No feature acceptance row is marked fully passed; the parent
AC-012 remains design-level evidence.

Next is WP-02B: deterministic business fixtures and JSON/CSV adapters into these
contracts, preserving provenance and one authoritative representation.
