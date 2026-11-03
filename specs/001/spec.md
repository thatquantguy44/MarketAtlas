# 001 — Securities-finance knowledge graph

Status: **WP-01 design complete; WP-02A foundation implemented; later work pending**.
Created 2026-11-03.
Owner: Josh / project owner; proposed implementation responsibilities are in
[plan.md](plan.md). This package specifies staged work; it does not
authorize source access, migrations, trading or a restricted-data deployment.

The parent [extension contract](../../docs/securities-finance-extension.md)
continues to govern isolation and canonical-instrument reuse. This feature
develops MarketAtlas REQ-012 and its design-level AC-012; its acceptance IDs below
are independent and do not mark existing implementation criteria passed.

## Purpose

**Confirmed workflow (Josh, 2026-11-03): lender/agent inventory coverage.**
The primary operator owns or represents lendable inventory and evaluates incoming
borrow requests against that inventory. Borrower-side sourcing is not the initial
workflow; recall/returns investigation remains a supporting planned capability.
**Confirmed allocation policy (Josh, 2026-11-03): coverage-first optimization.**
Maximize cleared fulfilled quantity per security, then honor FIFO request priority
among equally good coverage solutions, with a stable final allocation tie-break.
Other draft defaults and implementation remain subject to the
[WP-01 decision register](plan.md#wp-01-decision-register).

**Confirmed asset scope (Josh, 2026-11-03): equities and fixed income from the
first pilot**, with separate quantity conventions and test cases. **Equities use
whole shares only**, with integer allocations and a one-share increment for the
synthetic fixtures (Josh, 2026-11-03). **Fixed-income quantity rules are
instrument-specific** (Josh, 2026-11-03): each bond declares nominal currency,
precision, minimum nonzero allocation and permitted increments. Fixtures must
exercise different minimums/increments; exact synthetic values and step semantics
are declared in the contracts, not inferred from a universal bond convention.

**Confirmed balance policy (Josh, 2026-11-03): support both gross and already-net
inventory**, explicitly tagged and normalized to one free-capacity measure while
retaining the source balance basis. Included deductions are never subtracted twice.

**Confirmed input encodings (Josh, 2026-11-03): JSON and CSV records from the
start, JSON manifests and TOML settings.** Both record adapters share one normalized
contract and require equivalence tests.

**Confirmed source shape (Josh, 2026-11-03): versioned snapshots plus selected
lifecycle events.** Explicit inclusion boundaries prevent applying event effects
already contained in captured balances. This does not establish complete history.

**Confirmed initial rule scope (Josh, 2026-11-03): core operational checks**, with
configurable versions and parameters: active agreement, party/account permission,
instrument/location compatibility, settlement readiness and required-data
freshness. Capacity and quantity constraints remain mandatory; a separate
allow/block-list feature is deferred.

**Confirmed freshness policy (Josh, 2026-11-03): dataset-specific maximum ages in
TOML** for inventory, open requests and agreement-status confirmation. Check
agreement effective dates separately. Required stale/missing evidence remains
unknown and cannot clear an allocation. Exact fixture thresholds remain contract
work.

**Confirmed timestamp precision (Josh, 2026-11-03): precise timestamps and
date-only evidence.** Normalize timezone-aware timed values to UTC, preserve
date-only precision and withhold cutoff, freshness or FIFO claims when ambiguous.
Do not invent midnight timestamps.

**Confirmed ambiguous-FIFO policy (Josh, 2026-11-03): require proven order when
uncertainty could affect allocation.** Withhold affected proposals, report the
ordering ambiguity and retain the prior complete pack until resolved. Stable IDs
may break equal known timestamps, but cannot replace unknown chronology.

**Confirmed optimizer (Josh, 2026-11-03): SciPy/HiGHS MILP**, behind an adapter
with an optional Python optimization dependency. Ordered objective stages use
sequential solves/locks; independent validation checks allocations at exact
declared quantity precision. The package/version and numeric/run settings will
be explicit implementation contracts; no dependency is installed by these docs.

**Confirmed publication policy (Josh, 2026-11-03): proven results only.** Every
required objective stage and final tie-break must pass proof and independent
validation before publication. A time-limited feasible incumbent stays diagnostic;
retain the prior complete pack rather than publishing provisional allocations.

**Confirmed objective composition (Josh, 2026-11-03): both ordered stages and
explicit weighted tradeoffs within declared stages.** Keep coverage → FIFO →
canonical ties as the ordered default. Weighted profiles require reviewed,
versioned weights/scales and never relax eligibility, capacity or quantity rules.

**Confirmed balance metric (Josh, 2026-11-03): worst shortfall percentage.**
The separate balance profile maximizes the minimum fulfillment percentage among
positive-demand requests in the same security/unit group with provably usable
eligible supply. Other requests retain reported shortfalls and exclusion reasons;
the coverage/FIFO default is unchanged.

**Confirmed earnings inputs (Josh, 2026-11-03): supplied modeled net-benefit
coefficients per allocated unit for each potentially allocatable position/request
pairing.** Require quantity basis, currency, common horizon, method and assumption
provenance. The initial slice allocates using these inputs; fee/rate/valuation/FX
and duration-effect calculators are deferred.

WP-01's [file-first contracts](contracts.md) and
[synthetic settings](settings.example.toml) consolidate the selected policies and
explicit engineering defaults. WP-02A implements the typed envelope/quantity/reference
foundation; [its evidence](../../reports/spec001-wp02a-validation.md) covers structural
subcases only. WP-02B/C and later packages remain pending; no complete feature
acceptance is claimed by closing design or this foundation slice.

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
| Initial file-first demonstration | Invented parties, equity and fixed-income inventory with separate quantity conventions, open requests, agreements, rules, reservations, known loan allocations and recalls; coverage-first allocation proposals and a FIFO baseline; three report views | Synthetic artifacts only; no database or account access needed |
| Isolated persistence/integration | A separately authorized restricted database/schema, roles, adapters and negative access checks | Requires the parent contract's ownership, source-contract and security gates |
| Later enrichment | Collateral/rule explanations, instrument/borrower-parent concentration and commercial opportunity analysis | Requires its own inputs, methodology and acceptance evidence |

Initial inputs are versioned synthetic snapshots/events, not assumed connections
to a stock-loan system. Every borrow input declares whether it is an **open
request** or an **outstanding loan**; an existing borrowing position is not new
demand. Equity quantities use integer shares and a one-share fixture allocation
increment; fractional equity input is invalid for this pilot and cannot be silently
rounded. Fixed-income quantities use instrument-specific, versioned nominal
conventions including denomination currency, precision, permitted allocation
increments/step semantics and minimum nonzero allocation amounts. Missing required
conventions cannot be replaced with a universal default. Nominal amount is not
market value. Never combine share and
nominal totals or substitute one instrument's units for another's. Actual fee
calculations still require the earnings profile's separate input/method contract.

Proposals are simulations within a captured snapshot. They neither reserve
inventory nor execute, quote, approve or book a trade. The initial scope excludes
automatic source ingestion, new schedules, external publication, inferred
re-lending chains and a replacement credit/risk engine. Optimization claims are
limited to the declared allocation model, inputs and objective with retained
optimality evidence; they do not imply optimal earnings or market-wide liquidity.

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

A competing-request fixture uses one security: position A has 60,000 cleared
shares eligible for either request; position B has 40,000 eligible only for R1.
Older R1 requests 60,000 and newer R2 requests 40,000. A greedy FIFO baseline
choosing A first fills only 60,000. Coverage-first optimization assigns B's
40,000 plus A's 20,000 to R1 and A's remaining 40,000 to R2, filling 100,000.
This shows why position selection needs joint allocation; it does not establish
that FIFO request priority always reduces coverage.

A separate recall fixture identifies 15,000 and 5,000 shares in two explicit
owner-to-loan allocation records. A 20,000-share recall must find those records;
loans merely sharing the same security must not be treated as attributable.

## Capability map

| Stable module ID | Responsibility | Depends on |
| --- | --- | --- |
| `secfin-contracts` | Input grain, identifiers, temporal selection and synthetic fixtures | Existing synthetic instrument identity contract |
| `secfin-evaluation` | Typed/versioned checks, unknown states and evidence | `secfin-contracts` |
| `secfin-matching` | Capacity ledger, coverage-first optimizer, FIFO baseline and reproducible proposals | Contracts, evaluation |
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
| SF-FR-002 | Reference existing synthetic MarketAtlas instrument node IDs with type checks, plus explicitly declared bond reference fixtures in an isolated file-first catalog using the same identity/type contract. Reused IDs retain meaning and base/public outputs remain unchanged. Missing or ambiguous input mappings are quarantined/unknown; no fabricated public instrument or relationship. Later database integration resolves actual canonical rows separately. |
| SF-FR-003 | Keep business-effective time, source-available time/precision and system record time distinct. Support precise timezone-aware timestamps normalized to UTC and date-only evidence retaining its precision/context; withhold cutoff/freshness/FIFO claims that precision cannot establish. Select supported snapshot/event versions at explicit cutoffs; retain corrections and reject ambiguous active versions. Declare snapshot event-inclusion boundaries and apply only attributable, not-already-included effects once. Ambiguous boundaries withhold affected calculations. Missing availability or event coverage cannot support historical-as-known/complete-history claims. |
| SF-FR-004 | Accept both gross and already-net inventory with an explicit balance-basis tag and included-deduction contract. Normalize according to settlement/location and disjoint reservation/encumbrance components. Use either an authoritative net capacity or a documented gross-to-net bridge; never deduct included components twice. Retain source basis/provenance; an ambiguous basis cannot clear capacity and net data alone cannot establish a gross/deduction breakdown. |
| SF-FR-005 | Evaluate the core operational checks (active agreement, party/account permission, instrument/location compatibility, settlement readiness and required-data freshness) using configured, versioned parameters. Use dataset-specific TOML maximum ages for inventory, open requests and agreement-status confirmation against declared source evidence timestamps/reference cutoffs; agreement effective validity is separate. Retain `eligible`, `ineligible`, `unknown` or `not_evaluated` outcomes with all reason/input references. Required stale/missing evidence cannot clear capacity; neither file modification nor ingestion time refreshes it. A path alone is not eligibility. All required rules must pass; a separate allow/block-list feature is outside the initial slice. |
| SF-FR-006 | Compute request-specific candidate capacity and optimize allocations per security across the captured request set under the selected profile. The default maximizes cleared fulfillment, then applies FIFO priority among maximum-coverage solutions and a stable final tie-break. If uncertain FIFO order could affect allocation, withhold affected proposals, report the ambiguity and retain the prior complete pack; no unknown-chronology ID fallback. Enforce demand, position capacities and configured shared quantity headroom across the build; exclude unknown/ineligible edges and never reuse capacity. Retain a feasible greedy FIFO baseline using the same constraints/order-evidence policy. |
| SF-FR-007 | Explain excluded/unknown capacity and unfilled requests using a reconciled ledger. Primary quantity buckets are mutually exclusive; additional reason counts are non-additive. Preserve known failures alongside any missing information. |
| SF-FR-008 | Trace recalls through explicit current loan-allocation records and lifecycle events, accounting for known returns/cancellations once. Missing allocation lineage yields unknown impact, not an invented supply chain. |
| SF-FR-009 | Provide borrow coverage, allocation blockers and dependency-explorer views with inspectable underlying rows, rule results, units, cutoffs, input identity and freshness. Filters, sources and exports must share the same scope. |
| SF-FR-010 | Produce immutable, validated synthetic input/output packs. Retain objective/policy, method/solver version and settings, outcome status and available optimality evidence. Identical retained inputs/configuration/method reproduce the same business results, including allocation tie-breaks; failed or unproven optimization builds retain the prior complete artifact under the initial publication policy. |
| SF-FR-011 | Preserve the parent isolation boundary: no changes to existing public publication grains or source roles, no restricted grants to the current report reader/API, and no restricted records in public exports. |
| SF-FR-012 | Later collateral work must retain agreement/rule/valuation versions, asset allocations, margin/limit semantics and explicit missing facts; no eligible result from an agreement-to-collateral path alone. |
| SF-FR-013 | Configure typed, versioned objective profiles over the same hard allocation model: coverage, reviewed priority, defined balance, and modeled earnings when required inputs exist. Distinguish physical quantities, economic cost/benefit and preference scores. Support explicit objective precedence and reviewed weighted tradeoffs; reject missing inputs, invalid units, unknown terms and unsupported model/solver combinations. Retain component values and policy provenance for inspection and comparison. |
| SF-FR-014 | Support JSON and CSV record inputs through one normalized contract, with JSON manifests and TOML settings. Preserve identities, exact quantities, missing states, temporal precision and related/nested facts across encodings. Equivalent inputs produce identical normalized business facts/results with distinct raw provenance. Select one authoritative representation per logical dataset; alternative encodings cannot duplicate supply, demand or events. |
| SF-FR-015 | Consume supplied finite signed net-benefit coefficients per potentially allocatable position/request pairing with explicit amount, positive quantity basis, unit/convention, currency, common horizon and method/assumption provenance. Do not calculate or double-count underlying fees/costs/duration effects. Missing or incompatible coefficients fail a requested earnings/blend profile without removing candidate edges or inventing zeros. Non-earnings profiles do not require economic inputs; a fee calculator is later scope. |

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
- **Default objective hierarchy:** maximize total cleared fulfilled quantity separately
  per security and compatible unit. Fix that optimum, then lexicographically
  maximize each request's fill in FIFO order (declared request timestamp, then
  stable request ID). Finally fix a canonical allocation order using stable
  position/request IDs. Resolve ties explicitly; merely sorting solver input
  does not ensure reproducible allocations. FIFO never trades away the primary
  coverage optimum. IDs resolve equal known timestamps, not overlapping uncertain
  date/time intervals. Missing/ambiguous ordering facts follow a reviewed contract,
  not an invented timestamp. Uncertain order that could affect allocations
  withholds affected proposals and prevents replacing the prior complete pack.
  This policy does not claim fair allocation or optimal pricing.
- **Solve outcomes:** distinguish proven optimal, feasible but unproven,
  infeasible, time-limited without a feasible result, and failed. Independently
  validate quantities and all hard constraints. Partial coverage is a legitimate
  feasible result; unmet demand alone is not model infeasibility. The initial
  policy publishes only after every objective/tie-break stage is proven and the
  result validates; retain diagnostics and the prior pack otherwise.
- **Configurable profiles:** support both ordered stages and weighted terms within
  declared stages; the selected default remains ordered and coverage first.
  Alternative profiles may change precedence or blend reviewed, scaled terms
  within a stage. Priority before coverage can sacrifice overall fulfillment;
  earnings before coverage can leave otherwise eligible demand unfilled. Balance
  uses worst shortfall percentage across the confirmed request comparison
  population. This single worst-percentage stage is not recursive max-min fairness
  or guaranteed pro rata. An empty population has an unavailable metric.
  Earnings terms consume supplied net-benefit coefficients with unit, currency,
  horizon and assumption provenance; underlying fee/duration/valuation calculators
  are deferred. Missing inputs cannot be silently replaced with preference scores.
  Configuration never relaxes hard eligibility or capacity constraints. Detailed
  model/profile contracts are in the [plan](plan.md#configurable-allocation-model).

Quantities use exact declared precision. Values across units/currencies, snapshot
dates or overlapping populations are not summed. Any concentration/exposure
measure added later needs its own valuation, hierarchy, collateral and netting
contracts; an unweighted neighbor count is not such a measure.

## Quality, operational and access requirements

| ID | Requirement |
| --- | --- |
| SF-NFR-001 | File-first contracts, fixtures and validation use Python 3.11+ standard-library functionality and no credentials. Optimization uses the selected SciPy/HiGHS MILP adapter via a dedicated optional dependency extra, with a compatible package/version pinned during implementation and sequential objective solves/locks. Existing fixture/report workflows do not acquire a mandatory solver dependency. No package is installed by this spec. Optional persistence must use separately scoped roles and read-only source access. |
| SF-NFR-002 | Manifest identities include input hashes, effective/knowledge/system cutoffs, rule/configuration/objective/method versions, solver version/settings where used and code revision; time precision and unknown facts stay explicit. Retain solve status, objective values and bounds/gaps when available, without inventing proof. |
| SF-NFR-003 | Quarantine invalid identities, quantities, duplicate active versions and broken allocation references before producing cleared capacity. Zero and unavailable are distinct. Independently check solver output at exact declared precision against eligibility, demand, capacity and shared headroom; arbitrary rounding cannot repair an invalid solution. |
| SF-NFR-004 | Bound the initial workload to at most 100 positions, 20 requests, 20 outstanding loans and six-hop/200-row explanation responses. Oversized calculation inputs fail before publication; capped evidence signals truncation rather than implying complete coverage. Use a finite TOML optimization budget shared across groups/stages/tie-breaks; unfinished stages cannot publish a provisional pack. Larger workloads require measured validation. Proposed targets are ≤5-minute full build and ≤2-second prepared investigations on declared local hardware, not current benchmarks. |
| SF-NFR-005 | Preserve the previous artifact on validation/build failure. Replays do not duplicate events, proposals or publications; errors and exclusions are inspectable. |
| SF-NFR-006 | Keep synthetic artifacts and any later restricted artifacts in separate namespaces/deployments. Live client, agreement, position and collateral records never enter the existing public fixture or report API. |

## Acceptance criteria

All rows below are **pending full acceptance**. WP-02A supplies partial structural
evidence for SF-AC-003/004/015/017 in the
[validation report](../../reports/spec001-wp02a-validation.md); it does not complete
their adapter, temporal-selection, eligibility, optimizer or report scenarios.
File-first acceptance does not claim the parent's database permission checks passed.

| ID | Scenario and required evidence | Requirements |
| --- | --- | --- |
| SF-AC-001 | The worked fixture reconciles 180,000 gross → 90,000 cleared → 10,000 shortfall, with 50,000 reserved and 40,000 unknown separately explained. | FR-004/005/006/007 |
| SF-AC-002 | Equivalent tagged gross and net inputs produce identical normalized free capacity without representing duplicate supply. Net-available input is not reduced twice, and missing/ambiguous balance definitions cannot clear supply. Two competing requests cannot allocate more than one position's capacity/shared headroom. | FR-001/004/006 |
| SF-AC-003 | Wrong-type/unmapped instruments, duplicate active keys, incompatible units, invalid quantities and ambiguous versions cannot create cleared supply. | FR-001/002/003; NFR-003 |
| SF-AC-004 | Earlier cutoffs exclude later rules, reservations, returns and corrections; unknown availability withholds historical claims. Precise/date-only evidence preserves timezone/precision through both adapters; ambiguous cutoff, freshness and FIFO claims remain unknown without invented instants. Known equal timestamps and overlapping uncertain intervals are distinguished. Snapshot-included events are not reapplied, new effects apply once, and late events/reversals require supported boundary/correction evidence. Ambiguous boundaries withhold affected results. Current-source reconstruction and system-time replay remain distinguishable; selected events do not imply complete history. | FR-003/005/008; NFR-002 |
| SF-AC-005 | Each core operational check has independently verified pass/fail/missing-fact cases and version/parameter evidence. Independently test inventory, request and agreement-confirmation freshness just below/at/above their configured limits, separately from agreement effective validity; file/ingestion timestamps cannot refresh stale evidence. Eligible, ineligible, unknown and not-evaluated cases retain rule/input references; a connected path with missing or policy-stale required facts never passes. Known failures remain visible alongside missing facts. The collateral path-only case is a negative check, not acceptance of the later collateral engine. | FR-005/007/012 |
| SF-AC-006 | A recall reaches only explicitly attributed outstanding allocations; duplicate events and completed returns do not inflate impact. Snapshot/event reconciliation covers partial returns and reversals; a return alone cannot invent settled free inventory. | FR-001/003/004/008 |
| SF-AC-007 | The three views reconcile to pack rows, retain unavailable states and demonstrate filter/reset/source inspection at normal/narrow widths. | FR-009 |
| SF-AC-008 | Identical retained-input/configuration/method replay reproduces deterministic business identity/results; physical artifact hashes remain independently verifiable, with runtime/invocation metadata outside the business digest. Injected validation/publication failures leave the previous artifact usable. | FR-010; NFR-002/005 |
| SF-AC-009 | Existing MarketAtlas public fixture/report contracts remain unchanged; synthetic output provenance/classification and export boundaries are verified. | FR-011; NFR-006 |
| SF-AC-010 | Before restricted database integration: owner/contract review, negative writer/reader/API access tests and export review pass in an authorized isolated environment. | FR-011; NFR-001/006 |
| SF-AC-011 | Later collateral scenario passes independently checked allocation/valuation/rule tests, with stale/missing facts unavailable. | FR-012 |
| SF-AC-012 | Oversized computation inputs fail before publication; capped explanation responses signal truncation. Retained measurements assess the proposed build/investigation targets on declared hardware without claiming unmeasured capacity. | NFR-004/005 |
| SF-AC-013 | The competing-request fixture fills 100,000 versus the A-first FIFO baseline's 60,000 under identical constraints. Independent small-case optima, FIFO secondary priority, exact capacities/headroom, canonical ties and replay are verified. Ambiguous chronology that could affect allocation withholds affected proposals and retains the prior pack without ID fallback; equal known timestamps and proven order-independent cases are distinguished. Time limits at the first stage, between objectives and during final ties retain diagnostics/prior pack, even with a feasible incumbent. Unproven/time-limited/invalid results cannot publish or be labeled optimal; no provisional pack appears on first-run failure. | FR-003/006/010; NFR-002/003/004/005 |
| SF-AC-014 | Small independently checked cases demonstrate coverage, strict priority, worst-shortfall-percentage balance and synthetic earnings profiles. The 100k/50k-demand, 75k-supply balance example fills 50k/25k; unequal compatibility, bond minimums, excluded/zero-demand requests and empty populations retain correct metric/shortfall states. Ordered stages preserve earlier optima; weighted stages demonstrate declared tradeoffs without changing hard constraints or the default. Missing economic inputs, invalid/nonfinite weights, undefined scales and unsupported solver features fail explicitly. Reports retain raw/weighted components and shortfall, separate preference scores from modeled money, and identify identical-input comparisons. | FR-006/009/010/013; NFR-002/003 |
| SF-AC-015 | Separate equity-share and fixed-income nominal fixtures exercise normalization, eligibility, allocation and shortfall under declared precision/increment/minimum conventions. Equity allocations are integer shares at one-share increments; fractional equity inputs cannot be silently rounded or clear supply. At least two bond conventions exercise differing minimums/increments, zero/valid positive allocations, below-minimum/off-increment rejection and explicit unallocatable remainders. Missing or incompatible required conventions cannot clear supply or produce invalid proposals. Reports preserve nominal currency and unit identity without combining share/nominal quantities or treating nominal as market value. | FR-001/004/005/006/009; NFR-003 |
| SF-AC-016 | Equivalent JSON and CSV fixtures produce the same normalized facts and downstream business results for both asset classes, gross/net inputs, missing/zero quantities, timestamps and related records. Both adapters enforce the shared validation contract. Raw hashes/provenance remain distinct; alternative representations cannot be loaded as additive inventory, demand or events. | FR-001/003/004/010/014; NFR-002/003 |
| SF-AC-017 | Independently checked supplied-coefficient cases select greater modeled benefit, permit negative coefficients, preserve quantity basis/currency/horizon, and avoid double charging costs or multiplying duration again. Missing/mixed/nonrepresentable inputs fail the requested earnings/blend profile while a non-economic profile remains usable. Existing base fixture instrument meanings/outputs stay unchanged; isolated bond fixtures are declared/type-checked and never asserted as existing database rows. | FR-002/006/010/015; NFR-002/003/006 |

`FR-*` and `NFR-*` in this table abbreviate this document's `SF-FR-*` and
`SF-NFR-*` IDs. Existing MarketAtlas AC-012 remains design-level evidence.

## Review decisions and future gates

WP-01 is complete at design scope. The confirmed decisions and authored synthetic
engineering defaults are consolidated in [contracts.md](contracts.md) and
[settings.example.toml](settings.example.toml). All feature acceptance rows remain
pending; closing design does not establish a completed implementation review.

WP-02A's typed contracts and isolated canonical-reference catalog are implemented
and validated at their stated scope. WP-02B's business fixtures and format adapters
are next, followed by WP-02C temporal selection. The optimizer/package lock follows in WP-04.
Real-source interfaces, ownership, freshness thresholds, agreement interpretation,
valuation/netting, hosting and support remain later integration decisions. The
first earnings profile consumes supplied modeled benefit; fee/rate/valuation/FX
calculators require separate scope. Existing macro schedules remain unchanged.

Implementation sequence, proposed commands, tests and gates: [plan.md](plan.md).
