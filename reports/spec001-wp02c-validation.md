# Spec 001 — WP-02C temporal selection and event reconciliation

Validated 2026-11-03 on `feat/securities-finance-wp02c`, based on pushed WP-02B
`7ace21f`. Runtime checkpoint: `feaffab`, following tested temporal/boundary
increments `09decc0`, `43960ff` and `47b8dbc`.
See the [plan](../specs/001/plan.md) and
[implemented API](../specs/001/contracts.md#implemented-wp-02c-selection-api).

## Delivered behavior

`temporal.py` selects supported versions with independent business, source-knowledge
and system-record cutoffs. Exact instants normalize to UTC; date-only evidence
retains an interval in its declared timezone. Half-open state/system ends,
inclusive source availability, DST days and unknown boundaries are explicit.
Overlapping state versions or uncertain competitors cannot establish a winner.
Event corrections require an explicit, unambiguous visible supersession chain.

`selection.py` retains a decision/reasons for every input row, withholds unavailable
selected parents/dependents, binds agreement children to the exact selected version,
and exposes proven/unknown request-order comparisons within quantity groups.
Immutable source provenance and physical manifest identity remain distinct from
the deterministic normalized selection identity. No consequential FIFO or safe
allocation claim is inferred from uncertain order.

`events.py` validates optional manifest boundaries binding a component/stream and
complete inclusion list to an exact retained target version and captured-state
instant. Five fixture declarations use 11:50 UTC; the existing 95 records and
17-table JSON/CSV shapes remain unchanged. Older WP-02B manifests still load, but
missing boundary evidence blocks affected event reconciliation.

At the default noon cutoffs, ten position versions are selected; the old position
and four future events are excluded. Two event effects are already included; only
the new recall enters the action plan. Advancing all cutoffs to 12:30 produces
five actions, including three referenced reversals. Included corrections produce
an old/new replacement instruction rather than adding a full corrected quantity.
Missing/incomplete boundaries, invalid baseline validity, late unincluded effects,
unknown quantities, ambiguous lineage/order, target changes and duplicate reversals
withhold affected actions with inspectable scope/reasons. Replay returns the same
plan without mutating balances or appending effects.

## Validation

| Check | Result |
| --- | --- |
| Focused securities-finance tests | 87 passed: prior 55 plus 32 new (11 temporal, 21 selection/boundary/reconciliation) |
| Full standard-library `python3 -S` suite | 235 discovered; 221 passed, 14 expected optional/database skips |
| Full `.venv-dagster` suite | 235 discovered; 230 passed, five opt-in database skips |
| Changed Python Ruff lint/format | Passed, Python 3.11 target |
| Documentation links and runnable API example | Relative file links resolve; documented WP-02C example passes |
| Standalone `python3 -S` smoke | Gross JSON/CSV and already-net packs load/select; no SciPy, psycopg or Dagster imported |
| Base fixture SHA-256 | Unchanged: `15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da` |

Both full suites force `MARKETATLAS_TEST_DATABASE=0`. Retained ignored evidence is
under `data/generated/securities-finance-fixture/wp02c-validation/`: `core.log`,
`orchestration.log`, `selection-summary.json`. Local runtimes use Python 3.12;
the implementation uses Python 3.11-compatible standard-library APIs.

Tests cover independent clocks, adjacent/colliding versions, exact cutoff/end
boundaries, date-only starts/ends/availability, missing evidence, DST/skipped days,
source-scoped IDs, correction chains/forks/cycles/future knowledge, selected-parent
availability, legacy/incomplete/invalid/duplicate boundaries, included/new/late
effects, replay, partial returns, referenced and duplicate reversals, correction
replacements and target changes, retained unknown FIFO, JSON/CSV/gross/net inputs,
raw provenance and immutable results. A correction is also exercised through
rewritten, rehashed JSON and CSV source files and the strict pack loader.

## Captured local identities

Directories remain ignored under `data/generated/securities-finance-fixture/inputs/`.
New physical IDs include explicit event-boundary declarations; earlier B packs are
retained and still readable.

| Variant | Manifest/directory ID | Selection semantic identity |
| --- | --- | --- |
| Gross JSON | `d7a1b2839bfcf8107e05be139d6bfe04abb4677faa4f157aeb9d184258fa8361` | `a1c4bc749a898d974a3a980a517c1a2b9e243c32ea6cf528a9719cf67836fd43` |
| Gross CSV | `5cf1358e7b2b18cd705833eb76ddc3da165d8c7d580373142d968179aacb4e94` | `a1c4bc749a898d974a3a980a517c1a2b9e243c32ea6cf528a9719cf67836fd43` |
| Already-net JSON | `4128c9d3ec04a5231f14857efe4f5553585cf22286ced7a98c1d352eba346904` | `7114b75715d4f884d74bbaf5dd49f4f3261af1f9e81eeea103e0a03aadeb5061` |

Each has 95 retained decisions/provenance records. Gross JSON/CSV have identical
selection and event plans with separate raw provenance. Net source balances remain
different facts, so their selection identity differs; normalized capacity equality
is a WP-03 claim, not a result here.

## Reproduce and scope

Run the Python example in the API documentation, then:

```sh
PYTHONPATH=src python3 -S -m unittest discover -s tests -p 'test_securities_finance_*.py' -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src python3 -S -m unittest discover -s tests -v
MARKETATLAS_TEST_DATABASE=0 PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests -v
ruff check --select E4,E7,E9,F,I,UP,B --target-version py311 src/market_atlas/securities_finance/{temporal,selection,events,adapters,fixtures}.py tests/test_securities_finance_{temporal,selection}.py
ruff format --check src/market_atlas/securities_finance/{temporal,selection,events,adapters,fixtures}.py tests/test_securities_finance_{temporal,selection}.py
git diff --check
```

WP-02C and SF-WP-02 are complete at selected-fact/event-planning scope. SF-AC-003,
004 and 016 gain partial evidence; no complete feature acceptance row passes.
There is no dependency, database, upstream access, CLI, schedule, solver or report
publication change. The loader continues to reject unsupported ambiguous retained
reference/convention metadata; this API does not repair those histories.

Next is WP-03: consume selected facts, honor `event_plan.blocked_targets`, apply
supported effects once under component contracts, normalize gross/net capacity
without double deduction, and evaluate typed rules/dataset-specific freshness.
Return events alone never establish settled free capacity. Recall impact remains
WP-05; FIFO consequence/proven publication and previous-pack recovery remain later
optimizer/report work. Selected baseline tables must never be mistaken for
reconciled, eligible or allocatable balances.
