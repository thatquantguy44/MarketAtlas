# T-004B live MacroMedallion/EcoMedallion ingestion validation

Date: 2026-10-24. MacroMedallion and EcoMedallion are interchangeable names for the one local upstream asset. This evidence covers the bounded PostgreSQL integration; no remote repository URL, commit pin, or source-code import is required.

## Contract and boundary

The source session verified the approved meta.fred_series and gold.fred_point_in_time contracts under marketatlas_source_reader. The reader session was read-only, its negative write probe was blocked, and it held no upstream write privileges. The separate marketatlas_writer role wrote only to atlas.

The adapter ingest command performs these separate steps:

1. Read and validate the bounded source extract through the source reader.
2. Create or reuse an immutable atlas.input_manifest.
3. Upsert only macro-series identities and insert immutable macro-observation versions into atlas.

No upstream schemas, objects, or rows are modified.

## First live result

The first configured-pilot run created input manifest 8af251c8-c74f-5ca3-b4de-705ec4224ea1, loaded 3 macro-series identities, and inserted 151 macro-observation versions.

| Item | Value |
| --- | --- |
| Manifest SHA-256 | edee94f798e3b9a08f62dacfb36ca7e07ede8dde83b808809831af69fa26b902 |
| Source-row SHA-256 | ceb90016079d5e48699bad161c964928de4d6dc623a2078290458a057df67dc1 |
| Manifest created | true |
| Observation versions inserted | 151 |

The immediate repeat run reused that same manifest (manifest_created false) and inserted zero observation versions, demonstrating idempotency for identical configured source rows.

## Remaining limits

The live source load is intentionally bounded to macro identities and observation versions. It does not create market instruments, curated mappings, real-data report publication, or public data artifacts. The fixture publisher now selects only nodes explicitly marked as synthetic, so this live load cannot leak into a synthetic serving snapshot. Redistribution status remains unresolved, and broader source-owner/deployment discovery remains open in T-001/T-004.
