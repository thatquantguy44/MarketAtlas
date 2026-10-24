SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas.build_run (
    build_run_id uuid PRIMARY KEY,
    build_key uuid NOT NULL UNIQUE,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    knowledge_cutoff timestamptz,
    configuration_sha256 text NOT NULL CHECK (configuration_sha256 ~ '^[0-9a-f]{64}$'),
    configuration jsonb NOT NULL,
    code_revision text NOT NULL CHECK (code_revision <> ''),
    environment jsonb NOT NULL,
    run_status text NOT NULL CHECK (
        run_status IN ('building', 'validated', 'published', 'failed')
    ),
    error_detail text,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamptz,
    CHECK ((run_status = 'failed') = (error_detail IS NOT NULL)),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS atlas.serving_snapshot (
    serving_snapshot_id uuid PRIMARY KEY,
    snapshot_key uuid NOT NULL UNIQUE,
    build_run_id uuid NOT NULL UNIQUE REFERENCES atlas.build_run(build_run_id),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    knowledge_cutoff timestamptz,
    snapshot_status text NOT NULL CHECK (
        snapshot_status IN ('building', 'validated', 'published', 'superseded', 'failed')
    ),
    output_sha256 text CHECK (output_sha256 ~ '^[0-9a-f]{64}$'),
    row_count integer NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    failure_reason text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    validated_at timestamptz,
    published_at timestamptz,
    CHECK ((snapshot_status = 'failed') = (failure_reason IS NOT NULL)),
    CHECK (validated_at IS NULL OR validated_at >= created_at),
    CHECK (published_at IS NULL OR published_at >= created_at)
);

CREATE TABLE IF NOT EXISTS atlas.publication (
    publication_name text PRIMARY KEY CHECK (publication_name <> ''),
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS atlas_report.rolling_correlation_estimate_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    rolling_correlation_estimate_version_id uuid NOT NULL
        REFERENCES atlas.rolling_correlation_estimate_version(
            rolling_correlation_estimate_version_id
        ),
    instrument_low_node_id uuid NOT NULL,
    instrument_high_node_id uuid NOT NULL,
    endpoint_session_date date NOT NULL,
    window_start_session_date date NOT NULL,
    paired_return_count integer NOT NULL,
    correlation numeric,
    estimate_status text NOT NULL,
    knowledge_cutoff timestamptz,
    method_version text NOT NULL,
    configuration_sha256 text NOT NULL,
    input_selection_sha256 text NOT NULL,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    PRIMARY KEY (serving_snapshot_id, rolling_correlation_estimate_version_id)
);

CREATE INDEX IF NOT EXISTS ix_snapshot_correlation_lookup
    ON atlas_report.rolling_correlation_estimate_snapshot (
        serving_snapshot_id, endpoint_session_date
    );

CREATE OR REPLACE FUNCTION atlas.publish_serving_snapshot(
    p_publication_name text,
    p_serving_snapshot_id uuid
)
RETURNS uuid
LANGUAGE plpgsql
SET search_path = pg_catalog, atlas
AS $function$
DECLARE
    prior_snapshot_id uuid;
    snapshot_run_id uuid;
BEGIN
    PERFORM 1
    FROM atlas.serving_snapshot
    WHERE serving_snapshot_id = p_serving_snapshot_id
      AND snapshot_status = 'validated'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'snapshot % is not validated for publication', p_serving_snapshot_id
            USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO atlas.publication (publication_name, serving_snapshot_id)
    VALUES (p_publication_name, p_serving_snapshot_id)
    ON CONFLICT (publication_name) DO NOTHING;

    SELECT serving_snapshot_id INTO prior_snapshot_id
    FROM atlas.publication
    WHERE publication_name = p_publication_name
    FOR UPDATE;

    UPDATE atlas.publication
    SET serving_snapshot_id = p_serving_snapshot_id,
        published_at = clock_timestamp()
    WHERE publication_name = p_publication_name;

    UPDATE atlas.serving_snapshot
    SET snapshot_status = 'published', published_at = clock_timestamp()
    WHERE serving_snapshot_id = p_serving_snapshot_id
    RETURNING build_run_id INTO snapshot_run_id;

    UPDATE atlas.build_run
    SET run_status = 'published', completed_at = clock_timestamp()
    WHERE build_run_id = snapshot_run_id;

    IF prior_snapshot_id <> p_serving_snapshot_id THEN
        UPDATE atlas.serving_snapshot
        SET snapshot_status = 'superseded'
        WHERE serving_snapshot_id = prior_snapshot_id
          AND snapshot_status = 'published';
    END IF;
    RETURN p_serving_snapshot_id;
END
$function$;

CREATE OR REPLACE VIEW atlas_report.current_rolling_correlation_estimate AS
SELECT
    publication.publication_name,
    publication.published_at,
    snapshot.*
FROM atlas.publication
JOIN atlas_report.rolling_correlation_estimate_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id;

GRANT SELECT ON ALL TABLES IN SCHEMA atlas_report TO marketatlas_report_reader;

RESET ROLE;
