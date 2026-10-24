# MarketAtlas — Review and Traceability

## Review scope and status

Reviewed the complete original `market_knowledge_graph_spec.md` and reorganized its content into a focused specification, candidate architecture, actionable tasks, handoff, and milestone roadmap. The package is documentation, with all implementation acceptance evidence pending. Repository contents, PostgreSQL access/schema, source rights, and Power BI capabilities remain unverified.

## Material changes from the original

| Original gap | Resolution | Location |
| --- | --- | --- |
| Purpose, design, tasks, and future ideas were mixed together | Product requirements define WHAT/WHY; the plan defines HOW; task evidence and the roadmap carry execution scope | spec.md, plan.md, tasks.md, roadmap.md |
| MacroMedallion / EcoMedallion reuse was broad and assumed two repositories | Discovery resolves exact identity, interfaces, commits, source ownership, permissions, and reusable components | REQ-001; handoff.md |
| Public GitHub demo would depend on private source systems | Independent deterministic fixtures; real upstream access is optional and reported honestly | REQ-002; NFR-001 |
| Relationship targets referenced indices/concepts without defining their entity types | Explicit node types and allowed endpoint pairs; instrument/listing identity distinction | REQ-003–004; plan.md |
| Effective dates alone could not reproduce what was known earlier | Business validity, source availability, system record history, and revisions have explicit semantics | REQ-005–006 |
| Statistical edges could invite price-level or mixed-frequency correlations | v0.1 uses bounded, configured comparable instrument-return pairs; macro series provide curated context | REQ-007–008 |
| Flat one-row-per-instrument output could multiply data through index/sector memberships | Explicit dimensions/facts/bridges and reporting grains; count reconciliation required | REQ-009; RISK-004 |
| Build and refresh failure behavior was underspecified | Immutable run input identity, idempotent business results, atomic serving snapshots, prior-good recovery | REQ-010; NFR-002, NFR-005 |
| Provenance was descriptive rather than demonstrable | Trace sourced, curated, and calculated examples to inputs, rules, method versions, and run | REQ-011 |
| Event studies, beta, and securities finance could expand the first release | Deferred to evidence-based milestones; synthetic domain extension contract retained in v0.1 | REQ-012; roadmap.md |
| Acceptance criteria had no stable IDs or retained evidence requirements | REQ/NFR/AC identifiers, task links, explicit future evidence, and pending status | spec.md; tasks.md |
| Portfolio presentation could overstate progress | README states design status; screenshots, working instructions, badges, and results follow implementation | README.md; RISK-007 |

## Original scope coverage

| Original content | New home |
| --- | --- |
| Purpose, thesis, scope, and user questions | spec.md |
| Nodes, edges, PostgreSQL model, repository integration | plan.md |
| Market entity map and macro/statistical PoCs | spec.md, plan.md, roadmap.md |
| Power BI front end and reporting outputs | plan.md, tasks.md |
| Quality, availability timing, access, and reproducibility | spec.md, plan.md, handoff.md |
| Success measures and acceptance | spec.md, tasks.md |
| Securities-finance extension | spec.md, roadmap.md |
| Sequence and open design decisions | tasks.md, handoff.md |

## Documentation quality checks

Documentation checks should verify file links, stable requirement/acceptance references, task dependencies, and complete requirement coverage before packaging. A passing documentation check does not mean a database migration, pipeline, quant estimate, report, or performance benchmark passed. Implementation evidence belongs to the corresponding acceptance records produced later.


## Requirement-to-delivery map

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

Implementation status has advanced since the original documentation review. The checked-in evidence register is [acceptance.md](acceptance.md), and T-005 evidence is retained in `reports/t005-validation.md`. The earlier `reports/documentation-checks.md` remains a historical record of the documentation-only review.
