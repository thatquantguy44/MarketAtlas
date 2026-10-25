# MarketAtlas agent guidance

Use the pinned role folders in this directory as focused review and implementation
prompts. For reusable upstream agents, skills, commands, and templates, begin with
[`agent-skills/AGENTS.md`](agent-skills/AGENTS.md); its exact snapshot and refresh
instructions are in [`agent-skills/PINNED.md`](agent-skills/PINNED.md). Read
`docs/spec.md`, `docs/tasks.md`, `docs/handoff.md`, and the relevant acceptance rows
before acting.

Core constraints apply to every role:

- Source access uses `marketatlas_source_reader`; never write to `meta`, `silver`,
  `gold`, `bronze`, or `audit`.
- Graph writes use `marketatlas_writer` and only the dedicated `atlas` or
  `atlas_report` schemas.
- Local secrets stay in ignored `configs/local.toml`; do not log or copy them.
- Preserve effective time, source availability time, and MarketAtlas record time as
  distinct concepts. Do not backdate knowledge or overwrite corrections.
- Every implementation claim needs retained test or validation evidence.

Pinned catalog sources and intended use are listed in [CATALOG.md](CATALOG.md).
