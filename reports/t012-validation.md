# T-012 React demo validation

Date: 2026-10-24. The demo implements the frontend direction selected in [ADR-001](../docs/decisions/001-quantmeridian-react-scaffold.md). It is a React fixture demo, not Power BI acceptance evidence.

## Implementation

`frontend/` is an independent React 18, TypeScript, Vite, React Router, Zustand, and Tailwind application. Its terminal visual system follows the QuantMeridian scaffold pattern while retaining separate MarketAtlas source files and fixture data.

The initial route-oriented demo was superseded on 2026-10-24 by the current focused evidence workspace. It keeps the same fixture-only reporting boundary while composing its market-map, context, provenance, and review functions into one selected-entity graph lens:

| Route | Snapshot-pinned concept shown |
| --- | --- |
| Header and insight row | Snapshot/data-health state and current evidence universe |
| Graph stage | Bounded sourced relationships, focus lens, clustering, search, and view controls |
| Evidence drawer | Source lineage, human-readable fields, explicit evidence status, and scoped drill-through |
| Candidate-review queue | Opt-in unreviewed links, matching method/score, and an append-only demo decision flow |
| Evidence legend | Source-backed, reviewed, candidate, context-only, and unavailable treatment |

The current adapter is explicitly fixture-only and mirrors T-011’s declared report grains. Browser code has no PostgreSQL driver, database configuration, credential, or direct database connection. A production endpoint must read only the snapshot-pinned `atlas_report.current_*` views.

## Verification

From `frontend/`, the following succeeded:

```text
npm run typecheck
npm test              # 4 tests passed
npm run build         # production Vite bundle built successfully
```

The local Vite server returned the MarketAtlas demo HTML at `http://localhost:3001/`. Browser automation was unavailable for a screenshot/navigation run in this environment, so no visual browser assertion is claimed.

## Dependency posture

The scaffold retains the QuantMeridian-compatible React 18/Vite 5 architecture but applies compatible patch upgrades to React Router 6.30.6, Vite 5.4.21, and PostCSS 8.5.31. After classifying the Vite plugin as a build dependency, `npm audit --omit=dev` reports two moderate React Router 6 issues. They require the semver-major upgrade to React Router 7.18.4 for complete remediation. The static demo does not process untrusted redirects, hydrate server errors, or expose a public production server, but that upgrade is required before external deployment.

AC-009 remains partial because a Power BI semantic model/report has not been exercised.
