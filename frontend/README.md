# MarketAtlas demo terminal

This independent React application follows the QuantMeridian scaffold decision in `../docs/decisions/001-quantmeridian-react-scaffold.md`: React, TypeScript, Vite, React Router, Zustand, Tailwind, and a terminal-oriented shell.

It currently renders a clearly labeled synthetic snapshot adapter that mirrors the T-011 report contract. It does not connect browser code to PostgreSQL and contains no connection settings or credentials. A production server route must source its payload only from the snapshot-pinned `atlas_report.current_*` views documented in `../docs/reporting.md`.

```bash
npm install
npm run dev
npm test
npm run build
```

The five routes are Overview, Market map, Macro context, Correlations, and Provenance. Context links remain visibly distinct from calculated correlation estimates.
