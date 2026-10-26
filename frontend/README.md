# MarketAtlas evidence workspace

This independent React application follows the QuantMeridian scaffold decision in `../docs/decisions/001-quantmeridian-react-scaffold.md`: React, TypeScript, Vite, React Router, Zustand, Tailwind, and a focused evidence-workspace shell.

It renders a clearly labeled synthetic snapshot adapter and an optional local live macro-economic graph. The browser never connects to PostgreSQL and contains no credentials: the live toggle fetches only the localhost report API, which runs as `marketatlas_report_reader` and reads snapshot-pinned `atlas_report` views.

```bash
npm install
npm run dev
npm test
npm run build
```

For the live macro graph, publish the approved context projection first, then run the report API in another terminal:

```bash
PYTHONPATH=../src python -m market_atlas economic-graph publish --config ../configs/local.toml --input ../data/generated/macro_context_pilot.json
PYTHONPATH=../src python -m market_atlas report serve-macro-economic-graph --config ../configs/local.toml
```

Select **Live macro graph** in the upper-right mode toggle. If the API is unavailable, the UI stays explicit about the boundary rather than falling back to a database connection.

The default screen is a focused MarketAtlas graph workbench rather than a permanent navigation rail. It includes a selected-entity lens, source-aware edge treatments, a bounded expandable cluster, evidence drawer, full scoped-evidence workspace, and an opt-in candidate-review queue. Context links remain visibly distinct from calculated correlation estimates; candidate links explicitly require review and the local fixture decision flow is labeled as non-persistent demo behavior.
