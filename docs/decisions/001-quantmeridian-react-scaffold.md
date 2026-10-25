# ADR-001: Adopt the QuantMeridian React scaffold for the MarketAtlas demo

Status: accepted 2026-10-24.

## Decision

MarketAtlas will use the same frontend scaffold pattern as the local `QuantMeridian-Core` repository for its demo application:

- React 18, TypeScript, and Vite 5;
- React Router for page routing and Zustand for browser state;
- Tailwind CSS with the dense, terminal-oriented shell and component structure;
- a `src/app`, `src/components`, `src/lib`, and `src/server` layout;
- Vite client build plus server-side route-handler build, with TypeScript checks, Vitest, and Playwright available for verification.

The visual baseline is the QuantMeridian terminal language: dark panels, explicit evidence-state semantics, compact typography, and status-forward data displays. MarketAtlas uses its own focused workspace, components, assets, API contracts, and data model; it does not require a permanent navigation rail.

## Scope and constraints

This is a scaffold and interaction decision, not a source-code import or a runtime dependency on QuantMeridian-Core. MarketAtlas must not copy its private-upstream-only material, secrets, data, or domain modules. The target repository describes itself as generated and advises against direct edits; MarketAtlas therefore remains an independent application with separately maintained files and dependency lock.

The demo API must read only the `atlas_report` snapshot-pinned views created by T-010. It must expose the resolved snapshot ID, publication time, knowledge cutoff, and quality/provenance identifiers with each response. It must never connect browser code directly to PostgreSQL or expose local configuration credentials.

## Consequences

T-011 defines the snapshot-pinned report views and provenance payloads required by the frontend. T-012 implements them as a focused evidence workspace: graph lens, context treatment, provenance/quality drawer, and candidate-review controls. The frontend represents fixture-only, unsupported, missing, and unreviewed states explicitly rather than fabricate data.

## Evidence inspected

The local reference is `/Users/joshualutkemuller/Documents/Quant Sandbox/platforms/QuantMeridian-Core`: its `package.json` declares React, Vite, React Router, Zustand, Tailwind, TypeScript, Vitest, and Playwright; its source layout separates app routes, reusable components, data/lib code, and server handlers. This decision does not add those packages to MarketAtlas yet.
