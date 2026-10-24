# MarketAtlas source discovery — initial pass

Date: 2026-10-24. Scope: repository metadata, public documentation, and authorized read-only inspection of a local MacroMedallion PostgreSQL database. Credentials and connection coordinates remain only in the git-ignored `configs/local.toml`.

| Asset | Verified observation | Remaining decision or check |
| --- | --- | --- |
| MarketAtlas | [`thatquantguy44/MarketAtlas`](https://github.com/thatquantguy44/MarketAtlas) is the design-stage repository; this work starts from main commit `f57d3c9423326f38cc060a38474614ff10ae6c8e`. | Confirm pilot runtime, owners, and database scope. |
| EcoMedallion | [`thatquantguy44/EcoMedallion`](https://github.com/thatquantguy44/EcoMedallion) exists; inspected main commit `472a39f5fa5f47cac85efdb5aa7a88f8f4cf7b2d`. Its README documents a multi-source medallion pipeline, point-in-time outputs for vintage-enabled series, and SQLite, PostgreSQL, and Databricks backends. | Inspect approved source views and actual grains, identifiers, release/vintage fields, coverage, rights, and read-only role. A README is not an integration test. |
| MacroMedallion | An authorized local PostgreSQL database exists and was reached successfully. No separate repository was found by name in the connected GitHub search. | Confirm whether its code is EcoMedallion, a private repository, an alias, or a deployed derivative. |
| PostgreSQL | PostgreSQL 16.15 exposed six pre-existing user schemas and 100 relations/views. MarketAtlas now uses scoped NOLOGIN source, writer, and report roles plus dedicated `atlas` and `atlas_report` schemas. | Confirm operational login/secret management before a scheduled deployment. |
| Power BI | MarketAtlas specifies a report; EcoMedallion documents its own report plans. | Confirm authoring environment, gateway, refresh mode, and license. |

**Decision for this slice:** retain the independent synthetic fixture track and add a bounded database adapter. The verified adapter maps `meta.fred_series` to macro-series identities and `gold.fred_point_in_time` to versioned observations. Its required columns are present, and a configured three-series extraction produced 151 observation versions for 2024-01-01 through the 2026-10-24 cutoff. The source-row checksum was `0c467656df907de964ed732d41c0467e54c87015ada1445f9331fcde11bf65d2`. The generated extract remains local and ignored. T-001 and AC-001 remain pending because repository identity, rights, owners, and deployment decisions are unresolved.

## Verified database contract

| Object | Verified grain / key | MarketAtlas use | Limitation |
| --- | --- | --- | --- |
| `meta.fred_series` | Unique index on `series_id`; metadata includes title, category, frequency, units, active/vintage flags, load type, and update time | Macro-series identity and observation metadata | Most fields are nullable text; domain validation is still required |
| `silver.fred_observation` | Unique index on `(source, series_id, observation_date, realtime_start)` | Underlying version history and run provenance | No declared primary/foreign keys were found for this object |
| `gold.fred_point_in_time` | View over `silver.fred_observation`, one observation vintage per series/date/real-time start | Approved adapter read interface | Real-time availability is date precision, not an exact release timestamp |
| `audit.etl_run` / `audit.etl_series_run` | Run and series-run records with unique run index on `audit.etl_run.run_id` | Candidate input/run lineage | Not yet joined into the bounded adapter extract |

The local login principal is an administrative bootstrap credential, but application sessions immediately switch roles. `marketatlas_source_reader` can SELECT only the approved `meta.fred_series` and `gold.fred_point_in_time` interfaces, cannot write upstream, and cannot create in `atlas`. `marketatlas_writer` can write `atlas` but cannot access upstream objects. `marketatlas_report_reader` can read graph tables but cannot write them or create serving objects. The source session additionally enforces read-only transactions, and its negative write probe was rejected. Full NFR-001 / AC-013 remains partial pending release-wide public-artifact review and deployment credential handling.

FRED `realtime_start` and `realtime_end` provide usable vintage intervals, and the sampled records showed multiple revisions. The adapter preserves `realtime_end` as an inclusive source field and labels availability precision as `date`; it does not invent an intraday release timestamp. Redistribution status remains unresolved, so upstream extracts must not be committed or published.
