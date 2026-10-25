# T-001B source-reader scope validation

Date: 2026-10-25. This run validates the approved fixed read-only discovery surface for the local MacroMedallion/EcoMedallion asset.

Migration 008 granted the source reader USAGE and SELECT on existing objects in the audit, bronze, gold, meta, and silver schemas. It did not grant write permissions, future-object default privileges, or access to the public agent runtime tables.

The regenerated source catalog executed a zero-row read probe against every relation/view:

| Read-probe result | Count | Interpretation |
| --- | --- | --- |
| passed | 91 | Two supported live interfaces plus 89 readable, not-yet-onboarded economic-pipeline objects |
| not_authorized | 40 | 31 MarketAtlas-owned relations plus 9 deliberately excluded public agent tables |

The catalog now has fingerprint 709e2ebe613fe4b29deb657df7128bbebd3c3648f8da71c604820ee0f85448b7. No source rows were returned or retained; each probe was SELECT 1 with LIMIT 0 under the enforced read-only source role.

The 89 readable objects remain discovered_not_onboarded. They require an object-level owner, rights classification, grain/key, temporal semantics, and adapter contract before any data extraction or publication.
