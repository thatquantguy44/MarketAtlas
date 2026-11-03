# Spec 001 — WP-02B input fixtures and adapter validation

Validated 2026-11-03 on `feat/securities-finance-wp02b`, based on pushed WP-02A
commit `c2f40f8`. The [implementation plan](../specs/001/plan.md) and
[file API](../specs/001/contracts.md#implemented-wp-02b-file-api) define the scope.

## Delivered slice

Five source/test files implement typed source table shapes, JSON/CSV codecs,
normalized records, reference validation, TOML settings validation, a hashed input
manifest loader and deterministic synthetic fixture generation. No dependencies,
existing CLI, live source access, database objects, public outputs or schedules
change. The settings example's comments now identify the implemented input APIs.

The default fixture has 17 tables and **95 records**, including:

- Three existing share references and two isolated synthetic bond references,
  with whole-share and instrument-specific nominal conventions.
- Gross/net alternatives for the 180k inventory/100k request coverage case,
  request-specific joint-allocation inputs, percentage-balance inputs and bonds.
- A zero balance and an unknown balance, missing permission evidence, quoted
  Unicode/multiline text, date-only evidence, and two retained position versions.
- Two known loans, explicit 15k/5k ownership allocations, a reservation, seven
  lifecycle events and two explicit snapshot-included event references.
- Thirteen supplied signed net-benefit coefficients with declared basis,
  currency, horizon and assumption provenance. No fee calculator runs.

Every table has both physical representations. The loader verifies both hashes,
parses and validates both formats, and compares canonical normalized facts. It
then returns one selected representation per logical dataset, with file hash,
path, format and logical record ordinal in immutable provenance. Verification
does not append a second set of inventory, demand or events.

## Checks and results

| Check | Result |
| --- | --- |
| Focused securities-finance suite | 55 passed: 22 WP-02A plus 33 new WP-02B tests |
| Full `python3 -S` suite | 203 discovered, 189 passed / 14 expected optional/database skips |
| Full `.venv-dagster` suite | 203 discovered, 198 passed / five database skips |
| Changed Python Ruff lint/format checks | Passed, targeting Python 3.11 |
| Standalone standard-library build/load smoke | Three input packs generated and verified; no SciPy, psycopg or Dagster imported |
| Base public fixture hash | Unchanged: `15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da` |

Both full suites force `MARKETATLAS_TEST_DATABASE=0`. Logs and the three-pack
summary remain ignored under
`data/generated/securities-finance-fixture/wp02b-validation/` (`core.log`,
`orchestration.log`, `input-summary.json`). Local runtime checks used Python 3.12;
the code uses Python 3.11-compatible standard-library APIs.

Negative/equivalence cases cover JSON duplicate keys, unknown/missing columns,
CSV header duplication/ragged records, scalar types, resource limits, UTF-8 errors,
quotes/newlines, null versus empty/zero, fractional/invalid quantities through
each format, foreign keys, source namespace, instrument/convention bindings,
snapshot/event scope, shared event-version labels, signed coefficient basis and
horizon, unsupported TOML policies/terms/weights, file and manifest tampering,
logical/physical duplicate authorities, path traversal, escaping symlinks,
missing files, deep immutability and configured workload bounds.

Record order and TOML comments can change physical identities while preserving
normalized input identity. Mixed per-table authority formats still load 95
records once. Changing a bond minimum in TOML changes its loaded convention and
semantic identity. Failed staging leaves existing complete inputs unchanged and
cleans temporary directories; a tampered existing immutable directory is rejected
instead of overwritten as a repair.

## Captured local input identities

Directories are under `data/generated/securities-finance-fixture/inputs/`:

| Variant | Manifest/directory ID | Normalized input identity |
| --- | --- | --- |
| Gross, JSON authority | `eb05fd4224a0b6e389e37562a2466c2101890ae80928910f370325acfe16b4e1` | `3e4d2185c823019c8a27955068aa941ed66a6659a3d8dd2125a634072f40c53f` |
| Gross, CSV authority | `4189a3b7c18e125aae0e9d3567a0b3b6712e3f18a19025173d8bf89164835ca2` | `3e4d2185c823019c8a27955068aa941ed66a6659a3d8dd2125a634072f40c53f` |
| Already-net, JSON authority | `dc1a4b280ecc069794361a4965dcfb6455600a154d555fa986302c84045b3064` | `8f72fd2256664f661a02b95d72d7db3cf1bc0d44706180182de65d3900f21da9` |

Gross versus net has deliberately different source facts/balance definitions;
equal normalized capacity is a later WP-03 calculation, not a claim here.

## Reproduce

Use the runnable file API example in the contracts document to generate/load an
input pack. These are input fixtures, not as-of-selected report outputs.

```sh
PYTHONPATH=src python3 -S -m unittest discover -s tests -p 'test_securities_finance_*.py' -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src python3 -S -m unittest discover -s tests -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests -v
ruff check --select E4,E7,E9,F,I,UP,B --target-version py311 src/market_atlas/securities_finance/records.py src/market_atlas/securities_finance/adapters.py src/market_atlas/securities_finance/fixtures.py tests/test_securities_finance_adapters.py tests/test_securities_finance_fixtures.py
ruff format --check src/market_atlas/securities_finance/records.py src/market_atlas/securities_finance/adapters.py src/market_atlas/securities_finance/fixtures.py tests/test_securities_finance_adapters.py tests/test_securities_finance_fixtures.py
git diff --check
```

## Acceptance boundary

WP-02B is complete at input-fixture/adapter scope. SF-AC-003/004/015/016/017 have
additional structural, provenance and normalized-fact equivalence evidence.
Their complete downstream scenarios remain pending. In particular, no active
version/cutoff selection, event-effect application, balance normalization,
eligibility, allocation optimum or report behavior is established. No full
SF-AC-016 downstream-result claim or parent database permission claim is made.

Next is WP-02C: select supported versions at the three cutoffs and account for
snapshot/event inclusion without applying already-included effects twice.
