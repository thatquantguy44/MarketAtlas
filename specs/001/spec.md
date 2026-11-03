# 001 — Securities-finance knowledge graph

Status: **draft for review; not implemented**. Created 2026-11-03.
Owner: Josh / project owner; proposed implementation responsibilities are in
[plan.md](plan.md). This package specifies future work; creating it does not
authorize source access, migrations, trading or a restricted-data deployment.

The parent [extension contract](../../docs/securities-finance-extension.md)
continues to govern isolation and canonical-instrument reuse. This feature
develops MarketAtlas REQ-012 and its design-level AC-012; its acceptance IDs below
are independent and do not mark existing implementation criteria passed.

## Purpose

Help a securities-finance operator answer:

1. Which inventory can meet an open borrow request at a stated cutoff?
2. Why is apparently available inventory excluded or awaiting information?
3. Which known loans and allocations are affected by a recall or shared dependency?

The graph supplies identity, relationships, dependency paths and explanations.
Quantity accounting and versioned rule evaluation supply the numerical results.
Graph connectivity, screen distance and centrality do not establish eligibility,
credit exposure, executable liquidity or investment value.

## Scope and assumptions

| Stage | Included | Completion boundary |
| --- | --- | --- |
| Initial file-first demonstration | Invented parties, whole-share equity inventory, open requests, agreements, rules, reservations, known loan allocations and recalls; deterministic matching proposals; three report views | Synthetic artifacts only; no database or account access needed |
| Isolated persistence/integration | A separately authorized restricted database/schema, roles, adapters and negative access checks | Requires the parent contract's ownership, source-contract and security gates |
| Later enrichment | Collateral/rule explanations, instrument/borrower-parent concentration and commercial opportunity analysis | Requires its own inputs, methodology and acceptance evidence |

Initial inputs are versioned synthetic snapshots/events, not assumed connections
to a stock-loan system. Every borrow input declares whether it is an **open
request** or an **outstanding loan**; an existing borrowing position is not new
demand. Whole shares are the initial quantity unit. Bond nominal amounts, other
units and actual fee calculations are outside this first slice.

Proposals are simulations within a captured snapshot. They neither reserve
inventory nor execute, quote, approve or book a trade. The initial scope excludes
automatic source ingestion, new schedules, external publication, optimization
claims, inferred re-lending chains and a replacement credit/risk engine.

## Users and review scenarios

| User | Scenario | Required result |
| --- | --- | --- |
| Inventory/borrow operator | Inspect an open request and candidate supply | Requested quantity, cleared candidate capacity, proposed coverage, shortfall and blockers |
| Operations analyst | Investigate a blocked position | Rule/input versions, exact reason codes, missing facts and timestamps |
| Recall operator | Inspect a recall against known loan allocations | Affected loan/allocation IDs and quantities; unknown attribution stays unknown |
| Reviewer | Replay or audit an explanation | Input/configuration/code identities, three time dimensions, rule results and reproducible output |

### Worked synthetic coverage case

An open request needs **100,000 shares** of one canonical instrument at one
delivery location. Assume the required sample checks pass where stated:

| Position | Gross quantity | Reservation | Rule state on remaining capacity | Cleared quantity |
| --- | ---: | ---: | --- | ---: |
| Account A | 60,000 | 0 | Eligible | 60,000 |
| Account B | 80,000 | 50,000 | Eligible | 30,000 |
| Account C | 40,000 | 0 | Unknown: agreement facts missing | 0 |

Expected results: 180,000 gross shares; 50,000 reserved; 40,000 awaiting required
facts; 90,000 cleared/proposed shares; 10,000 request shortfall. This fixture uses
a declared gross baseline: feeding an already-net available quantity into the
same calculation must not subtract reservations again. Unknown capacity is
reported separately, not counted as cleared or classified as a known rejection.

A separate recall fixture identifies 15,000 and 5,000 shares in two explicit
owner-to-loan allocation records. A 20,000-share recall must find those records;
loans merely sharing the same security must not be treated as attributable.

## Capability map

| Stable module ID | Responsibility | Depends on |
| --- | --- | --- |
| `secfin-contracts` | Input grain, identifiers, temporal selection and synthetic fixtures | Existing synthetic instrument identity contract |
| `secfin-evaluation` | Typed/versioned checks, unknown states and evidence | `secfin-contracts` |
| `secfin-matching` | Capacity ledger and deterministic allocation proposals | Contracts, evaluation |
| `secfin-dependencies` | Bounded recall/loan/account paths with quantity attribution | Contracts |
| `secfin-reporting` | Borrow coverage, blockers and dependency investigation | Evaluation, matching, dependencies |
| `secfin-collateral` | Later collateral allocations, valuations and rule checks | Contracts, evaluation; separately scoped |

Build contracts → evaluation → matching → dependency investigation → reporting.
Persistence and later collateral are explicit follow-on gates, not implicit parts
of the file-first implementation.

## Functional requirements

| ID | Requirement |
| --- | --- |
| SF-FR-001 | Normalize positions, requests, parties, accounts, agreements, rules, loans, allocations and events at declared grains with stable IDs and source-record provenance. Reject conflicting duplicates; do not merge by ticker or sum duplicate source representations. |
| SF-FR-002 | Reference existing synthetic MarketAtlas instrument node IDs with type checks. Missing or ambiguous mappings are quarantined/unknown; no fabricated public instrument or relationship. |
| SF-FR-003 | Keep business-effective time, source-available time/precision and system record time distinct. Select supported versions at explicit cutoffs; retain corrections and reject ambiguous active versions. Missing availability cannot support historical-as-known claims. |
| SF-FR-004 | Normalize inventory according to the source balance definition, settlement/location and disjoint reservation/encumbrance components. Use either an authoritative net capacity or a documented gross-to-net bridge; never both deductions. |
| SF-FR-005 | Evaluate configured, versioned rules as `eligible`, `ineligible`, `unknown` or `not_evaluated`, retaining all reason/input references. A path alone is not eligibility. All required rules must pass before capacity is cleared. |
| SF-FR-006 | Compute request-specific candidate capacity and deterministic proposals across the captured request set. Enforce position capacities and configured quantity headroom globally within that build; do not reuse the same capacity for multiple proposals. |
| SF-FR-007 | Explain excluded/unknown capacity and unfilled requests using a reconciled ledger. Primary quantity buckets are mutually exclusive; additional reason counts are non-additive. Preserve known failures alongside any missing information. |
| SF-FR-008 | Trace recalls through explicit current loan-allocation records and lifecycle events, accounting for known returns/cancellations once. Missing allocation lineage yields unknown impact, not an invented supply chain. |
| SF-FR-009 | Provide borrow coverage, allocation blockers and dependency-explorer views with inspectable underlying rows, rule results, units, cutoffs, input identity and freshness. Filters, sources and exports must share the same scope. |
| SF-FR-010 | Produce immutable, validated synthetic input/output packs. Identical retained inputs/configuration/method reproduce the same business results; failed builds retain the prior complete artifact. |
| SF-FR-011 | Preserve the parent isolation boundary: no changes to existing public publication grains or source roles, no restricted grants to the current report reader/API, and no restricted records in public exports. |
| SF-FR-012 | Later collateral work must retain agreement/rule/valuation versions, asset allocations, margin/limit semantics and explicit missing facts; no eligible result from an agreement-to-collateral path alone. |

## Calculation and decision semantics

- **Open demand:** the request's authoritative remaining quantity, or a validated
  bridge from original/filled/cancelled quantities. Outstanding loan size is not
  a substitute. Negative, inconsistent or unit-mismatched quantities are invalid.
- **Cleared candidate capacity:** compatible free capacity passing every required
  check for that request. It is request-specific and cannot be added across
  requests as if it were independent stock.
- **Proposed coverage:** quantity actually assigned by the deterministic simulation
  after competing requests and shared headroom are accounted for.
- **Shortfall:** open demand minus proposed coverage, bounded below by zero.
  Unknown capacity is displayed alongside the shortfall, not included in coverage.
- **Decision aggregation:** a known failed required rule makes the result
  ineligible; otherwise missing required facts make it unknown; only all-pass is
  eligible. Retain the individual rule outcomes so a known failure does not hide
  missing facts. `not_evaluated` never clears capacity.
- **Ordering:** a versioned sample policy orders requests and candidate positions
  with stable tie-breakers. It is a demonstration policy, not a claim of optimal
  pricing, fair allocation or production suitability.

Quantities use exact declared precision. Values across units/currencies, snapshot
dates or overlapping populations are not summed. Any concentration/exposure
measure added later needs its own valuation, hierarchy, collateral and netting
contracts; an unweighted neighbor count is not such a measure.

## Quality, operational and access requirements

| ID | Requirement |
| --- | --- |
| SF-NFR-001 | File-first use requires Python 3.11+ standard-library functionality and no credentials. Optional persistence must use separately scoped roles and read-only source access. |
| SF-NFR-002 | Manifest identities include input hashes, effective/knowledge/system cutoffs, rule/configuration/method versions and code revision; time precision and unknown facts stay explicit. |
| SF-NFR-003 | Quarantine invalid identities, quantities, duplicate active versions and broken allocation references before producing cleared capacity. Zero and unavailable are distinct. |
| SF-NFR-004 | Bound the initial workload to at most 100 positions, 20 requests, 20 outstanding loans and six-hop/200-row explanation responses. Oversized calculation inputs fail before publication; capped evidence signals truncation rather than implying complete coverage. Larger workloads require measured validation. Proposed targets are ≤5-minute full build and ≤2-second prepared investigations on declared local hardware, not current benchmarks. |
| SF-NFR-005 | Preserve the previous artifact on validation/build failure. Replays do not duplicate events, proposals or publications; errors and exclusions are inspectable. |
| SF-NFR-006 | Keep synthetic artifacts and any later restricted artifacts in separate namespaces/deployments. Live client, agreement, position and collateral records never enter the existing public fixture or report API. |

## Acceptance criteria

All rows below are **pending implementation**. File-first acceptance does not
claim the parent contract's database permission checks passed.

| ID | Scenario and required evidence | Requirements |
| --- | --- | --- |
| SF-AC-001 | The worked fixture reconciles 180,000 gross → 90,000 cleared → 10,000 shortfall, with 50,000 reserved and 40,000 unknown separately explained. | FR-004/005/006/007 |
| SF-AC-002 | Net-available input is not reduced twice; two competing requests cannot allocate more than one position's capacity/shared headroom. | FR-001/004/006 |
| SF-AC-003 | Wrong-type/unmapped instruments, duplicate active keys, incompatible units, invalid quantities and ambiguous versions cannot create cleared supply. | FR-001/002/003; NFR-003 |
| SF-AC-004 | Earlier cutoffs exclude later rules, reservations, returns and corrections; unknown availability withholds historical claims. Current-source reconstruction and system-time replay remain distinguishable. | FR-003/005/008; NFR-002 |
| SF-AC-005 | Eligible, ineligible, unknown and not-evaluated cases retain rule/input evidence; a connected path with missing or policy-stale required facts never passes. The collateral path-only case is a negative check, not acceptance of the later collateral engine. | FR-005/007/012 |
| SF-AC-006 | A recall reaches only explicitly attributed outstanding allocations; duplicate events and completed returns do not inflate impact. | FR-001/008 |
| SF-AC-007 | The three views reconcile to pack rows, retain unavailable states and demonstrate filter/reset/source inspection at normal/narrow widths. | FR-009 |
| SF-AC-008 | Identical retained-input replay reproduces output identity; injected validation/publication failures leave the previous artifact usable. | FR-010; NFR-002/005 |
| SF-AC-009 | Existing MarketAtlas public fixture/report contracts remain unchanged; synthetic output provenance/classification and export boundaries are verified. | FR-011; NFR-006 |
| SF-AC-010 | Before restricted database integration: owner/contract review, negative writer/reader/API access tests and export review pass in an authorized isolated environment. | FR-011; NFR-001/006 |
| SF-AC-011 | Later collateral scenario passes independently checked allocation/valuation/rule tests, with stale/missing facts unavailable. | FR-012 |
| SF-AC-012 | Oversized computation inputs fail before publication; capped explanation responses signal truncation. Retained measurements assess the proposed build/investigation targets on declared hardware without claiming unmeasured capacity. | NFR-004/005 |

`FR-*` and `NFR-*` in this table abbreviate this document's `SF-FR-*` and
`SF-NFR-*` IDs. Existing MarketAtlas AC-012 remains design-level evidence.

## Review decisions and future gates

The proposed defaults are synthetic-only, whole-share equity quantities,
file-first delivery, deterministic sample ordering and a separate report artifact.
Review them before implementing the first slice. Real source interfaces, balance
definitions, freshness limits, allocation policy, agreement interpretation,
valuation/netting methodology, hosting and support owners remain unconfirmed.
No existing macro ingestion or report schedule is repurposed by this document.

Implementation sequence, proposed contracts/commands, tests and decision gates:
[plan.md](plan.md).
