# T-002 scaffold and isolated-runtime validation

Date: 2026-10-24. This validation covers the portable fixture path only; it does not require an upstream checkout or database credentials.

## Exercised workflow

```text
PYTHONPATH=src python3 -m market_atlas fixture build --output <temporary directory>
PYTHONPATH=src python3 -m market_atlas fixture validate --input <temporary directory>
PYTHONPATH=src python3 -m market_atlas fixture inspect --knowledge-cutoff 2024-02-10T00:00:00Z
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

The build/validate pair produced and verified the canonical `synthetic-v1` fixture without upstream access. The inspected cutoff returned a synthetic availability-only view and did not make business-time or system-time replay claims. The full suite completed with 22 passing tests.

Configuration separates read-only `source_database` and `target_database` roles. The optional local upstream checkout is configured only in ignored `configs/local.toml`; it is never required for fixture mode and its path is not emitted in public CLI output.
