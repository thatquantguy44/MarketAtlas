# Contributor demo walkthrough

This is the exercised, credential-free path for a new contributor. It uses only
the tracked synthetic fixture; it does not read MacroMedallion / EcoMedallion,
require `configs/local.toml`, or make a vendor call.

## Prerequisites

- Python 3.11 or newer.
- Node.js 20 or newer only when running the browser demo.
- A checkout of this repository. No database is needed for the fixture steps.

## Fixture contract walkthrough

Run from the repository root:

```bash
PYTHONPATH=src python3 -m market_atlas fixture build --output /tmp/marketatlas-fixture
PYTHONPATH=src python3 -m market_atlas fixture validate --input /tmp/marketatlas-fixture
PYTHONPATH=src python3 -m market_atlas fixture inspect --knowledge-cutoff 2024-02-10T00:00:00Z
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The first command creates the labeled synthetic `fixture.json` and its
manifest. The validation command must report `"synthetic": true` and the
stable SHA-256
`15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da`.
The cutoff inspection demonstrates that the later macro revision is excluded
at the requested cutoff. A clean checkout walkthrough of these exact commands
ran on 2026-10-26; all 49 Python tests passed. The run transcript and output
summary are retained in [the T-014 handoff report](../reports/t014-contributor-handoff.md).

## Browser demonstration

The fixture view has no API or database dependency:

```bash
cd frontend
npm install
npm run dev
```

Open the displayed localhost URL and keep **Fixture graph** selected. The
expected screen is the `Synthetic Alpha Share` one-hop graph with a snapshot
and source-lineage drawer. Run `npm test` and `npm run build` before handing
off a frontend change.

The optional **Live macro graph** is an integration demonstration, not part of
the clean-room fixture path. It needs the separately started local report API:

```bash
PYTHONPATH=src python3 -m market_atlas report serve-macro-economic-graph --config configs/local.toml
cd frontend
npm run dev
```

It fetches only `/api/v1/macro-economic-graph` through Vite's local proxy. It
does not receive database credentials and must never query upstream schemas
from browser code. The UI asks for 12 series per visual category page so cards
and connections remain readable; the report API remains independently bounded
to 1–100 rows and T-013 benchmarks a 50-series request.

## Screenshot evidence

On 2026-10-26 the implementation walkthrough captured three local browser
screenshots in the task execution record: the synthetic fixture graph, the
live catalog summary (290 approved series and 11 concepts), and the live
Regional category page (120 matching series, 12 visual nodes per page).
Screenshots are intentionally not regenerated from restricted source data or
checked in as binary assets. Recreate them only from the synthetic fixture or
the authorized local report API, and label the latter `current_only` taxonomy.

## What this walkthrough does not claim

- It does not exercise Power BI, a scheduler, or a production deployment.
- It does not authorize any discovered source table beyond the five
  `supported_live` contracts.
- It does not establish redistribution rights for MacroMedallion / EcoMedallion
  content or its derived public artifacts.

See [operations.md](operations.md) for refresh/recovery responsibility and
[data-and-license-notice.md](data-and-license-notice.md) before publishing an
artifact.
