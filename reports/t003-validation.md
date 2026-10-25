# T-003 deterministic synthetic fixture validation

Date: 2026-10-24. The generated fixture is explicitly synthetic and portable.

The exercised canonical fixture had SHA-256 `15e24cebf895af4e58b1c5a4dfe5712ba28b473ca64ee6c4f4df2f5bac0877da` with 15 entities, 4 identifier intervals, 15 assertions, 3 curated contexts, 222 market observations, 2 macro observations, 75 sessions, and 2 configured pairs.

`fixture validate` accepted the generated manifest and payload. The early availability inspection selected only the initial `M-GROWTH` macro vintage for `2024-01`, demonstrating that the fixture preserves the later macro revision for a later knowledge cutoff. Fixture labels, manifest status, and CLI output identify the data as synthetic; no upstream records are copied into the repository.
