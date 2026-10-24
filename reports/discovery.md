# MarketAtlas source discovery — initial pass

Date: 2026-10-24. Scope: repository metadata and public documentation only. No live database, source tables, credentials, or vendor data were accessed.

| Asset | Verified observation | Remaining decision or check |
| --- | --- | --- |
| MarketAtlas | [`thatquantguy44/MarketAtlas`](https://github.com/thatquantguy44/MarketAtlas) is the design-stage repository; this work starts from main commit `f57d3c9423326f38cc060a38474614ff10ae6c8e`. | Confirm pilot runtime, owners, and database scope. |
| EcoMedallion | [`thatquantguy44/EcoMedallion`](https://github.com/thatquantguy44/EcoMedallion) exists; inspected main commit `472a39f5fa5f47cac85efdb5aa7a88f8f4cf7b2d`. Its README documents a multi-source medallion pipeline, point-in-time outputs for vintage-enabled series, and SQLite, PostgreSQL, and Databricks backends. | Inspect approved source views and actual grains, identifiers, release/vintage fields, coverage, rights, and read-only role. A README is not an integration test. |
| MacroMedallion | No separate repository was found by name in the connected GitHub search. | Confirm whether this is an alias, prior name, or separate private asset. |
| PostgreSQL | The EcoMedallion README describes a PostgreSQL backend. | Verify target database/version, designated MarketAtlas schemas, migration policy, roles, and actual accessible objects. No connection was attempted. |
| Power BI | MarketAtlas specifies a report; EcoMedallion documents its own report plans. | Confirm authoring environment, gateway, refresh mode, and license. |

**Decision for this slice:** use an independent, synthetic fixture track. No repository-specific import path, database table, real-data mapping, or live source adapter is assumed. The fixture is generated and validated locally without upstream credentials. T-001 and AC-001 remain pending because source contracts, rights, and owner decisions are unresolved.

Potential reuse to inspect next: EcoMedallion's Gold point-in-time output and normalized series metadata. These are candidates only; MarketAtlas must verify their actual table contracts and availability semantics before linking them to historical graph questions.
