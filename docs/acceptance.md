# MarketAtlas — Acceptance Evidence Register

Status: implementation evidence is in progress. AC-003 passes for the fixture track; several checks are partial and the rest remain pending. A task checkbox or planning review does not satisfy an acceptance criterion.

| Acceptance | Requirement | Status | Evidence artifact / run / commit | Reviewer and date |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | Pending | Not yet produced | Unassigned |
| AC-002 | REQ-002 | Pending | Not yet produced | Unassigned |
| AC-003 | REQ-003 | Passed (fixture) | `reports/t005-validation.md`: stable UUID reload, ticker history, overlap rejection | Implementation agent, 2026-10-24 |
| AC-004 | REQ-004 | Passed (fixture) | `reports/t006-validation.md`: bounded path, endpoint rules, disputed/retracted state handling, and invalid-type rejection pass | Implementation agent, 2026-10-24 |
| AC-005 | REQ-005 | Passed (fixture) | `reports/t006-validation.md`: source availability and MarketAtlas record-time replay differ as expected; unsupported history is explicit | Implementation agent, 2026-10-24 |
| AC-006 | REQ-006 | Passed (fixture) | `reports/t007-validation.md`: market/macro version contracts, macro-vintage cutoff selection, adjustment-history labeling, and input-manifest reproduction | Implementation agent, 2026-10-24 |
| AC-007 | REQ-007 | Passed (fixture) | `reports/t008-validation.md`: source-backed country/concept and curated sector context mappings have rationale, owner, source, dates, taxonomy version, and explicit non-sensitivity label | Implementation agent, 2026-10-24 |
| AC-008 | REQ-008 | Passed (fixture) | `reports/t009-validation.md`: fixed-window configured-pair return correlations, independent numerical match, undefined statuses, input/cutoff metadata, and no-lookahead validation | Implementation agent, 2026-10-24 |
| AC-009 | REQ-009 | Partial | `reports/t011-validation.md`, `docs/reporting.md`, `reports/t012-validation.md`: snapshot-pinned reporting outputs and React fixture demo pass; Power BI implementation remains required | Implementation agent, 2026-10-24 |
| AC-010 | REQ-010 | Passed (fixture) | `reports/t010-validation.md`: immutable build/snapshot identities, idempotent output reuse, validation hash, and single-pointer publication | Implementation agent, 2026-10-24 |
| AC-011 | REQ-011 | Passed (fixture) | `reports/t011-validation.md`: sourced relationship, curated context, and correlation each drill through to snapshot, build/input, and source/method evidence | Implementation agent, 2026-10-24 |
| AC-012 | REQ-012 | Pending | Not yet produced | Unassigned |
| AC-013 | NFR-001 | Partial | `reports/t005-validation.md`: source/writer/report role boundaries and negative write probe pass; release artifact review remains | Implementation agent, 2026-10-24 |
| AC-014 | NFR-002 | Partial | `reports/t007-validation.md`, `reports/t009-validation.md`, `reports/t010-validation.md`: fixture input, correlation configuration/input, code revision/environment, and output hash are recorded; broader environment/recovery reproducibility remains | Implementation agent, 2026-10-24 |
| AC-015 | NFR-003 | Partial | `reports/t005-validation.md`, `reports/t006-validation.md`, `reports/t007-validation.md`, `reports/t008-validation.md`, `reports/t009-validation.md`, `reports/t010-validation.md`, `reports/t011-validation.md`: graph, temporal, observation, context, analytical, serving-snapshot, and reporting-grain guards pass; broader release checks remain | Implementation agent, 2026-10-24 |
| AC-016 | NFR-004 | Pending | Not yet produced | Unassigned |
| AC-017 | NFR-005 | Passed (fixture) | `reports/t010-validation.md`: injected failed build remains un-published with zero snapshot rows; the last complete snapshot remains the sole reader view | Implementation agent, 2026-10-24 |
| AC-018 | NFR-006 | Pending | Not yet produced | Unassigned |

Attach reproducible output locations, input hashes, method/configuration versions, declared environment, and concise results as appropriate. Restricted data and environment details must stay in their authorized location; public summaries should use synthetic examples and safe identifiers. Record failed and unsupported checks honestly.
