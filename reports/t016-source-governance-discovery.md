# T-016 source governance and next-interface discovery

Date: 2026-10-26. The source catalog was refreshed in a read-only transaction
under `marketatlas_source_reader`. Post-promotion verification produced
fingerprint `983c665d16384309fe3c8ef7b3d9dbd15ab8423e0e87ad0ec3886d633929999e`
and reported 102 upstream objects, of which six are supported live and 85
remain discovered but not onboarded.

The recommended next candidate is `gold.v_series_revision_summary`, a compact
current revision-quality view keyed by `series_id`. It is a safer next contract
than the 20.5-million-row revision history table. Josh approved its restricted
internal-only use and accepted the local pilot ownership roles.

The full decision and candidates are in
[`docs/source-onboarding-decision.md`](../docs/source-onboarding-decision.md).
T-016 promoted the view in the tracked registry and added a bounded read-only
adapter. `adapter verify-revision-summary` passed with no source-write
privileges. The configured three-series extract passed with no missing IDs;
its local generated payload is ignored. Its input-selection checksum was
`0210e390d6f96c46c0fbadfc9f03f7a58fb9297050d6e64894add5de00cd8530` and
its source-row checksum was
`6464695799cb764811958b659f3834effcf54f8cb80b4df0b904faeb34a9f212`.
No `atlas` or `atlas_report` rows were written or published.
