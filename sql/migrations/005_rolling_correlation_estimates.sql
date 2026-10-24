SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas.rolling_correlation_estimate_version (
    rolling_correlation_estimate_version_id uuid PRIMARY KEY,
    estimate_key uuid NOT NULL,
    instrument_low_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    instrument_high_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    endpoint_session_date date NOT NULL,
    window_start_session_date date NOT NULL,
    window_session_count integer NOT NULL DEFAULT 60 CHECK (window_session_count = 60),
    minimum_paired_return_count integer NOT NULL DEFAULT 45
        CHECK (minimum_paired_return_count = 45),
    paired_return_count integer NOT NULL CHECK (paired_return_count BETWEEN 0 AND 59),
    correlation numeric,
    estimate_status text NOT NULL CHECK (
        estimate_status IN (
            'supported', 'insufficient_sample', 'zero_variance',
            'incompatible_input', 'unsupported_history'
        )
    ),
    return_definition text NOT NULL CHECK (return_definition = 'simple_adjusted_close_return'),
    adjustment_basis text NOT NULL CHECK (adjustment_basis <> ''),
    calendar_name text NOT NULL CHECK (calendar_name <> ''),
    method_version text NOT NULL CHECK (method_version <> ''),
    configuration_sha256 text NOT NULL CHECK (configuration_sha256 ~ '^[0-9a-f]{64}$'),
    input_selection_sha256 text NOT NULL CHECK (input_selection_sha256 ~ '^[0-9a-f]{64}$'),
    knowledge_cutoff timestamptz,
    max_input_available_at timestamptz,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    recorded_from timestamptz NOT NULL,
    recorded_to timestamptz,
    provenance jsonb NOT NULL,
    CHECK (instrument_low_node_id < instrument_high_node_id),
    CHECK (window_start_session_date <= endpoint_session_date),
    CHECK (
        (estimate_status = 'supported' AND correlation IS NOT NULL)
        OR (estimate_status <> 'supported' AND correlation IS NULL)
    ),
    CHECK (correlation IS NULL OR correlation BETWEEN -1 AND 1),
    CHECK (
        max_input_available_at IS NULL
        OR knowledge_cutoff IS NULL
        OR max_input_available_at <= knowledge_cutoff
    ),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (estimate_key, recorded_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_rolling_correlation_estimate_current_key
    ON atlas.rolling_correlation_estimate_version (estimate_key)
    WHERE recorded_to IS NULL;
CREATE INDEX IF NOT EXISTS ix_rolling_correlation_estimate_lookup
    ON atlas.rolling_correlation_estimate_version (
        instrument_low_node_id, instrument_high_node_id, endpoint_session_date
    );

CREATE OR REPLACE FUNCTION atlas.validate_rolling_correlation_estimate_version()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, atlas
AS $function$
DECLARE
    low_type text;
    high_type text;
BEGIN
    SELECT node_type INTO low_type FROM atlas.node WHERE node_id = NEW.instrument_low_node_id;
    SELECT node_type INTO high_type FROM atlas.node WHERE node_id = NEW.instrument_high_node_id;
    IF low_type <> 'instrument' OR high_type <> 'instrument' THEN
        RAISE EXCEPTION 'rolling correlation endpoints must be instrument nodes'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

DROP TRIGGER IF EXISTS trg_validate_rolling_correlation_estimate_version
    ON atlas.rolling_correlation_estimate_version;
CREATE TRIGGER trg_validate_rolling_correlation_estimate_version
BEFORE INSERT OR UPDATE ON atlas.rolling_correlation_estimate_version
FOR EACH ROW EXECUTE FUNCTION atlas.validate_rolling_correlation_estimate_version();

RESET ROLE;
