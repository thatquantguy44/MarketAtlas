# MarketAtlas evidence workspace

This independent React application follows the QuantMeridian scaffold decision in `../docs/decisions/001-quantmeridian-react-scaffold.md`: React, TypeScript, Vite, React Router, Zustand, Tailwind, and a focused evidence-workspace shell.

It currently renders a clearly labeled synthetic snapshot adapter that mirrors the T-011 report contract. It does not connect browser code to PostgreSQL and contains no connection settings or credentials. A production server route must source its payload only from the snapshot-pinned `atlas_report.current_*` views documented in `../docs/reporting.md`.

```bash
npm install
npm run dev
npm test
npm run build
```

The default screen is a focused MarketAtlas graph workbench rather than a permanent navigation rail. It includes a selected-entity lens, source-aware edge treatments, a bounded expandable cluster, evidence drawer, full scoped-evidence workspace, and an opt-in candidate-review queue. Context links remain visibly distinct from calculated correlation estimates; candidate links explicitly require review and the local fixture decision flow is labeled as non-persistent demo behavior.
