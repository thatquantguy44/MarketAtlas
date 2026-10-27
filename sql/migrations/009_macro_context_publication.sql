SET ROLE marketatlas_writer;

-- These are current source-interface records, not reconstructed point-in-time history.
CREATE TABLE IF NOT EXISTS atlas.macro_series_taxonomy_current (
    macro_series_taxonomy_id uuid PRIMARY KEY,
    series_node_id uuid NOT NULL UNIQUE REFERENCES atlas.node(node_id),
    series_id text NOT NULL UNIQUE,
    title text,
    source text,
    frequency text,
    units text,
    econ_category text,
    polarity text,
    default_transform text,
    scale text,
    decimals integer,
    notes text,
    geo text,
    metric text,
    temporal_status text NOT NULL DEFAULT 'current_only'
        CHECK (temporal_status = 'current_only'),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL UNIQUE,
    source_extracted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS atlas.macro_release_event_current (
    macro_release_event_id uuid PRIMARY KEY,
    release_id text NOT NULL,
    release_name text,
    release_date date NOT NULL,
    importance text,
    econ_category text,
    representative_series_id text,
    representative_series_node_id uuid REFERENCES atlas.node(node_id),
    is_future boolean NOT NULL,
    source_fetched_at timestamptz,
    temporal_status text NOT NULL DEFAULT 'scheduled_event'
        CHECK (temporal_status = 'scheduled_event'),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL UNIQUE,
    source_extracted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (release_id, release_date)
);

CREATE TABLE IF NOT EXISTS atlas.macro_source_coverage_current (
    macro_source_coverage_id uuid PRIMARY KEY,
    source text NOT NULL,
    series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    series_id text NOT NULL,
    category text,
    frequency text,
    latest_observation_date date,
    observation_count bigint,
    days_since_last bigint,
    is_stale boolean NOT NULL,
    temporal_status text NOT NULL DEFAULT 'current_only'
        CHECK (temporal_status = 'current_only'),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL UNIQUE,
    source_extracted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (source, series_node_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.macro_source_context_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    context_kind text NOT NULL CHECK (
        context_kind IN ('series_taxonomy', 'release_event', 'source_coverage')
    ),
    context_subject_id uuid NOT NULL,
    series_node_id uuid REFERENCES atlas.node(node_id),
    effective_date date,
    temporal_status text NOT NULL CHECK (
        temporal_status IN ('current_only', 'scheduled_event')
    ),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL,
    details jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, context_kind, context_subject_id)
);

ALTER TABLE atlas_report.provenance_snapshot
    DROP CONSTRAINT IF EXISTS provenance_snapshot_provenance_kind_check;
ALTER TABLE atlas_report.provenance_snapshot
    ADD CONSTRAINT provenance_snapshot_provenance_kind_check CHECK (
        provenance_kind IN (
            'relationship', 'macro_context', 'rolling_correlation',
            'macro_source_context'
        )
    );

CREATE INDEX IF NOT EXISTS ix_report_macro_source_context_series
    ON atlas_report.macro_source_context_snapshot (serving_snapshot_id, series_node_id);

CREATE OR REPLACE VIEW atlas_report.current_macro_source_context AS
SELECT
    publication.publication_name,
    publication.published_at,
    snapshot.*
FROM atlas.publication AS publication
JOIN atlas_report.macro_source_context_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id
WHERE publication.publication_name = 'macro_context';

GRANT SELECT ON ALL TABLES IN SCHEMA atlas_report TO marketatlas_report_reader;

RESET ROLE;
