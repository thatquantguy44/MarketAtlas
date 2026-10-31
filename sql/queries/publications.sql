-- Run with a login that can assume marketatlas_report_reader.
-- Connect to the target database configured in ignored configs/local.toml.
BEGIN READ ONLY;
SET LOCAL ROLE marketatlas_report_reader;

-- All currently published snapshots, with their independent identities/times.
SELECT publication_name, serving_snapshot_id, published_at,
       input_manifest_id, build_run_id, knowledge_cutoff, row_count
FROM atlas_report.current_snapshot_metadata
ORDER BY publication_name;

-- Discover the available report views in your database client.
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'atlas_report'
ORDER BY table_name;

COMMIT;
