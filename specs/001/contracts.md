# 001 — File-first contracts and synthetic settings

Status: WP-01 design baseline, 2026-11-03; parsers, fixtures, solver and commands
are not implemented. Implements the choices in the
[decision register](plan.md#wp-01-decision-register), under the
[specification](spec.md) and parent isolation contract. The values in
[settings.example.toml](settings.example.toml) are explicit synthetic engineering
defaults, not assumed real-source terms or measured performance.

## Version and authority

Use `schema_version = 1`. Reject unknown fields/versions and unsupported policy
terms rather than guessing. Each logical dataset selects exactly one authoritative
JSON or CSV representation; the other may be used for equivalence verification.
Never concatenate equivalent representations as additional supply/demand/events.
Relationships refer to stable keys, not row order, ticker or display label.

Manifest fields: `schema_version`, `manifest_id`, `classification = synthetic`,
`datasets`, `instrument_catalog`, `cutoffs`, `settings_file` and its SHA-256.
Each dataset entry declares `dataset_id`, `record_type`, `schema_version`,
`source_name`, `snapshot_id` or `event_stream_id`, `selected_format`, and files
with relative `path`, `format` and `sha256`. JSON/CSV alternatives share a
`logical_dataset_id` and explicit selected representation. Reject path traversal,
duplicate selected representations, file hash mismatch and conflicting identities.
All three cutoffs are explicit timezone-aware instants; never use the wall clock
as an implicit replay cutoff.

## Encoding and exact values

- JSON: UTF-8, one array of objects per record table; reject duplicate object keys
  and nonfinite numbers. Quantity, money, weights and scales are decimal strings,
  not binary floating-point literals. JSON `null` means unavailable, never zero.
- CSV: UTF-8, header required, comma delimiter, double-quote quoting with doubled
  embedded quotes, LF output, and exact declared header names. Numeric fields
  use the same decimal text as JSON. Reserved `\N` means null; an empty string
  stays an empty string and is invalid for a required numeric/ID field. Literal
  `\N` is unsupported in version 1 rather than ambiguously escaped. IDs and
  quantities are not whitespace-trimmed or converted through spreadsheet types.
- JSON booleans and CSV `true`/`false` normalize to booleans; dates use
  `YYYY-MM-DD`. Timed values carry an offset or `Z`. Reject naïve timed values.
- Repeated/nested facts use keyed child tables in both formats, including
  `agreement_parties`, `agreement_instruments`, `agreement_locations` and
  `snapshot_included_events`. No lists disappear into ad hoc CSV strings.
- Normalize decimal text before semantic hashing without losing declared unit or
  precision. Preserve original file hashes and source row references separately.
  Equivalent accepted inputs have equal normalized facts; malformed, missing and
  conflicting data must receive equivalent treatment through both adapters.

## Common record envelope and grains

Every versioned source record has `source_name`, `record_id`, `version_id`,
`effective_from`, `effective_to`, `source_available_at`, `source_confirmed_at`,
`recorded_from`, `recorded_to`, and `source_record_reference`. A null end is an
open interval; selection uses half-open intervals. A missing required start or
evidence time cannot be replaced with capture time. Field-specific applicability
is explicit: immutable catalog rows use catalog provenance, and lifecycle events
use `effective_at` instead of an effective interval.

For each evidence time, represent `value`, `precision` (`instant` or `date`) and
`source_timezone` as separate flattened columns, e.g. `source_available_at_value`.
Date precision needs source calendar/timezone context to resolve a day interval.
System record times are precise instants. Use child tables for relations below;
child keys include parent `version_id`, preserving the parent's time/provenance.

| Table / grain | Additional required fields |
| --- | --- |
| `instrument_catalog`: instrument | `instrument_node_id`, `canonical_key`, `node_type`, `asset_class`, `label`, `provenance_reference` |
| `quantity_convention`: instrument/convention version | `convention_id`, `instrument_node_id`, `quantity_unit`, `quantity_currency`, `quantity_precision`, `minimum_allocation`, `allocation_increment`, `increment_origin`, `minimum_scope` |
| `legal_entity`: party version | `party_id`, `label`, `role` |
| `account`: account version | `account_id`, `owner_party_id`, `lender_party_id`, `custodian_party_id` |
| `inventory_position`: authoritative position version | `position_id`, `account_id`, `instrument_node_id`, `location_id`, `convention_id`, `quantity`, `balance_basis`, `deduction_contract_id`, `settlement_state`, `ready_date`, `snapshot_id` |
| `deduction_contract`: source balance definition | `deduction_contract_id`, `balance_basis`, `reservations_already_deducted`, `encumbrances_already_deducted`, `outstanding_loans_already_deducted`, `definition_reference` |
| `capacity_component`: identified component version | `component_id`, `position_id`, `kind`, `quantity`, `status`, `overlap_group_id`, `snapshot_id` |
| `borrow_request`: open request version | `request_id`, `borrower_party_id`, `instrument_node_id`, `location_id`, `convention_id`, `open_quantity`, `required_date`, `request_order_at`, `priority_tier`, `agreement_id`, `input_kind = open_request`, `snapshot_id` |
| `agreement`: agreement version | `agreement_id`, `status`, `business_valid_from`, `business_valid_to`, `permission_reference`, `snapshot_id` |
| `agreement_parties`: agreement-version/party/role | `agreement_version_id`, `party_id`, `role`, `permission_state` |
| `agreement_instruments`: agreement-version/instrument | `agreement_version_id`, `instrument_node_id`, `permission_state` |
| `agreement_locations`: agreement-version/location | `agreement_version_id`, `location_id`, `permission_state` |
| `loan`: outstanding loan version | `loan_id`, `agreement_id`, `instrument_node_id`, `convention_id`, `outstanding_quantity`, `status`, `input_kind = outstanding_loan`, `snapshot_id` |
| `loan_allocation`: owner-position/known-loan attribution version | `allocation_id`, `loan_id`, `position_id`, `outstanding_quantity`, `snapshot_id` |
| `lifecycle_event`: identified event version | `event_id`, `event_stream_id`, `event_type`, `state_component`, `target_record_id`, `quantity`, `status`, `effective_at`, `supersedes_version_id`, `reverses_event_id` |
| `snapshot_included_events`: snapshot/component/included-event version | `snapshot_id`, `state_component`, `target_record_id`, `source_name`, `event_id`, `event_version_id` |
| `net_benefit`: proposed position/request pairing and horizon version | `coefficient_id`, `position_id`, `request_id`, `convention_id`, `net_benefit_amount`, `basis_quantity`, `currency`, `horizon_id`, `horizon_start`, `horizon_end`, `method_version`, `assumption_reference` |

Record keys are `(source_name, record_type, record_id, version_id)`; referenced
business IDs must be source-qualified or resolved through an explicit source
mapping. Required columns/keys must be present even when their value is null to
represent unavailable evidence. Nullability never makes a missing fact eligible.
Baseline enums are `asset_class = equity|fixed_income`,
`balance_basis = gross|net_available`, `permission_state = permitted|denied`
(nullable for unknown), `settlement_state = settled|pending|failed`, agreement
`status = active|inactive`, and `capacity_component.kind = reservation|encumbrance|on_loan`.
Other lifecycle statuses/types are selected typed transitions, not arbitrary
expressions. Quantity and unit fields on components/events inherit and validate
the referenced position/loan convention, rather than defaulting a missing unit.

Rules live in versioned TOML configuration, not executable expressions from data:
`rules.version` plus the required typed check IDs below. The source tables supply
facts and references; evaluations retain resolved rule version/parameters and each
input reference. New vocabulary needs a schema/method version and tests.

Foreign keys resolve within the selected retained input set. Missing permission
facts are unknown, not implied permission; a missing optional custodian is null.
`permission_state` is an explicit synthetic fact, not a legal-prose interpretation
or a separate configurable block-list engine. Required-input absence remains
inspectable. Unknown fields, malformed values, conflicting duplicate keys and
broken identity/unit references are validation failures; selected valid facts may
still produce an unknown rule outcome when required evidence is unavailable.

## Canonical instrument fixture boundary

The current base fixture contains `I-A`, `I-B`, `I-C` share instruments. Reuse their
identity and meaning unchanged. WP-02 must additionally declare isolated synthetic
bond reference records `SF-BOND-A` and `SF-BOND-B` in this feature's file catalog,
using the existing `graph.fixture_loader.stable_id("node", source_id)` identity
contract and `node_type = instrument`. Their `asset_class = fixed_income` is an
explicit invented fixture fact. They are not asserted existing database rows.

This catalog is separate from `fixtures.build_fixture()` and public publications;
do not relabel existing shares, alter existing fixture outputs or write nodes to
repair an unmapped input. The feature's generator creates declared known bond
fixtures; the adapter only validates references. Later database integration must
resolve actual existing canonical instrument rows under its separate gate.

## Quantity and capacity semantics

The example settings declare whole-share equities and two USD nominal bond
conventions. Minimums apply to each proposed position/request allocation edge.
For bonds, `increment_origin = minimum` permits zero or `minimum + k*increment`
for nonnegative integer `k`. A different origin or aggregate-ticket minimum is an
unsupported version-1 convention, not silently translated. Existing balances and
partial returns need exact precision but need not meet a *new proposal's* minimum
or increment; retain residual quantities and explain unallocatable remainders.

For an edge with cap `U`, use exact scaled quantity units. With minimum `m` and
increment `s`, a bounded formulation is `x = m*y + s*k`, binary `y`, integer
`k >= 0`, and `k <= floor((U-m)/s)*y` when `U >= m`; otherwise force `x = 0`.
Recheck all quantities against the original exact contracts after solving.
Equities use ordinary nonnegative integer share quantities. No arbitrary rounding
can turn an infeasible fractional solution into an accepted allocation.

Gross normalization subtracts only disjoint authoritative components. Already-net
normalization uses the declared net baseline and does not re-subtract included
components. Alternative gross/net fixtures are representations of the same
position, not additive holdings. Missing balance definitions or unresolved overlap
withhold affected capacity. Never reconstruct an unsupported gross breakdown from
net alone. Shared quantity headroom is scoped to the same instrument/unit/currency;
version 1 does not couple independent groups through cross-security limits.

## Time, events and freshness

Normalize offset-aware instants to UTC, preserving precision/context. Date-only
timestamp evidence denotes the supported source-day interval, not a known instant.
Only establish inclusion or freshness if the entire supported interval satisfies
the check. Otherwise retain unknown. Equal known request instants use request ID;
overlapping uncertain times are not equal known instants. If order could affect
allocation, withhold affected proposals and preserve the previous complete pack.
Conservatively withhold unless order-independence is actually established.

Use business-effective cutoff for state validity, knowledge cutoff for source
availability, and system cutoff for record-version selection. The synthetic
freshness reference is the **knowledge cutoff**, using `source_confirmed_at`;
the maximum age comparison is inclusive. Require confirmation not later than the
reference and age not greater than the dataset's configured maximum. Do not use
file modification, ingestion or agreement document age as confirmation. Agreement
business-validity dates are separate business-date fields, not date-only source
timestamp substitutes. Retain all failed and missing/stale checks.

For version 1, snapshot inclusion uses explicit event/version IDs, not inferred
timestamp watermarks. Initial selected events are reservation create/release,
recall issue/cancel, and return settle/reverse. Each identifies the affected
reservation, recall or known loan allocation. Apply not-already-included supported
effects once; reversals reference retained original effects. Ambiguous inclusion,
late corrections or attribution cannot create capacity/known impact. Returns
may reduce explicitly attributable outstanding allocations; free inventory still
needs an authoritative balance/settlement fact. Selected event coverage is not a
complete-history claim.

## Rule and objective contracts

Required typed checks: active agreement, party/account permission,
instrument compatibility, location compatibility, settlement readiness and source
freshness. Settlement uses explicit `settlement_state`/`ready_date` against the
request's `required_date`, without inventing a market holiday calendar. Missing
required facts yield unknown, known failures remain visible, and only all-pass
required checks clear candidate supply. Quantity/headroom constraints remain hard.

Example profiles in the settings are synthetic, separately versioned policies:
coverage first; priority-tier service; coverage then worst-percentage balance;
earnings first; and an explicit weighted preference blend. They share hard facts
and constraints. Priority tiers 1/2/3 are invented fixture labels, with 1 first;
they are not an inferred borrower ranking. FIFO is within declared remaining ties.
Alternative orders/weights require a new resolved policy identity, never a silent
change to the selected default.

For balance, use positive-demand requests with provably positive feasible supply
under hard rules/quantity constraints in the security/unit group. Minimize `z`
subject to `u[j] <= z*d[j]`. Preserve every excluded request's shortfall/reason.
Empty populations have an unavailable metric. This single stage does not promise
recursive fairness or exact pro rata under incompatible constraints.

## Supplied net-benefit coefficients

The first earnings profile **consumes supplied modeled net-benefit coefficients**;
it does not compute fees, rates, rebates, valuations, FX or duration effects.
For each potentially allocatable position/request pairing, provide a finite signed
decimal `net_benefit_amount` per positive `basis_quantity`, matching that pairing's
quantity convention, plus currency, a common declared horizon, method version and
assumption/source references. The amount is already net of its declared modeled
costs for that horizon. Do not charge those costs again or multiply by duration a
second time. Expected benefit is `x * net_benefit_amount / basis_quantity`.

The initial examples use USD and one common synthetic 30-day horizon. Reject
mixed currencies/horizons or missing coefficients for a requested earnings/blend
profile; do not drop inconvenient candidate edges or invent zero benefits. Negative
coefficients are valid modeled losses. Coverage-only profiles do not require money
inputs. Preference points never substitute for money, and provided figures never
become claims of realized earnings.

Represent per-unit coefficients on the declared micro-currency objective scale;
reject nonrepresentable coefficients rather than silently rounding. Store the
original amount/basis and exact scaled conversion. A future fee calculator needs
its own method/input contract and acceptance evidence; it is outside WP-04.

## Numerical, publication and replay contract

The optional optimizer uses SciPy/HiGHS MILP with sequential solves and explicit
earlier-objective locks. Select a Python-compatible exact package/wheel lock in
WP-04; preserve SciPy/backend build identity and settings with validation evidence.
Contracts/fixtures/validation remain standard-library usable. The example's
60-second total optimization budget is shared across groups, objectives and final
ties; it is a configurable cap, not a promise the workload finishes in 60 seconds.
No silent greedy fallback or partial/provisional report publication is allowed.

Use zero requested relative MIP gap for required optimum stages. Recompute integer
objective values and constraint checks exactly; verify finite bounds/gaps consistent
with the required optimum, not just a success flag. Numeric-range and near-integer
checks may canonicalize floating representation noise only if every original exact
constraint still passes; they cannot repair a truly fractional solution. Continuous
balance/scaled-score stages use the declared absolute proof tolerance. "Proven"
means solver optimality/bounds satisfying this recorded numerical policy plus
independent exact allocation validation, not a formal exact-arithmetic certificate.

Publish only after every configured stage and canonical tie-break passes. Failures,
ambiguous consequential FIFO order and unfinished solves retain diagnostics and
the prior complete pack; a failed first run has no complete pack to serve.
Canonical allocation ties lexicographically minimize edge quantities by
`(position_id, request_id)` after locking earlier objectives. IDs use ordinal
string ordering, not locale-dependent sorting.

Separate identities: raw source hashes/provenance identify the physical input;
normalized semantic hashes and resolved schema/settings/cutoffs/method/code identify
business results. Runtime, invocation ID and operational solver traces belong to
the run envelope, outside the deterministic business digest. Hash and validate
every physical artifact independently. JSON/CSV equivalents may have different
raw manifest/artifact identities while producing the same business identity.

## Requirement trace and WP-02 entry

| Contract area | Requirement / future acceptance evidence |
| --- | --- |
| Envelopes, grains, encodings and identity | SF-FR-001/002/003/014; SF-AC-003/004/016 |
| Unit conventions, capacity and boundaries | SF-FR-004/006/007; SF-AC-001/002/015 |
| Time, events, required checks and freshness | SF-FR-003/005/008; SF-AC-004/005/006 |
| Profiles, coefficients and proof | SF-FR-006/010/013/015; SF-AC-013/014/017 |
| Reports, replay and isolated delivery | SF-FR-009/010/011; SF-AC-007/008/009/012 |
| Restricted persistence and collateral | SF-FR-011/012; SF-AC-010/011 remain separate gates |

WP-01 is complete at design scope with these explicit defaults. WP-02 implements
the contracts, both fixture encodings, reference catalog and cutoff selection;
WP-03 implements eligibility/balances, WP-04 the optimizer and profiles, and WP-05
recall calculations. No implementation acceptance row is passed by this document.
