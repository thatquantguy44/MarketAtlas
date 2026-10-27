# MarketAtlas — Implementation Plan

Status: active design for the v0.1 specification, 2026-10-26. The fixture workflow, complete local source catalog, bounded live MacroMedallion/EcoMedallion macro ingestion, identity/ontology graph, temporal reference replay, versioned fixture observations, curated-context mappings, bounded rolling correlations, atomic fixture publication, snapshot-pinned reporting outputs, a React fixture demo, a separate current-only live macro-economic graph projection, and a contributor/design handoff exist. The graph now has a full approved-series catalog view with bounded category neighborhoods; it remains descriptive taxonomy rather than historical taxonomy or analytical evidence. Power BI remains proposed. This document does not assert specification approval or a release gate pass.

## Design overview

Use `thatquantguy44/MarketAtlas` as the project repository, with a portable fixture workflow and optional adapters to the user's verified MacroMedallion / EcoMedallion assets. Keep source access read-only. Use a dedicated PostgreSQL graph schema and a report schema to expose documented dimensions, facts, and bounded paths. Build only the market map, curated macro context, and rolling return correlations for v0.1.

Use ordinary relational tables for the graph. Stable entity IDs, controlled edge types, explicit timestamps, and versioned estimates are sufficient for the pilot questions. The design must work through SQL and standard Power BI visuals; a network visual is optional.

## P1. Discovery and integration contracts

Treat MacroMedallion and EcoMedallion as interchangeable names for one local upstream asset. Let each operator optionally select its local checkout in git-ignored configuration; do not require a remote URL, commit, branch pin, or source-code import. Inventory the approved PostgreSQL objects, grains, primary keys, timestamps, source rights, and migration/runtime conventions. Record verified component reuse and unresolved gaps in `reports/discovery.md`; keep private infrastructure details outside public artifacts.

Define a common adapter interface before implementation. Each adapter supplies entities, identifier mappings, reference assertions, curated context, and observations plus a manifest of source identity, extraction time, rights, checksums, and coverage. A source may explicitly lack some outputs. Missing fields must remain missing or quarantined rather than fabricated.

The tracked `contracts/source_contracts.toml` registry is the promotion gate for
upstream objects. It records contract ownership, source-owner status, purpose,
grain/key, required schema fingerprints, temporal semantics, rights status,
lifecycle, and adapter. A fresh metadata-only source catalog must verify against
that registry before a `supported_live` adapter runs; readable but undeclared
objects remain non-ingestible.

Fixture mode supplies all contracts deterministically from labeled synthetic files. Upstream mode uses versioned database views or repository interfaces identified during discovery. Upstream adapters must not import guessed module paths or alter source schemas. Select existing migration and scheduling conventions where suitable; keep the public demo independent of private packages. (REQ-001, REQ-002, NFR-001, NFR-006)

## P2. Storage, identity, and ontology

Proposed schemas: `atlas` for graph/build objects and `atlas_report` for serving outputs. Their final names must be approved for the selected database. Observation payloads remain in governed sources when immutable, reproducible references are possible; otherwise capture permitted immutable inputs for each build. Do not duplicate all source history by default.

| Proposed object | Grain and key information |
| --- | --- |
| `node` | One stable identity per type/canonical key; internal ID never reused |
| `node_attribute_version` | Entity attributes per effective/knowledge history; changing label does not create a new identity |
| `node_identifier` | Source identifier mapped to entity over explicit intervals; ambiguous overlaps quarantined |
| `node_type`, `edge_type`, `edge_endpoint_rule` | Controlled type definitions and allowed ordered endpoint-type pairs |
| `reference_assertion` | One versioned sourced fact or curated mapping assertion, including rationale/source and temporal fields |
| `market_observation_version`, `macro_observation_version`, `input_manifest` | Implemented fixture contracts: one market or release/vintage version at declared grain, with a reproducible input hash |
| `curated_macro_context_version` | Implemented fixture context mapping with evidence basis, owner, source, taxonomy version, temporal fields, and a non-sensitivity semantic label |
| `rolling_correlation_estimate_version` | Implemented fixture estimate: canonical instrument pair, fixed session window, cutoff, method/configuration and input hashes, correlation or explicit undefined status |
| `build_run`, `input_manifest` | Implemented fixture run status, immutable input identity, configuration/code/environment capture, and validation outcome |
| `serving_snapshot`, `publication` | Implemented fixture snapshot identity, output hash, failure evidence, prior-snapshot retention, and one atomically selected publication |

Include instrument, listing, issuer, organization, index/basket, country, currency, sector/industry, economic concept, market, and macro-series types where pilot links use them. Do not equate an exchange listing with its underlying instrument. The same ticker on two venues must be resolvable without a collision.

Use stable canonical keys with unique constraints. Enforce edge endpoints with foreign keys and an allowed `(edge_type, from_type, to_type)` relation, using a composite constraint strategy or explicit validation with quarantine before publication. A generic string edge name without type enforcement is insufficient. Enforce single-valued facts only where the ontology declares that cardinality; multiple index memberships are valid.

Use distinct predicates or role fields for issuer domicile, listing-market country, denomination currency, and economic exposure. Listing location or denomination alone must not imply business exposure. Retain taxonomy provider and version for sector/index assignments.

Reference/curated assertions and analytical estimates have separate contracts. Store explicit provenance and classification of each relationship; an unknown mapping is not a sourced negative fact. (REQ-003, REQ-004, REQ-007, NFR-003)

## P3. Temporal and observation semantics

Use UTC timestamps and half-open intervals `[start, end)` with documented open ends. Preserve three distinct concepts:

- `valid_from/valid_to`: when the fact applies in the business domain.
- `available_at`: when the source information became usable, with supporting evidence or an unknown status.
- `recorded_from/recorded_to`: when MarketAtlas stored each assertion version.

Append corrections or retractions as new versions and close prior system intervals transactionally; retain their payloads. Query current context using current versions. Query historical source-available context only with supported availability/vintage history. Query what MarketAtlas actually knew using the additional record-time cutoff. Expose `effective_as_of`, `knowledge_cutoff`, and, for system replay, `system_cutoff` in the query contract. Bind these cutoffs to serving snapshot metadata; a Power BI date slicer cannot create historical state absent from that snapshot. Never substitute ingestion time for a missing source publication timestamp and call it historical source availability.

Market observation contracts include instrument/listing identity, measure/unit/currency, trading date/time, calendar, close convention, adjustment basis, source record, and availability cutoff. Macro contracts include reference period, frequency, units, release timestamp, vintage/revision identity, and extraction time. Select the release available by the calculation cutoff; a later revision cannot enter an earlier historical calculation. Mark latest-only history as descriptive and exclude unsupported historical inferences.

Retain the adjustment convention used to create returns. Versioned adjusted prices may incorporate future corporate actions; historical-as-known claims require an eligible input vintage or independently supported return construction. Preserve this limitation in serving output. (REQ-005, REQ-006, NFR-002)

## P4. Analytical method

v0.1 implements rolling Pearson correlation on a configured list of at most 300 eligible instrument-return pairs. Proposed sizing is 50 instruments, 25 contextual macro series, and two years of daily market history. This is a bounded pilot envelope, subject to discovery.

For each endpoint date, use the last **60 scheduled sessions** of the declared common calendar as the fixed window. Retain at least 45 valid paired return observations to publish an estimate. Missing observations reduce sample size; do not reach farther back to replace them. Returns require adjacent valid prices on the chosen session grid. Do not forward-fill missing prices or mix multi-session returns with one-session returns.

Default to simple adjusted-price returns `P(t)/P(t-1)-1` for comparable instruments with documented adjustment and close conventions. Other conventions require explicit configuration and method versioning. Keep asynchronous markets ineligible until a documented alignment rule exists. Low-frequency macro levels remain context; they do not enter this daily return-correlation family. Future macro sensitivity work requires compatible transformations and cadence.

Canonicalize undirected Pearson pairs by stable ID ordering and reject self-pairs or duplicates. Retain window boundaries, paired dates or their reproducible identity, sample count, input cutoff, method/configuration version, and estimate status. Use explicit `insufficient_sample`, `zero_variance`, `incompatible_input`, and `unsupported_history` statuses. Preserve missing/undefined results instead of converting them to zero. Numerical verification tolerance must be declared, proposed absolute tolerance `1e-10` on deterministic fixtures. (REQ-008, NFR-002, NFR-003)

## P5. Builds, publication, and provenance

A build reads a fixed adapter snapshot, validates inputs, resolves entities, writes versioned assertions and estimates, prepares serving outputs, and runs publication checks. Its manifest records input checksums/identities, seed, configuration hash, code revision, dependency lock/environment, method versions, cutoff, and output snapshot ID. If input retention rights prevent reproduction, record that limitation and do not claim full upstream reproducibility.

Write outputs under a new snapshot ID. Reject/quarantine invalid records with reasons and fail publication if required pilot coverage or integrity criteria are unmet. Publication changes one pointer in a transaction only after the snapshot is complete. Rerunning identical input/configuration preserves business identity and result equivalence; additional audit runs may exist without duplicate business facts.

Power BI refreshes must pin **one snapshot ID for every query in that refresh**. Capture the validated snapshot before refresh and use it as a fixed Power Query parameter/filter. Views include snapshot IDs; prohibit a refresh that independently resolves a changing publication pointer for each table. Retain the previous snapshot until all consumers have finished their pinned refreshes.

Every serving relationship exposes a provenance key linking to the assertion or analytical edge, source record/input snapshot, mapping/method version, temporal cutoff, quality results, and build. (REQ-010, REQ-011, NFR-002, NFR-005)

## P6. Power BI serving model

Propose Import mode for the small pilot, subject to the BI environment. SQL output validation and actual Power BI validation remain distinct acceptance steps.

| Output | Declared grain |
| --- | --- |
| Entity dimensions | One row per entity at serving snapshot; separate instrument/listing when needed |
| `fact_relationship` | One visible assertion/version per snapshot |
| `bridge_instrument_classification` | Instrument, classification type/member, assertion, snapshot; multiple memberships allowed |
| `bridge_macro_context` | One curated instrument/classification-to-series mapping per snapshot |
| `fact_observation` | Entity, measure, observation period/time, chosen vintage, snapshot |
| `fact_pair_estimate` | Canonical pair, method/window, endpoint date, snapshot |
| `dim_provenance` and quality output | Provenance or validation key per snapshot |
| Bounded path extract | Start node, path identity/step, endpoint, assertion, snapshot; configured depth/row caps |

Use role-playing dimensions for pair endpoints and explicit bridge filtering for multi-valued memberships. Keep observations and estimates at their own grains; do not flatten all memberships into a one-row-per-instrument observation view. Default to controlled single-direction relationships and deliberate selection measures. Instrument counts use distinct instrument IDs; pair measures operate at pair/date grain. Validate row totals before and after filters, including multi-classification fixtures.

Report pages: market map, macro context, correlation monitor, and provenance/quality drill-through. Show context versus estimates, as-of date, snapshot, freshness, status, and sample/window definitions. Use tables, slicers, matrices, and time series as the baseline; any approved network visual consumes a bounded extract. Report consumers should not need to understand physical table internals. The React demo will adopt the [QuantMeridian scaffold decision](decisions/001-quantmeridian-react-scaffold.md), while keeping MarketAtlas data/API contracts independent. (REQ-009, REQ-011)

## P7. Layout, validation, and delivery

| Proposed path | Responsibility |
| --- | --- |
| `src/market_atlas/adapters/` | Fixture and verified upstream contracts/adapters |
| `src/market_atlas/graph/` | Identity, ontology, temporal assertions, and bounded paths |
| `src/market_atlas/analytics/` | Return alignment and rolling correlation |
| `frontend/` | Independent QuantMeridian-style React fixture demo consuming the T-011 reporting contract |
| `src/market_atlas/pipeline/` | Build manifests, quality gates, publication, recovery |
| `sql/migrations/`, `sql/serving/` | Dedicated-schema DDL and grain-documented outputs |
| `config/`, `data/fixtures/` | Public non-secret configuration and synthetic inputs |
| `powerbi/` | Supported semantic/report source format and setup notes |
| `tests/`, `reports/` | Contract/temporal/numeric/integration validation and evidence |
| `docs/` | Specification chain, decisions, operating handoff |

Existing CLI workflow: `market-atlas fixture build|validate|inspect`, `market-atlas database inspect`, and `market-atlas adapter verify|extract`. The contributor walkthrough records the exercised fixture commands; the remaining `market-atlas demo`, `market-atlas build --adapter <name>`, `market-atlas validate --snapshot <id>`, and `market-atlas publish --snapshot <id>` forms are proposed downstream interfaces, not implemented commands.

Validate invalid endpoints, ticker reuse, late corrections, macro revisions, unavailable historical data, constant/missing series, clean-room fixture execution, idempotency, failure retention, provenance, and Power BI filter/grain behavior. Match numerical results against an independent hand-checkable calculation. For AC-016 record hardware, scale, query text, cache policy, build duration, and at least 20 runs per prepared query; target build under 5 minutes and query p95 at most 2 seconds. These are unmeasured proposed targets, not database or Power BI guarantees.

Log run/snapshot IDs, input coverage, quarantine counts, missingness, build duration, query times, and publication/failure state. Public logs contain no secrets or restricted rows. Domain extensions add new controlled types/adapters and restricted schemas without redefining existing edge semantics. (REQ-012, NFR-001, NFR-003, NFR-004, NFR-006)

## Failure Modes & Rollback

Bad contracts, missing permission, and unsupported histories fail with actionable status. Invalid records are quarantined; partial outputs are never published. A failed build leaves the prior serving pointer intact. Recovery disables the scheduled job, pins consumers to the prior complete snapshot, records the incident, and rebuilds after correction. Migrations are additive where practical; test rollback in an isolated schema and never roll back by modifying upstream objects. Retention cleanup cannot delete snapshots pinned by readers.

## Trade-offs

PostgreSQL relational edges keep the pilot close to the existing database and familiar SQL operations. A dedicated graph engine is deferred until measured traversal needs justify its operating cost. An all-purpose ontology and dense all-pairs estimation add scope without improving the first questions. Report-time recursive DAX traversal is rejected because precomputed bounded outputs make grain, performance, and access easier to verify. The synthetic demo is portable, while live-source accuracy remains a separately evidenced integration responsibility.

## Design principles and requirement coverage

Candidate design review: correctness uses constrained identities/types and explicit temporal/numeric contracts; reversibility uses isolated schemas and versioned publication; observability uses manifests/quality/run metrics; access and data controls use scoped roles and synthetic public artifacts. The QF Workflow SDK constitution and stage hook are not included in this package. No formal constitution-compliance or stage-gate execution is claimed.

| Requirement | Plan section | Delivery tasks | Acceptance |
| --- | --- | --- | --- |
| REQ-001 | P1 | T-001, T-004 | AC-001 |
| REQ-002 | P1, P7 | T-002, T-003, T-014 | AC-002 |
| REQ-003 | P2 | T-005 | AC-003 |
| REQ-004 | P2 | T-005, T-006 | AC-004 |
| REQ-005 | P3 | T-006, T-007 | AC-005 |
| REQ-006 | P3 | T-004, T-007 | AC-006 |
| REQ-007 | P2, P6 | T-008 | AC-007 |
| REQ-008 | P4 | T-009 | AC-008 |
| REQ-009 | P6 | T-011, T-012 | AC-009 |
| REQ-010 | P5 | T-010 | AC-010 |
| REQ-011 | P5, P6 | T-011, T-012 | AC-011 |
| REQ-012 | P7 | T-014 | AC-012 |
| NFR-001 | P1, P7 | T-002, T-004, T-013, T-014 | AC-013 |
| NFR-002 | P3–P5 | T-003, T-007, T-009, T-010, T-013 | AC-014 |
| NFR-003 | P2–P5, P7 | T-005, T-006, T-007, T-009, T-010, T-013 | AC-015 |
| NFR-004 | P7 | T-013 | AC-016 |
| NFR-005 | P5, Failure Modes & Rollback | T-010, T-013, T-014 | AC-017 |
| NFR-006 | P1, P7 | T-002, T-014 | AC-018 |

## Open Questions

Resolve exact upstream identities and schema compatibility; supported historical vintages/availability; eligible calendars and adjustment sources; retention/redistribution rights; Power BI authoring and refresh configuration; and actual owners/hardware. Record changes to pilot defaults before implementation and preserve requirement IDs when revising the design.
