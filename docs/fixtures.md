# Synthetic fixture contract (first implementation slice)

`python -m market_atlas fixture build --output <directory>` writes canonical JSON and a SHA-256 manifest. This fixture is fully generated, fixed to a synthetic 2024 weekday calendar, and has no upstream or database dependency. The manifest says `graph_and_report_not_built` to keep the implementation status explicit.

## Records and grain

| Collection | Grain | Distinguishing fields |
| --- | --- | --- |
| `entities` | One synthetic canonical entity | Stable ID and controlled type |
| `identifiers` | One source ticker mapping interval | Listing, source, scheme, value, `[valid_from, valid_to)` |
| `assertions` | One reference or curated assertion | Typed endpoints, predicate, status, effective dates, availability, record time, provenance |
| `market_observations` | Instrument × session × measure | Synthetic adjusted close, unit, adjustment, availability, source record |
| `macro_observations` | Series × period × vintage | Value, frequency, unit, availability, source record |
| `configured_pairs` | One undirected instrument pair | Two stable instrument IDs |

The 75 sessions omit weekends but do **not** model real market holidays. `I-A` changes its listing ticker from `OLDX` to `NEWX` without changing instrument identity. `O-A` has a sector and index membership. `A8` is disputed, while `A14` is a late-arriving fact. The macro series has an initial release and a later revision. `I-B` has three missing prices; `I-C` is constant. The `I-A`/`I-B` pair is intended for a later rolling-correlation example, and `I-A`/`I-C` for a zero-variance case. These are fixture inputs, not calculated or validated estimates.

`fixture inspect --knowledge-cutoff <UTC timestamp>` selects only assertions and macro vintages available at that cutoff. It demonstrates the availability dimension of the contract. It does not replay MarketAtlas system-record history, evaluate business effective intervals, or implement graph traversal. Those behaviors require T-005 through T-007.

## Current validation

The validator checks synthetic labels, unique keys, known endpoint types, controlled predicates, required provenance and temporal fields, positive prices, configured pairs, manifest counts, canonical JSON, and SHA-256 integrity. It does not validate live-source rights, full temporal exclusion constraints, PostgreSQL integrity, analytical results, or Power BI behavior. All acceptance criteria in [acceptance.md](acceptance.md) remain pending.
