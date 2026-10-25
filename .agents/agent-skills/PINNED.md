# Pinned upstream snapshot

This directory is the complete tracked contents of the upstream `agent-skills`
repository at Git commit `f63ec56a3cc936408d792956ae583c3c96a825bd`.

It was added as a Git-archive snapshot on 2026-10-25. It intentionally has no
`.git` directory, submodule, or symlink to an external checkout: the catalog is
reviewable and available to future MarketAtlas builds even when the original local
checkout moves. Any internal symlinks tracked by the upstream project are retained.

## Refreshing deliberately

To refresh the catalog, choose and record an explicit upstream commit, replace this
directory with `git archive <commit>` from the upstream repository, update this file
and `../CATALOG.md`, then review the resulting diff before committing. Do not update
the snapshot implicitly as part of unrelated application work.

MarketAtlas-specific guidance in the sibling role folders and `.agents/AGENTS.md`
takes precedence over generic upstream instructions.
