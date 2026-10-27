# Synthetic securities-finance extension contract

Status: design contract for a future synthetic demonstration. No restricted
client, agreement, loan, or collateral data is implemented or authorized in
the current MarketAtlas database.

## Boundary and reuse

The extension reuses an existing public MarketAtlas **instrument** only by its
stable `atlas.node.node_id`. It must not copy a client name, account, agreement
term, position, collateral balance, or eligibility result into `atlas_report`
or the public fixture publication. Existing instrument, issuer, country,
currency, macro-context, correlation, and provenance grains remain unchanged.

```text
atlas / atlas_report (market facts, public or synthetic fixture)
                 ^ stable instrument node_id only
                 |
restricted deployment (client, agreement, loan, collateral, rule evaluation)
```

The restricted deployment may be a separately authorized database or a
separate `atlas_restricted` schema. It is intentionally not proposed as an
extension of the source-reader role or a browser API.

## Controlled restricted objects

| Object | Grain | Required references and temporal fields |
| --- | --- | --- |
| `client` | one authorized legal client identity | restricted client key; recorded interval |
| `legal_entity` | one borrower/lender/custodian entity | client key, role, effective and recorded intervals |
| `agreement` | one legal agreement version | parties, agreement type, effective and recorded intervals |
| `loan` | one loan/position version | agreement, borrowed instrument node ID, quantity/unit, lifecycle status, effective and recorded intervals |
| `collateral_asset` | one pledged asset version | agreement, collateral instrument node ID where applicable, valuation basis/currency/time |
| `collateral_allocation` | one allocation version | loan, collateral asset, amount/haircut, effective and recorded intervals |
| `eligibility_rule` | one versioned rule | agreement scope, priority, effective/recorded interval, rule expression reference |
| `eligibility_evaluation` | one evaluated rule result | allocation/rule/input snapshot, evaluation time, `eligible`/`ineligible`/`unknown`/`not_evaluated`, reason codes |

`loan.borrowed_instrument_node_id` and
`collateral_asset.instrument_node_id` must reference a canonical instrument of
the approved type. A missing or unmapped instrument is an explicit quarantine
or `unknown` state, never a fabricated public node. Each restricted version
keeps business-effective, source-available where supported, and recorded
intervals; it does not overwrite a prior agreement or collateral fact.

## Permission model

- A restricted writer may write only the restricted deployment after its own
  contract and validation gates pass.
- A restricted reader may read restricted objects needed for an authorized
  evaluation. It receives no source-schema write permission.
- `marketatlas_report_reader`, the browser report API, and public fixture
  builds have **no grants** on restricted objects.
- Cross-boundary reporting is allowed only through a separately reviewed,
  sanitized publication that contains no client or agreement identifiers and
  declares its aggregate grain, minimum-cell policy, and approved audience.
- A real client/trade deployment requires named data, legal, security, and
  report owners before migration or access grants. The current project has no
  such authorization.

## Eligibility semantics

A graph path is an explanation aid, not proof of collateral eligibility. A
published `eligibility_evaluation` needs its rule version, all required input
facts, valuation time, haircuts/concentration or limit checks when applicable,
and an explicit unknown/not-evaluated state. The renderer must show reason
codes and input freshness; it must not infer eligibility merely because an
agreement links a loan and collateral asset.

## Synthetic demonstration and acceptance

The first extension demo should use invented parties, agreements, loans,
collateral, and rule inputs, while referencing existing synthetic fixture
instrument IDs. It should prove: type-safe instrument links, versioned rule
evaluation, an `unknown` case, a rejected cross-boundary browser/report query,
and that public MarketAtlas report outputs are unchanged. This design satisfies
the extension-design portion of AC-012; implementing a restricted deployment
requires a separately approved task and security review.
