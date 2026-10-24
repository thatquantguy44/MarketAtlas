# MarketAtlas

**A temporal market knowledge graph connecting instruments, macro data, and measurable relationships through PostgreSQL and Power BI.**

Status: early implementation. The deterministic fixture contract, bounded MacroMedallion PostgreSQL adapter, identity/ontology graph, temporal assertion replay, versioned synthetic observation loading, curated macro-context mappings, and bounded rolling correlations work. Serving publication and Power BI remain planned.

MarketAtlas gives market data a relationship layer. Start with a security, issuer, currency, country, index, or economic series; follow the links; inspect the source and the date each link was known. Compare those sourced relationships with time-bounded statistical estimates without treating correlation as causality.

The project consumes verified MacroMedallion PostgreSQL outputs through a small read-only adapter and will use dedicated PostgreSQL schemas for graph storage and reporting views. Repository identity, redistribution rights, and a least-privilege database role still require owner decisions.

## The first demonstration

A reviewer should be able to select a fixture instrument, follow its issuer and classifications, inspect the evidence for a macro context link, and examine how a rolling correlation changed across selected dates. Every statistical edge should show its transformation, sample size, window, and data cutoff.

| Question | Planned output |
| --- | --- |
| What connects this instrument to an issuer, sector, currency, or country? | A bounded relationship path with provenance |
| Why is a macro series shown alongside this market? | A sourced or explicitly curated context mapping |
| Has a relationship changed? | Rolling correlation estimates and quality diagnostics |
| Could this have been known at the time? | Effective dates, availability timestamps, and vintage information |

The portable demonstration will use clearly labeled synthetic fixtures. Authorized upstream integrations are optional. Real historical results require suitable data rights and verified availability/vintage history.

## Planned architecture

```mermaid
flowchart TD
    A["MacroMedallion / EcoMedallion"] --> C["Read-only source adapters"]
    B["Labeled synthetic fixtures"] --> D["Canonical entities and observations"]
    C --> D
    D --> E["PostgreSQL graph and analytical estimates"]
    E --> F["Power BI dimensions, facts, and bounded paths"]
```

Reference facts and calculated estimates have distinct semantics. PostgreSQL prepares the relationships and reporting outputs. Power BI presents filtered views, paths, and time series using explicit row grains.

## Working slices

The repository has a standard-library Python CLI for generating and validating deterministic **synthetic inputs**. It also has an optional PostgreSQL adapter for verified MacroMedallion series metadata and point-in-time observations, versioned fixture loading into the dedicated `atlas` schema, and a bounded rolling-correlation fixture calculator. It does not yet create a serving publication or Power BI report. Python 3.11 or newer is required.

```bash
PYTHONPATH=src python -m market_atlas fixture build --output /tmp/marketatlas-fixture
PYTHONPATH=src python -m market_atlas fixture validate --input /tmp/marketatlas-fixture
PYTHONPATH=src python -m market_atlas fixture inspect --knowledge-cutoff 2024-02-10T00:00:00Z
PYTHONPATH=src python -m unittest discover -s tests -v
```

For local PostgreSQL integration, copy `configs/local.example.toml` to the git-ignored `configs/local.toml`, fill in the connection values, install `requirements.lock`, and run:

```bash
PYTHONPATH=src python -m market_atlas database inspect --output data/generated/macro_medallion_schema.json
PYTHONPATH=src python -m market_atlas database migrate
PYTHONPATH=src python -m market_atlas database validate-roles
PYTHONPATH=src python -m market_atlas adapter verify
PYTHONPATH=src python -m market_atlas adapter extract --output data/generated/macro_medallion_pilot.json
PYTHONPATH=src python -m market_atlas graph validate-fixture
PYTHONPATH=src python -m market_atlas graph validate-temporal-fixture
PYTHONPATH=src python -m market_atlas graph validate-observation-fixture
PYTHONPATH=src python -m market_atlas graph validate-curated-context-fixture
PYTHONPATH=src python -m market_atlas analytics validate-fixture
```

Source connections force `default_transaction_read_only=on` and switch to the NOLOGIN `marketatlas_source_reader` role. Migrations switch to `marketatlas_writer`; report consumers use `marketatlas_report_reader`. Generated inspection and extract files are ignored. The migration never changes objects or permissions inside existing source schemas beyond granting the source role SELECT on the two approved interfaces.

The fixture manifest records record counts, a SHA-256 hash, and the explicit status `graph_and_report_not_built`. The database loader records a reproducible `input_manifest` for the same fixture hash and structured source-backed/curated context mappings. [Fixture contract](docs/fixtures.md) describes the grains and edge cases. [Source discovery](reports/discovery.md) records the verified PostgreSQL contract and remaining gaps. [Acceptance evidence](docs/acceptance.md) records fixture evidence and the remaining partial or pending checks.

## Delivery documents

Read in order:

1. [Specification](docs/spec.md): user questions, scope, requirements, and acceptance criteria.
2. [Implementation plan](docs/plan.md): architecture, contracts, build order, and requirement coverage.
3. [Tasks](docs/tasks.md): dependencies, owners, completion evidence, and acceptance mapping.
4. [Handoff](docs/handoff.md): current state, next action, integration questions, and operating expectations.
5. [Roadmap](docs/roadmap.md): capability milestones and the securities-finance extension.
6. [Review and traceability](docs/review.md): changes from the original spec and the requirement-to-task map.
7. [Acceptance evidence register](docs/acceptance.md): the 18 implementation checks, currently pending.
8. [Naming notes](docs/naming.md): repository name, alternatives, and positioning.

The individual documents are canonical. Preserve requirement IDs when revising scope so the plan, tasks, and acceptance evidence stay aligned.

## Extending to securities finance

The later domain layer can reuse instruments, issuers, countries, currencies, and markets to add agreement rules, collateral eligibility, borrower/lender relationships, and exception dependencies. A public example will remain synthetic. Any internal integration requires an authorized environment and domain-specific data contracts.

## Portfolio presentation

Repository: [thatquantguy44/MarketAtlas](https://github.com/thatquantguy44/MarketAtlas).

Suggested repository description:

> Temporal market knowledge graphs in PostgreSQL: connect macro data, instruments, and statistical relationships, with provenance and Power BI views.

Suggested topics: `knowledge-graph`, `market-data`, `macroeconomics`, `quantitative-finance`, `postgresql`, `python`, `powerbi`, `data-lineage`, `point-in-time`.

Before pinning an implemented release, add a real demo screenshot, a short reproducible walkthrough, and the measured release evidence. Screenshots, tests, and performance badges should describe work that actually exists. The project uses the [MIT License](LICENSE). Data sources and redistributed datasets require their own usage and redistribution review.
