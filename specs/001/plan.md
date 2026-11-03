# 001 — Securities-finance implementation plan

Status: **WP-01 design complete; WP-02A implemented; WP-02B onward pending**.
Created 2026-11-03.
Specification: [spec.md](spec.md). Parent boundary:
[extension contract](../../docs/securities-finance-extension.md).

This plan implements the stable modules in the specification. Work packages below
are the feature's ordered implementation backlog. WP-01 is complete at design
scope; WP-02A is implemented and WP-02B/C onward remain pending. They do not
replace the main product task register or authorize a live deployment.

## WP-01 decision register

User-confirmed choices below define the pilot. The linked contracts/settings
separately identify authored synthetic engineering defaults; these do not establish
real-source policies or implementation acceptance.

| ID | Decision | Status | Selection or recommendation |
| --- | --- | --- | --- |
| SF-D-001 | Primary workflow | Confirmed by Josh, 2026-11-03 | Lender/agent inventory coverage: match incoming open requests to represented inventory and explain usable, blocked and unknown capacity. |
| SF-D-002 | Default competing-request allocation | Confirmed by Josh, 2026-11-03 | Coverage-first optimization per security; FIFO request priority among maximum-coverage solutions, then a canonical allocation tie-break. Keep greedy FIFO as a comparison baseline. |
| SF-D-003 | Asset scope and quantity policy | Confirmed by Josh, 2026-11-03 | Equities and fixed income in the first pilot, with separate conventions/tests. Equity allocations use whole shares only and a one-share fixture increment. Each bond declares its own nominal currency, precision, minimum nonzero allocation and permitted increment; fixtures exercise differing minimums/increments. Specific synthetic values and precise step semantics must be explicit in the contracts, with no universal bond default. |
| SF-D-004 | Inventory balance contract | Confirmed by Josh, 2026-11-03 | Support both gross and already-net balances, explicitly tagged. Normalize each source to one free-capacity measure, retain its balance basis and included deductions, and verify no double deduction. Version-1 synthetic source fields and normalization semantics are documented in contracts.md; real-source mappings are a later gate. |
| SF-D-005 | Source shape and encoding | User choices confirmed, 2026-11-03; v1 technical contract documented | Support JSON and CSV records immediately, JSON manifests and TOML settings. Use versioned snapshots plus selected identified lifecycle events, with explicit inclusion boundaries to prevent double application. Both adapters share one normalized contract and require equivalence tests. Version-1 event coverage, CSV conventions and keyed child-table mappings are in contracts.md. |
| SF-D-006 | Rule vocabulary, timing and freshness policy | User choices confirmed, 2026-11-03; synthetic thresholds/fields documented | Implement the core operational checks with configurable versions/parameters and dataset-specific TOML freshness limits, separate from agreement effective validity. Accept timezone-aware precise timestamps normalized to UTC and date-only evidence retaining its precision; withhold unsupported cutoff/freshness/FIFO claims. If uncertain FIFO order could affect allocation, withhold affected proposals and retain the prior complete pack until resolved; report the ambiguity and use no stable-ID fallback for unknown chronology. Required stale/missing evidence stays unknown. Capacity/quantity constraints and four-state/three-clock boundaries remain mandatory; separate allow/block lists are deferred. Explicit synthetic thresholds, evidence clocks and ordering fields are in contracts.md and settings.example.toml. |
| SF-D-007 | Optimization engine and configurable policy contract | User choices confirmed, 2026-11-03; v1 profiles/run contract documented | Use optional SciPy/HiGHS MILP, sequential solves/locks and exact allocation validation; proven-only publication with prior-pack recovery. Support ordered/weighted stages, the ordered coverage/FIFO default and worst-percentage request balance. Consume supplied net-benefit coefficients with quantity basis, currency, horizon and provenance; no fee calculator. Synthetic numeric/run settings, profiles and example weights are explicit in the linked contracts/settings; no package is installed. |

The seven decision areas are closed for the synthetic file-first design. User
choices and authored technical defaults are distinguished in
[contracts.md](contracts.md) and [settings.example.toml](settings.example.toml).
Those contracts specify input grains, encoding/null rules, event inclusion,
quantity conventions, freshness clocks, objective coefficients, numerical proof,
replay identity and acceptance traces. Synthetic example weights and thresholds
are explicit test settings, not asserted real-source operating policies.

**WP-02A is complete** at its typed contract/reference scope; see
[validation evidence](../../reports/spec001-wp02a-validation.md). **WP-02B is next**:
business fixtures and JSON/CSV adapters. Later implementation, optimizer package
installation, database integration and complete feature acceptance remain pending.
Josh remains the project review owner; no restricted access is implied.

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

The contract and catalog modules below are implemented in WP-02A. Other runtime
paths remain proposals. Design-time contracts/settings under `specs/001/` exist
but are not consumed by a runtime file parser yet:

| Path | Responsibility |
| --- | --- |
| `specs/001/contracts.md` | WP-01 normalized file, temporal, quantity, coefficient and numerical contracts |
| `specs/001/settings.example.toml` | Parseable synthetic defaults; not yet runtime-consumed |
| `src/market_atlas/securities_finance/contracts.py` | Typed/versioned input contracts, identity/unit/time checks |
| `.../catalog.py` | Implemented immutable synthetic instrument/convention catalog and quantity/reference binding |
| `.../fixtures.py` | Deterministic invented cases referencing synthetic instrument node IDs |
| `.../adapters.py` | JSON and CSV readers into one normalized contract; split format adapters if needed |
| `.../selection.py` | Effective/source-knowledge/system-record cutoff selection |
| `.../eligibility.py` | Approved typed rules, aggregation and reason/input evidence |
| `.../matching.py` | Hard allocation model, capacity ledger, solver adapter and FIFO baseline; split further before implementation if needed |
| `.../policy.py` | Typed objective registry, profile validation, objective stages and coefficient provenance |
| `.../dependencies.py` | Bounded attributable loan/recall paths |
| `.../pack.py` | Immutable manifests, validation and atomic artifact delivery |
| `configs/securities_finance_fixture.toml` | Synthetic scope, rule/policy versions and workload bounds; no credentials |
| `contracts/securities_finance_fixture.*` | File-contract declarations; not an approved live-source registry entry |
| `tests/test_securities_finance_*.py` | Independent numerical, temporal, graph and failure checks |
| `powerbi/securities-finance/` | Proposed report-source/guidance namespace; native Power BI execution is optional future scope |
| `data/generated/securities-finance-fixture/` | Ignored local generated inputs, packs and browser workspace |

The `.../` rows abbreviate `src/market_atlas/securities_finance/`. JSON and CSV
records, JSON manifests and TOML settings are selected. Implement their versioned
schemas and parsing conventions as specified in [contracts.md](contracts.md); no
additional interchange-format dependency is required by this choice.

## Input grains and identity contracts

Every row has a stable source identity, input manifest and temporal/provenance
fields where applicable. Version IDs are separate from business IDs.

| Object | Grain and essential facts |
| --- | --- |
| `legal_entity` / `account` | Stable party/account identity; explicit beneficial owner, lender, borrower or custodian role; no ticker-based party resolution |
| `inventory_position` | One authoritative account/instrument/location/optional-lot position version; asset type, share/nominal unit and precision, nominal currency where applicable, quantity-convention reference, explicit gross/net balance basis and included-deduction contract, settlement state |
| `reservation` / `encumbrance` | One identified component/event against a position, with quantity, status and timing; overlapping components must be reconciled, not simply added |
| `borrow_request` | One request/version with borrower, canonical instrument, required location/date and authoritative open quantity or a reconciled original/filled/cancelled bridge |
| `agreement` / `rule` | Agreement/rule version, participating parties, scope, required input fields, priority and typed expression reference |
| `loan` | One known loan/version with agreement, instrument, unit, outstanding quantity and lifecycle state; not interpreted as a request |
| `loan_allocation` | Explicit quantity attribution from a known loan to an owner/account/position; distinguish it from a proposed allocation |
| `recall` / `return_event` | Identified lifecycle event with quantity, referenced loan/allocation, effective/known/recorded times and reversal/status semantics |
| Later `collateral_asset` / `collateral_allocation` | Assets/allocations, valuation timestamp/currency/basis, agreement/rules and haircut/margin convention; absent inputs stay unknown |

Use the existing synthetic instrument identity generation/reference contract.
Reuse existing share identities unchanged; declare additional known synthetic bond
references only in the isolated feature catalog described in
[contracts.md](contracts.md#canonical-instrument-fixture-boundary). These are not
asserted database rows. Validate canonical node type before accepting a link. Do not create
new public entities to repair missing identifiers or import private records into
`atlas`/`atlas_report`. Duplicate representations of the same position require an
explicit authoritative-source mapping; different accounts holding the same ISIN
are not duplicate positions merely because the security matches.

## Input encoding contract

Provide both JSON and CSV representations of each supported synthetic record
type from the first pilot. Both adapters produce the same typed normalized
objects before temporal selection, rule evaluation or allocation. JSON manifests
declare schema version, dataset/representation identity, source file hashes and
authoritative input selection; TOML settings select scope and policies.

Define CSV encoding/dialect, explicit missing-value representation, stable keys,
timestamp precision and exact numeric parsing. Define lossless related tables for
nested JSON facts such as rule inputs/reason references; do not drop structure or
infer identifiers from row order. The version-1 mappings are fixed in [contracts.md](contracts.md#encoding-and-exact-values).
Compare both formats for equity and fixed-income fixtures, gross/net balances,
missing versus zero values, temporal versions and related records. Preserve the
same validation/rejection semantics across adapters.

Equivalent representations must produce identical normalized business facts and
allocation results, while raw file hashes and format-specific provenance remain
distinct. They need not have identical input-manifest or complete pack identities.
The manifest selects one authoritative representation per logical dataset; loading
both equivalent files must not double inventory, demand or lifecycle events.

## Snapshot and lifecycle-event contract

Use versioned captured state for positions, open requests, agreements and known
loan allocations, with selected identified reservation, recall and return events.
This is not a claim of a complete event-sourced history. Each relevant snapshot
declares its source stream, state scope and which event effects it already
contains, using included event IDs or a source ordering/watermark with defined
inclusion semantics. A capture timestamp alone is not an inclusion boundary.

Select snapshots and events under all three cutoffs before applying changes.
Apply an event only to its declared state component, only if its effect is not
already included, and once per stable source/event identity. Explicit correction,
reversal and supersession links preserve history; replaying or re-encoding an
event cannot apply it twice. Late-arriving events that predate a snapshot need
supported inclusion/correction evidence, not an assumed incremental adjustment.
If the boundary or affected-state attribution is ambiguous, withhold the affected
calculation and retain an inspectable unknown/reconciliation reason.

Separate loan outstanding, reservations and settled free inventory: a recorded
return does not automatically establish settled lendable capacity. The source
contract must support each state transition. Reconcile snapshot-plus-event
results to the authoritative balances where supplied. Test included versus new
events, duplicate replay, late events, reversals, partial returns, gross/net
snapshots and both encodings. Missing event coverage cannot support a claim of
complete historical reconstruction.

## Freshness policy

Configure separate maximum ages in TOML for inventory evidence, open-request
evidence and agreement-status confirmation. Each policy declares the authoritative
source evidence/confirmation field and its reference clock/cutoff; retain the
resolved policy and numeric threshold with each evaluation. File modification
time and MarketAtlas ingestion time cannot make old source evidence fresh.
An agreement's document creation/modification age is not a substitute for current
status confirmation. Check the agreement's effective validity separately.

Missing or stale required evidence produces unknown and cannot clear capacity;
retain known failed checks alongside missing/stale facts. Declare exact synthetic
thresholds and boundary semantics in the fixture settings, and test just-below,
at and just-above each maximum age independently. Changing one dataset's threshold
must not silently change another's. Preserve date/time precision and all three
clocks under the selected precision policy below.

## Timestamp precision and uncertain order

Accept timezone-aware precise timestamps and date-only evidence. Normalize timed
values to UTC while retaining their original precision/provenance. Preserve a
date-only value as date precision with a declared source-calendar/timezone context
where needed; never replace it with an asserted midnight or capture timestamp.
Business dates such as settlement date remain distinct from timestamp evidence.

For timestamp evidence with date precision, reason over the supported interval,
not an invented instant. Establish cutoff inclusion, freshness or relative FIFO
order only when the available precision proves the result. Withhold ambiguous
claims with an inspectable unknown reason; missing timezone/calendar context
cannot be guessed to resolve them. Test precise/date-only equivalents where the
claim is provable, overlapping day/instant intervals, cutoff/freshness boundaries
and JSON/CSV precision preservation. Preserve all three independent clocks.

Stable IDs may break genuinely equal, known request timestamps; they do not prove
chronological order between requests with overlapping uncertain intervals. If
that uncertainty could change allocation of limited supply, withhold affected
proposals, retain diagnostics and do not replace the previous complete pack until
ordering is resolved. If no previous pack exists, there is no newly validated
pack to serve. No stable-ID chronology fallback is permitted under this policy.
Only treat ambiguous chronology as harmless if allocation independence is actually
established; full demand satisfaction is one simple case. Test a competing-request
shortage that blocks publication, equal known timestamps that allow the approved
ID tie-break, and a provably order-independent case without a false FIFO claim.

## Time, quantity and decision design

1. Freeze input hashes and all three cutoffs in the run manifest. Select uniquely
   effective versions whose supported source availability is within the knowledge
   cutoff and whose record interval is within any requested system cutoff.
   Preserve date-only precision and distinguish captured-current facts from
   replayable history. An unknown timestamp is not replaced with capture time.
2. Accept both gross and already-net balances with an explicit source balance
   basis; normalize one authoritative baseline per position. For an already-net
   available balance, validate its declared included deductions and use its net
   capacity without subtracting those components again. For a gross baseline,
   subtract only disjoint, reconciled components. Do not subtract outstanding
   loans again if the upstream definition already excludes them. Missing or
   ambiguous balance definitions cannot create cleared capacity. Preserve source
   basis, included-deduction metadata and the supported normalization bridge;
   never invent gross quantities or a deduction breakdown from net data alone.
3. Use exact quantities at the declared scale for both equity-share and
   fixed-income nominal fixtures. Equities use integer shares and a one-share
   fixture allocation increment; fractional equity quantities are invalid in this
   pilot, never silently rounded. Resolve the instrument's quantity convention,
   nominal currency where applicable, allocation increment and any minimum
   nonzero allocation before proposing quantities. Fixed-income conventions are
   instrument-specific and versioned; declare the increment's origin/step semantics
   explicitly rather than assuming that a minimum and a step imply the same valid
   quantities in every convention. Include at least two synthetic bond conventions
   with differing minimums/increments and test zero, valid positive, below-minimum,
   off-increment and residual-unallocated cases. Missing required conventions
   remain unavailable; do not invent a universal bond denomination. Reject
   negatives, contradictory missing/value states and incompatible units. Nominal
   currency identifies denomination, not market value; prices, valuations and FX
   are not invented to calculate exposure. Verify increment/minimum constraints
   independently and select a solver formulation that can actually enforce them.
4. Evaluate the selected typed core rule vocabulary: active agreement,
   party/account permission, instrument/location compatibility, settlement
   readiness and required-data freshness, with required facts explicit. Keep
   capacity and quantity-convention constraints mandatory in every profile.
   Rule versions and parameters are configurable; a separate agreement-scoped
   allow/block-list feature is deferred beyond the first pilot. Store
   expression/version, all input references,
   per-rule outcome, reason codes, evaluation time and freshness status. Do not
   execute arbitrary Python/SQL from data or parse legal prose as an approval.
5. Clear capacity only for all-pass required checks. A known failure dominates
   an unknown aggregate result but retains the missing-fact outcomes. Assign each
   quantity to one primary ledger bucket; additional reason counts are explicitly
   non-additive. Record unknown/not-evaluated capacity independently.
6. Build a joint allocation model on cleared request/position edges. Bound each
   position by normalized free capacity and each request by open demand; apply
   supported shared quantity headroom without reusing capacity. Use the selected
   versioned objective profile. The default maximizes coverage per security,
   fixes that optimum, then maximizes request fills lexicographically by FIFO
   timestamp/request ID and resolves remaining allocations by canonical IDs.
   If uncertain FIFO order could change allocations, apply the withholding policy
   above; do not emit a substitute ordering. A separate greedy FIFO baseline uses
   the same constraints and order-evidence policy. Independently
   reconcile every proposed quantity before pack publication.
7. Trace recalls only through explicit allocations and supported events. Apply
   partial returns/reversals once using stable event IDs and time selection.
   Where attribution is missing, return unknown impact rather than following all
   loans of the same security as though they share ownership.

The proposal ledger simulates one snapshot; independent builds do not reserve
real capacity against each other. Production concurrency/execution would need
separate transaction/reservation semantics and is outside this plan's first slice.

## Configurable allocation model

Keep the **feasible allocation model**, **objective policy** and **solver adapter**
separate. Configuration selects typed terms and reviewed inputs, never arbitrary
Python/SQL expressions or permission overrides. Unknown required facts remove
candidate edges; no preference penalty may buy an exception to eligibility.

For each compatible security/unit group, let `x[i,j]` be quantity allocated from
position `i` to request `j`, `c[i]` normalized free capacity, `d[j]` open demand,
and `u[j]` explicit shortfall. The base constraints are:

```text
x[i,j] >= 0, at the declared precision and supported allocation increment/minimum
sum_j x[i,j] <= c[i]
sum_i x[i,j] + u[j] = d[j], with u[j] >= 0
x[i,j] = 0 on every incompatible, ineligible, unknown or not-evaluated edge
plus supported, typed shared-headroom constraints
```

Unused inventory is allowed. A shortage is represented by `u`, so demand above
available supply does not itself make the model infeasible. Do not optimize raw
share totals across unrelated securities. The first slice uses independent
security/unit groups; a limit coupling different groups needs an explicitly
supported joint model and cannot be enforced by independently solving each group.
Each group also validates quantity-convention identity and nominal currency where
applicable. Both equity and fixed-income fixtures are required; their quantities
are never pooled. Nonzero minimum allocations can require discrete activation
constraints rather than simple flow capacities; implement the selected convention/formulation
from [contracts.md](contracts.md#quantity-and-capacity-semantics).

| Profile / term | Model expression or stages | Required policy/input contract |
| --- | --- | --- |
| `coverage_first` (selected default) | Minimize `sum(u)`; fix that optimum; minimize each request's shortfall in FIFO order; canonical allocation tie-break | Demand/capacity, request ordering timestamp and stable IDs |
| `priority_service` | Lexicographically minimize shortfall per priority tier, then FIFO and canonical ties | Reviewed tier membership/order; configuration explicitly states whether tier priority precedes or follows total coverage |
| `balanced_fulfillment` | After configured higher-priority stages, minimize worst relative shortfall `z`, with `u[j] <= z*d[j]` for each comparison request | Confirmed request-level population: positive demand, same security/unit group, provably usable eligible supply under the quantity constraints; excluded requests still retain shortfalls and reasons |
| `net_earnings` | Minimize negative supplied modeled net benefit `-sum(b[i,j]*x[i,j])` under the declared stage ordering | Supplied amount/positive quantity basis, matching convention/currency/common horizon and method/assumption provenance; no first-slice fee/rate/valuation/FX/duration calculator |
| `preference_cost` | Minimize `sum(p[j]*u[j]) + sum(q[i,j]*x[i,j])` within its declared objective stage | Nonnegative reviewed penalty coefficients, units/scales and documented willingness to trade service outcomes; scores are preferences, not money |

The same term can be placed at different priorities. For example, coverage then
earnings maximizes modeled earnings only within maximum-coverage allocations;
earnings first may deliberately leave low-benefit demand unfilled. Priority first
may sacrifice overall coverage; weighted priority costs are not strict tier
precedence. A worst-shortfall balance policy is not automatically pro rata.
Each named profile fixes these semantics rather than relying on its label.

Confirmed balance metric/population (Josh, 2026-11-03): minimize the largest
request shortfall percentage, equivalently maximize the minimum fulfillment
percentage, within the comparison population above. Record why each request is
included/excluded. Usable supply must support a positive feasible allocation under
the instrument's minimum/increment rules; a graph edge alone is insufficient.
Zero-demand, unknown/ineligible and proven-unfillable requests are outside this
metric but remain in coverage/blocker outputs. An empty comparison population
has an unavailable/not-applicable balance metric, not a fabricated perfect score.

This is one worst-percentage stage, not a claim of recursive max-min fairness
across every request. Declared later stages resolve remaining ties. The synthetic
coverage-then-balance example has 100,000 and 50,000 fully compatible share demand
and 75,000 supply: both reach 50% fulfillment (50,000 and 25,000). Test unequal
compatibility, discrete bond minimums, excluded requests, empty populations and
constraint-preserving ties independently. The default coverage/FIFO profile is
unchanged; a balance profile has its own declared objective ordering.

Confirmed composition policy (Josh, 2026-11-03): support **lexicographic** stages
(preserve earlier optima) and explicit **weighted** sums within declared stages
(allow reviewed tradeoffs). The default stays coverage → FIFO → canonical ties;
enabling weighted support does not silently change that profile. Weighted profiles
require versioned coefficients, term units/scales, normalization and documented
tradeoffs. They never soften eligibility, capacity or quantity constraints.
Use exact objective locks for the initial integer coverage/FIFO stages. Any later
continuous monetary/balance stage needs declared numerical tolerances and retained
stage bounds; do not silently degrade earlier objectives. Never mix raw currency,
shares and preference points by assigning arbitrary large weights. Weighted terms
need declared scaling and conversion to a common score, or separate stages.
Test both composition modes on the same hard-constraint fixture, show raw and
weighted components separately, and reject invalid/nonfinite weights or undefined
scales. A weighted preference score cannot be labeled money or strict priority.

The complete design-time configuration is
[settings.example.toml](settings.example.toml); its runtime parser is not
implemented. This excerpt uses the same version-1 structure:

```toml
schema_version = 1
default_profile = "coverage_first"

[solver]
adapter = "scipy_highs_milp"
require_all_stages_proven = true

[profiles.coverage_first]
policy_id = "coverage-first-v1"
ordered_terms = ["total_shortfall", "fifo_shortfall", "canonical_allocation"]
```

FIFO and canonical terms expand into documented sequential variable/objective
locks; a single timestamp-weighted cost is not equivalent. Version and hash the
expanded model/policy and coefficient provenance. Reject unknown terms, invalid
weights, missing economic inputs, unsupported combinations and solver capability
mismatches before solving; never fall back silently to a different profile.

Use the selected SciPy/HiGHS MILP adapter for the first optimizer. Basic
capacity/demand and linear edge costs also have network-flow formulations;
minimum nonzero allocations, fixed allocation costs and broader side constraints
need an appropriate integer/activation-variable formulation. Keep the model and
objective policy independent of the adapter, with an explicit supported-feature
matrix. See [OR-Tools min-cost flow](https://developers.google.com/optimization/flow/mincostflow),
[multiobjective composition](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html)
and [SciPy MILP constraints/statuses](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
for implementation references.

Engine confirmed (SF-D-007): use an optional SciPy/HiGHS MILP adapter for this
Python pilot, with sequential solves/locks for objective stages. OR-Tools/SCIP is
not selected. Add a dedicated optimization extra during implementation and pin a
Python-3.11-compatible package/version after compatibility checks; this choice
does not add a mandatory dependency to existing fixture/report workflows. No
solver is installed by this documentation change. Keep contracts, fixtures and
independent validation usable without the optional optimizer extra. Benchmark
after implementation; no engine performance or successful solve is established
by these docs.

Define explicit stage tolerances and numeric-range checks; a solver success flag
alone does not establish the required objective proof. Independently verify
integer allocation quantities/capacities/increments, preserve exact integer
objective locks at declared scales and retain available objective bounds/gaps.
Any continuous balance/economic stage needs its declared precision/tolerance.
Set a finite overall optimization budget in TOML, shared across security groups
and sequential objective/tie-break solves; pass only the remaining budget into
each solve rather than resetting a full budget for every stage. Numeric limits
and the initial fixture budget are explicit implementation settings, not measured
performance claims.

Confirmed publication policy (Josh, 2026-11-03): independently validate exact
allocations and retain per-stage objective values,
status, runtime, solver version/settings and available bounds/gaps. Publish under
the initial policy only after all stages and canonical ties are proven and the
ledger validates; retain diagnostics and the prior pack on failure/time limits
or feasible-but-unproven results. An unfinished run may retain diagnostics but
cannot replace the complete report pack with provisional allocations. Missing
first-run output remains unavailable if no previous complete pack exists.
Test time limits at the first objective, between objectives and during canonical
tie-breaking, including a feasible incumbent whose required stages are unfinished.
Comparison runs share identical facts and hard
constraints and show coverage, request/borrower fill rates, shortfall, preference
scores and modeled earnings separately. A preference score is never displayed as
actual cost, and a synthetic benefit is never displayed as realized earnings.

## Earnings input method

Confirmed by Josh, 2026-11-03: consume **supplied net-benefit coefficients** per
potentially allocatable position/request pairing. Require quantity basis, currency,
common modeling horizon and versioned method/assumption provenance. Normalize the
provided coefficient to allocation units exactly; do not multiply duration again,
subtract included costs twice, replace missing benefits with zero, or remove
candidate edges to avoid missing economic inputs. Negative values are valid.
Coverage-only profiles do not require economic inputs. Detailed coefficient fields,
scaling and failure semantics are in
[contracts.md](contracts.md#supplied-net-benefit-coefficients). Fee calculators and
additional rate/valuation/currency models are deferred, rather than implied by
testing the allocation optimizer. SF-AC-017 supplies implementation evidence later.

## Output and reporting contracts

Use a distinct, explicitly synthetic pack and report identity. Proposed outputs:

| Output | Grain / reconciliation |
| --- | --- |
| `request_coverage` | Request/build: open demand, candidate capacity, proposed coverage, shortfall and unknown capacity; candidate capacity is non-additive across requests |
| `capacity_ledger` | Position/request/check-stage slice: quantities and mutually exclusive primary states; no duplicate debits |
| `rule_evaluations` | Evaluated subject/rule-version/input snapshot: outcome, all reasons, input references and freshness |
| `allocation_proposals` | Proposal/request/position/build: derived quantity and policy identity, clearly not a booked loan |
| `optimization_runs` / `objective_components` | Build/security/profile/stage: resolved policy and coefficient provenance, raw metric, preference/economic classification, scale/weight, stage value, solve status and available bound/gap; baseline/scenario differences use identical hard constraints |
| `recall_impacts` | Recall/known allocation/build: attributable outstanding quantity or explicit unknown, with path/input references |
| `explanation_steps` | Explanation/ordered step: controlled endpoints, source/rule IDs and dates, bounded depth/row count |
| `manifest` / schema | Input/configuration/objective/method/code identities, solver version/settings where used, three cutoffs, synthetic classification, file hashes, keys, counts and exclusions |

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

WP-01 is complete at design scope and WP-02A at its stated implementation scope.
WP-02B/C and later packages remain pending. Split implementation further if a slice would need
more than about five source/test files. Require actual retained evidence before
checking any acceptance row.

| Work | Deliverable / acceptance | Depends on | Verification |
| --- | --- | --- | --- |
| SF-WP-01 | Complete (design): selected policies, version-1 contracts, synthetic settings and requirement traces | User decisions and governing boundary | contracts.md/settings.example.toml; Markdown/TOML/reference/default-consistency checks; no runtime acceptance claimed |
| SF-WP-02 | In progress: WP-02A typed envelope/quantity/reference foundation complete; WP-02B business fixtures/adapters and WP-02C temporal selection pending | WP-01 | WP-02A evidence linked above; full adapter/selection scenarios still needed for SF-AC-003/004/015/016/017 |
| SF-WP-03 | Add capacity normalization and typed rule evaluation with explanation rows | WP-02 | Independent gross/net and four-state cases for both asset classes; SF-AC-001/003/005/015 |
| SF-WP-04 | Add typed policy/model contract, coverage-first optimizer, FIFO baseline and reconciled ledgers; split solver/profile adapters into bounded tasks | WP-03 | 180k/90k/10k fixture; joint allocation fills 100k versus greedy 60k; independent optima, exact quantity/increment/minimum constraints, canonical ties, profile validation and outcome statuses; SF-AC-001/002/013/014/015/017 |
| SF-WP-05 | Add explicit loan-allocation and recall investigation | WP-02 | 15k+5k attribution, unrelated same-security loan exclusion, returns/replay; SF-AC-004/006 |
| SF-WP-06 | Package and validate immutable outputs; integrate the three synthetic report views with inspectable policy/stage results | WP-04/05 | Keys/hashes, injected failure, source/filter/reset, normal/narrow and bounded-workload measurements; SF-AC-007/008/009/012/014 |
| SF-WP-07 | Optional restricted persistence/adapters and negative permission tests | WP-06 plus separate access/deployment authorization | Source contracts, roles, denied public-reader/API queries, export review; SF-AC-010 |
| SF-WP-08 | Later collateral enrichment and independently verified calculations | Contracts/evaluation plus separately reviewed inputs/scope | Agreement/valuation/rule/missing-input evidence; SF-AC-011 |

**WP-02 implementation slices** (review/test each before advancing):

| Slice | Deliverable | Focused evidence |
| --- | --- | --- |
| WP-02A | Complete: typed envelope/quantity/reference contracts and independent validators | 22 focused tests; unchanged pinned base fixture; full regression/lint results in the validation report |
| WP-02B | Deterministic fixture generator and JSON/CSV adapters | Identical normalized business facts, missing versus zero, keyed child tables, one authoritative representation |
| WP-02C | Three-cutoff selection and snapshot/event inclusion accounting | Precise/date-only boundaries, corrections, included versus new events, ambiguous facts withheld; no eligibility or optimizer claim |

Keep each slice to about five source/test files, splitting further if needed.
Use the proposed feature modules in this plan; copy the documented settings into
a runtime config only when the corresponding parser/validation is implemented.
Do not install SciPy just to complete WP-02's standard-library contract work.

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

Adapter equivalence covers normalized facts and downstream business results, not
equality of raw file hashes. Exercise quoted/escaped CSV fields, missing versus
zero values, exact numeric/timestamp parsing, nested-to-related-table mappings,
malformed records and simultaneous alternative representations. One format cannot
silently accept data that the shared contract rejects in the other.

For optimization, compare tiny cases with independent exhaustive enumeration or
another independently checked oracle. Cover the 100k-versus-60k allocation,
FIFO secondary priority, worst-shortfall balance, explicit weighted tradeoffs,
negative-benefit earnings choices, zero demand and structurally blocked requests.
Verify invalid/missing coefficient inputs fail before solve, solver capability
mismatches fail explicitly, exact hard constraints survive every profile, and
time limits/unproven stages cannot replace the prior pack. Test canonical output
under shuffled source order; sorted solver inputs alone are not evidence of it.

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

WP-01 is complete at design scope: selected policies and explicit synthetic
technical defaults are documented in the contracts/settings. WP-02A is implemented
and validated at its stated scope. **WP-02B is next**.
The exact optimization package/wheel lock and backend build identity are WP-04
implementation artifacts, not unresolved business choices. No solver is installed
and all feature acceptance rows remain pending.

Before WP-07, resolve real identifiers, source history/contracts, actual agreements,
roles/deployment and owners. Before WP-08, define margin/haircut, valuation/FX,
concentration/netting semantics and independent examples. Synthetic coefficients,
thresholds and priorities do not establish real operating policy or authorize
live integration.

Josh is the project review owner. Assign implementation and methodology reviewers
when accepting the work packages; name the separate real-source/security/legal
owners before any restricted integration. These drafts do not assign those
approvals or claim a completed implementation review.
