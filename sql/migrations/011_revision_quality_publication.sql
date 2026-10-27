SET ROLE marketatlas_writer;

-- Captured current-quality versions, never historical observation vintages.
CREATE TABLE IF NOT EXISTS atlas.macro_revision_quality_version (
    revision_quality_version_id uuid PRIMARY KEY,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    series_id text NOT NULL,
    quality_status text NOT NULL CHECK (quality_status IN ('available', 'unknown')),
    observation_count bigint CHECK (observation_count >= 0),
    avg_revision_count double precision CHECK (avg_revision_count >= 0 AND avg_revision_count < 'Infinity'),
    max_revision_count bigint CHECK (max_revision_count >= 0),
    avg_abs_revision_pct double precision CHECK (avg_abs_revision_pct >= 0 AND avg_abs_revision_pct < 'Infinity'),
    max_abs_revision_pct double precision CHECK (max_abs_revision_pct >= 0 AND max_abs_revision_pct < 'Infinity'),
    source_record text NOT NULL,
    source_extracted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    temporal_status text NOT NULL DEFAULT 'current_only_revision_quality'
        CHECK (temporal_status = 'current_only_revision_quality'),
    UNIQUE (input_manifest_id, series_id),
    CHECK (
        (quality_status = 'unknown' AND observation_count IS NULL
         AND avg_revision_count IS NULL AND max_revision_count IS NULL
         AND avg_abs_revision_pct IS NULL AND max_abs_revision_pct IS NULL)
        OR (quality_status = 'available' AND observation_count IS NOT NULL
         AND avg_revision_count IS NOT NULL AND max_revision_count IS NOT NULL
         AND avg_abs_revision_pct IS NOT NULL AND max_abs_revision_pct IS NOT NULL
         AND avg_revision_count <= max_revision_count
         AND avg_abs_revision_pct <= max_abs_revision_pct)
    )
);

CREATE TABLE IF NOT EXISTS atlas_report.macro_revision_quality_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    revision_quality_version_id uuid NOT NULL REFERENCES atlas.macro_revision_quality_version(revision_quality_version_id),
    series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    series_id text NOT NULL,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    build_run_id uuid NOT NULL REFERENCES atlas.build_run(build_run_id),
    source_record text NOT NULL,
    details jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, series_node_id),
    UNIQUE (serving_snapshot_id, series_id)
);

ALTER TABLE atlas_report.provenance_snapshot
    DROP CONSTRAINT IF EXISTS provenance_snapshot_provenance_kind_check;
ALTER TABLE atlas_report.provenance_snapshot
    ADD CONSTRAINT provenance_snapshot_provenance_kind_check CHECK (
        provenance_kind IN ('relationship', 'macro_context', 'rolling_correlation',
                          'macro_source_context', 'macro_economic_graph', 'macro_revision_quality')
    );

CREATE OR REPLACE VIEW atlas_report.current_macro_revision_quality AS
SELECT publication.publication_name, publication.published_at, snapshot.*
FROM atlas.publication AS publication
JOIN atlas_report.macro_revision_quality_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id
WHERE publication.publication_name = 'macro_revision_quality';

GRANT SELECT ON atlas_report.macro_revision_quality_snapshot,
    atlas_report.current_macro_revision_quality TO marketatlas_report_reader;

RESET ROLE;
