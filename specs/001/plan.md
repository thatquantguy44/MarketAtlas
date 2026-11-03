# 001 — Securities-finance implementation plan

Status: **proposed; no implementation started**. Created 2026-11-03.
Specification: [spec.md](spec.md). Parent boundary:
[extension contract](../../docs/securities-finance-extension.md).

This plan implements the stable modules in the specification. Work packages below
are the feature's ordered implementation backlog; all are pending. They do not
replace the main product task register or authorize a live deployment.

## Architecture and build order

Use PostgreSQL's existing graph foundation where appropriate, without introducing
a graph database. First prove the operational questions with deterministic files
and pure Python functions. Keep identity, balance normalization, eligibility,
matching proposals and dependency paths as distinct calculations.

```text
Synthetic source contracts + existing synthetic instrument identities
  → validated, cutoff-selected facts
  → normalized capacity + versioned rule results
  → bounded matching proposals / explicit recall dependencies
  → validated immutable evidence pack
  → separate synthetic report workspace
```

The graph contains sourced/fixture relationships such as position→account,
position→instrument, request→borrower/instrument, agreement→parties,
loan→agreement/instrument, allocation→loan/owner-position and recall→allocation.
Candidate and proposal relationships have their own derived types and evaluation
IDs; they are not asserted booked loans. No path grants an approval or implies a
chain of ownership/re-lending without explicit allocation records.

## Proposed file/module layout

These paths are proposals, not existing commands or implemented interfaces:

| Path | Responsibility |
| --- | --- |
| `src/market_atlas/securities_finance/contracts.py` | Typed/versioned input contracts, identity/unit/time checks |
| `.../fixtures.py` | Deterministic invented cases referencing synthetic instrument node IDs |
| `.../selection.py` | Effective/source-knowledge/system-record cutoff selection |
| `.../eligibility.py` | Approved typed rules, aggregation and reason/input evidence |
| `.../matching.py` | Capacity ledger, shared headroom, stable ordering and proposals |
| `.../dependencies.py` | Bounded attributable loan/recall paths |
| `.../pack.py` | Immutable manifests, validation and atomic artifact delivery |
| `configs/securities_finance_fixture.toml` | Synthetic scope, rule/policy versions and workload bounds; no credentials |
| `contracts/securities_finance_fixture.*` | File-contract declarations; not an approved live-source registry entry |
| `tests/test_securities_finance_*.py` | Independent numerical, temporal, graph and failure checks |
| `powerbi/securities-finance/` | Proposed report-source/guidance namespace; native Power BI execution is optional future scope |
| `data/generated/securities-finance-fixture/` | Ignored local generated inputs, packs and browser workspace |

The `.../` rows abbreviate `src/market_atlas/securities_finance/`. Decide final
file-contract encoding in the first work package using current repository tools;
do not introduce a dependency just to choose an interchange format.

## Input grains and identity contracts

Every row has a stable source identity, input manifest and temporal/provenance
fields where applicable. Version IDs are separate from business IDs.

| Object | Grain and essential facts |
| --- | --- |
| `legal_entity` / `account` | Stable party/account identity; explicit beneficial owner, lender, borrower or custodian role; no ticker-based party resolution |
| `inventory_position` | One authoritative account/instrument/location/optional-lot position version; quantity unit/precision, balance basis and settlement state |
| `reservation` / `encumbrance` | One identified component/event against a position, with quantity, status and timing; overlapping components must be reconciled, not simply added |
| `borrow_request` | One request/version with borrower, canonical instrument, required location/date and authoritative open quantity or a reconciled original/filled/cancelled bridge |
| `agreement` / `rule` | Agreement/rule version, participating parties, scope, required input fields, priority and typed expression reference |
| `loan` | One known loan/version with agreement, instrument, unit, outstanding quantity and lifecycle state; not interpreted as a request |
| `loan_allocation` | Explicit quantity attribution from a known loan to an owner/account/position; distinguish it from a proposed allocation |
| `recall` / `return_event` | Identified lifecycle event with quantity, referenced loan/allocation, effective/known/recorded times and reversal/status semantics |
| Later `collateral_asset` / `collateral_allocation` | Assets/allocations, valuation timestamp/currency/basis, agreement/rules and haircut/margin convention; absent inputs stay unknown |

Use the existing synthetic instrument identity generation/reference contract.
Validate canonical node type before accepting an instrument link. Do not create
new public entities to repair missing identifiers or import private records into
`atlas`/`atlas_report`. Duplicate representations of the same position require an
explicit authoritative-source mapping; different accounts holding the same ISIN
are not duplicate positions merely because the security matches.

## Time, quantity and decision design

1. Freeze input hashes and all three cutoffs in the run manifest. Select uniquely
   effective versions whose supported source availability is within the knowledge
   cutoff and whose record interval is within any requested system cutoff.
   Preserve date-only precision and distinguish captured-current facts from
   replayable history. An unknown timestamp is not replaced with capture time.
2. Normalize one inventory baseline per position. For an already-net available
   balance, validate its declared included deductions. For a gross baseline,
   subtract only disjoint, reconciled components. Do not subtract outstanding
   loans again if the upstream definition already excludes them.
3. Use exact quantities at the declared scale, initially whole shares. Reject
   negatives, contradictory missing/value states and incompatible units. Prices,
   market values and currencies are not invented to calculate exposure.
4. Evaluate only a small typed rule vocabulary: required facts, party/account
   permission, instrument/location compatibility, settlement/readiness and
   configured sample constraints. Store expression/version, all input references,
   per-rule outcome, reason codes, evaluation time and freshness status. Do not
   execute arbitrary Python/SQL from data or parse legal prose as an approval.
5. Clear capacity only for all-pass required checks. A known failure dominates
   an unknown aggregate result but retains the missing-fact outcomes. Assign each
   quantity to one primary ledger bucket; additional reason counts are explicitly
   non-additive. Record unknown/not-evaluated capacity independently.
6. Match requests in a documented stable order, then positions in a documented
   stable order. Cap each proposal by remaining demand, position capacity and any
   shared configured quantity headroom. Update the build-local ledger after each
   proposal. No position's capacity or headroom may be reused within that build.
7. Trace recalls only through explicit allocations and supported events. Apply
   partial returns/reversals once using stable event IDs and time selection.
   Where attribution is missing, return unknown impact rather than following all
   loans of the same security as though they share ownership.

The proposal ledger simulates one snapshot; independent builds do not reserve
real capacity against each other. Production concurrency/execution would need
separate transaction/reservation semantics and is outside this plan's first slice.

## Output and reporting contracts

Use a distinct, explicitly synthetic pack and report identity. Proposed outputs:

| Output | Grain / reconciliation |
| --- | --- |
| `request_coverage` | Request/build: open demand, candidate capacity, proposed coverage, shortfall and unknown capacity; candidate capacity is non-additive across requests |
| `capacity_ledger` | Position/request/check-stage slice: quantities and mutually exclusive primary states; no duplicate debits |
| `rule_evaluations` | Evaluated subject/rule-version/input snapshot: outcome, all reasons, input references and freshness |
| `allocation_proposals` | Proposal/request/position/build: derived quantity and policy identity, clearly not a booked loan |
| `recall_impacts` | Recall/known allocation/build: attributable outstanding quantity or explicit unknown, with path/input references |
| `explanation_steps` | Explanation/ordered step: controlled endpoints, source/rule IDs and dates, bounded depth/row count |
| `manifest` / schema | Input/configuration/method/code identities, three cutoffs, synthetic classification, file hashes, keys, counts and exclusions |

Report **borrow coverage**, **allocation blockers** and a **dependency explorer**.
Use tables for actionable records and graph paths for explanations, not a dense
network as the sole evidence. Keep quantities, states and reasons inspectable;
filters and exports retain the same population. Define any percentage denominator
and preserve null/unknown separately from zero. No estimated revenue, net credit
exposure, collateral eligibility or market-wide scarcity without its own data
and method contract.

Stage and validate a candidate pack before publication. Reuse exact retained
inputs without duplicate business records; retain the previous complete artifact
on failure. Report delivery must use a new synthetic workspace/identity rather
than silently extending the existing macro report or public fixture publication.

## Ordered work packages and verification

Each work package is pending. Split implementation further if a slice would need
more than about five source/test files. Require actual retained evidence before
checking any acceptance row.

| Work | Deliverable / acceptance | Depends on | Verification |
| --- | --- | --- | --- |
| SF-WP-01 | Confirm file contracts, whole-share scope, balance definitions, cutoffs and sample ordering; record reviewed decisions | This draft | Resolve first-slice decisions below; trace every input field and requirement |
| SF-WP-02 | Implement deterministic fixtures, canonical links and temporal selection | WP-01 | Offline generation/replay; wrong-type/duplicate/unit/time rejection; SF-AC-003/004 |
| SF-WP-03 | Add capacity normalization and typed rule evaluation with explanation rows | WP-02 | Independent gross/net and four-state cases; SF-AC-001/003/005 |
| SF-WP-04 | Add build-local competing-request matching proposals and reconciled ledgers | WP-03 | 180k/90k/10k fixture, no double deductions/allocations, stable tie-breaking; SF-AC-001/002 |
| SF-WP-05 | Add explicit loan-allocation and recall investigation | WP-02 | 15k+5k attribution, unrelated same-security loan exclusion, returns/replay; SF-AC-004/006 |
| SF-WP-06 | Package and validate immutable outputs; integrate the three synthetic report views | WP-04/05 | Keys/hashes, injected failure, source/filter/reset, normal/narrow and bounded-workload measurements; SF-AC-007/008/009/012 |
| SF-WP-07 | Optional restricted persistence/adapters and negative permission tests | WP-06 plus separate access/deployment authorization | Source contracts, roles, denied public-reader/API queries, export review; SF-AC-010 |
| SF-WP-08 | Later collateral enrichment and independently verified calculations | Contracts/evaluation plus separately reviewed inputs/scope | Agreement/valuation/rule/missing-input evidence; SF-AC-011 |

**Checkpoint after WP-02:** input identity/time contracts and synthetic fixtures
are trustworthy before quantities are cleared. **After WP-04:** balances and
proposals reconcile before presenting operational coverage. **After WP-06:** the
file-first demonstration may pass its own acceptance rows. It must not claim
database isolation was tested or the parent extension's full acceptance completed.
WP-07 supplies permission evidence; any claim to the parent's collateral scenario
also requires the relevant WP-08 evidence.

## Commands and test strategy

Existing regression command, executable today from the repository root:

```sh
PYTHONPATH=src .venv-dagster/bin/python -m unittest discover -s tests -v
git diff --check
```

Proposed CLI shape below is **not implemented and is not runnable yet**. Add it
with the work packages, without changing existing command behavior:

```sh
PYTHONPATH=src python -m market_atlas securities-finance fixture --output data/generated/securities-finance-fixture/inputs
PYTHONPATH=src python -m market_atlas securities-finance build --input data/generated/securities-finance-fixture/inputs --as-of 2026-11-03T12:00:00Z --knowledge-cutoff 2026-11-03T12:00:00Z --system-cutoff 2026-11-03T12:00:00Z --output data/generated/securities-finance-fixture/packs
PYTHONPATH=src python -m market_atlas securities-finance validate --input "PACK_DIRECTORY"
```

Use the repository's unittest conventions and independent hand-calculated fixture
ledgers. Cover duplicate/corrected inputs, partial reservations/returns, stale or
unknown facts, same-security unrelated positions, competing requests, unit
mismatch, deterministic order, tampering and failed publication. Focused test
patterns must discover a nonzero suite before being cited as evidence. Run the
full existing suite and changed-file lint; optional database checks belong only
in an authorized isolated environment. No tests or benchmarks are claimed run by
this planning document.

## Isolation, rollout and unresolved decisions

- Preserve existing source roles, `atlas`/`atlas_report` grains, publication
  pointers, macro schedules and public-reader permissions. Synthetic field names
  are not permission to reuse restricted production objects.
- For WP-07, choose a separate database or separately authorized restricted
  schema with its own migration, writer, reader and access tests. Any overlap
  with MarketAtlas's general writer boundary needs an explicit scoped revision;
  do not infer it from the schema name in the older design.
- Live access needs named data, methodology/legal, security, database, report and
  support owners, approved interfaces/rights, freshness expectations and retention.
  A sanitized cross-boundary publication needs an approved audience, aggregate
  grain and minimum-cell policy; it is not automatic.
- Initial rollout is an offline synthetic walkthrough. Retain original fixture
  and report outputs for comparison, then inject a failed build and prove recovery.
  Roll back by selecting the previous synthetic artifact; no source repair or
  deletion is involved.

Before WP-01 closes, review the proposed scope, authoritative balance definitions,
request priorities, tie-breakers, rule vocabulary and freshness treatment. Before
WP-07, resolve real identifiers, available temporal history, actual agreements,
roles/deployment and source ownership. Before WP-08, define margin versus haircut,
valuation/FX timestamps, concentration/netting semantics and independent examples.

The next implementation candidate is **WP-01 → WP-02**, not a live adapter,
migration or production report. This document leaves all implementation and
acceptance work pending for review.

Josh is the project review owner. Assign implementation and methodology reviewers
when accepting the work packages; name the separate real-source/security/legal
owners before any restricted integration. These drafts do not assign those
approvals or claim a completed implementation review.
