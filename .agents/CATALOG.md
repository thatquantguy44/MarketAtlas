# Pinned agent catalog

These are focused, repository-local adaptations of roles from the referenced source
commit. They are deliberately not symlinked, so MarketAtlas has stable, reviewable
guidance even when the upstream catalog changes.

## Full reusable catalog

The complete upstream `agent-skills` catalog is vendored in
[`agent-skills/`](agent-skills/) at commit
`f63ec56a3cc936408d792956ae583c3c96a825bd`. It is an immutable Git-archive
snapshot, not a symlink or submodule, so it can be used for future builds without
depending on the local upstream checkout. See
[`agent-skills/PINNED.md`](agent-skills/PINNED.md) for provenance and refresh
guidance.

The focused roles below remain the MarketAtlas-specific entry points. Their safety
and domain guidance takes precedence if it conflicts with a generic upstream role.

| Local role | Upstream role | Pinned commit | Use in MarketAtlas |
| --- | --- | --- | --- |
| `sql-integration` | `agents/sql-integration-agent` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | PostgreSQL access, schema discovery, and safe queries |
| `temporal-provenance` | `agents/provenance/bitemporal_data` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | Revisions, retractions, as-of replay, and look-ahead controls |
| `data-modeling` | `agents/data_engineering/data_modeling` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | Observation and serving-table grain, keys, and SCD design |
| `data-quality` | `agents/data_quality` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | Contract, coverage, identity, and point-in-time quality gates |
| `quant-analytics` | `agents/quant_analyst` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | Correlation methodology and later research workflow design |
| `powerbi-reporting` | `agents/powerbi-dashboard-agent` | `bc4306062e2873dc6b92a7e20a88dea8afb0e0bf` | Report-model, governance, and Power BI deployment review |
| `code-review` | `agent-skills/agents/code-reviewer` | `f63ec56a3cc936408d792956ae583c3c96a825bd` | Correctness, architecture, security, and performance review before merge |
| `security-review` | `agent-skills/agents/security-auditor` | `f63ec56a3cc936408d792956ae583c3c96a825bd` | Secret handling, least privilege, SQL safety, and dependency hardening |
| `test-engineering` | `agent-skills/agents/test-engineer` | `f63ec56a3cc936408d792956ae583c3c96a825bd` | Test strategy, failure-mode coverage, and evidence quality |

The three generic quality roles are used as independent pre-merge gates. They complement
rather than replace the domain-specific roles above.
