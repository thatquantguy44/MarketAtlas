SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas.input_manifest (
    input_manifest_id uuid PRIMARY KEY,
    source_name text NOT NULL CHECK (source_name <> ''),
    source_object text NOT NULL CHECK (source_object <> ''),
    source_snapshot_reference text,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    extracted_at timestamptz NOT NULL,
    redistribution_status text NOT NULL
        CHECK (redistribution_status IN ('synthetic', 'approved', 'unresolved', 'restricted')),
    manifest jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (source_name, source_object, manifest_sha256)
);

CREATE TABLE IF NOT EXISTS atlas.market_calendar_session (
    calendar_name text NOT NULL CHECK (calendar_name <> ''),
    session_date date NOT NULL,
    is_business_day boolean NOT NULL,
    calendar_version text NOT NULL CHECK (calendar_version <> ''),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    PRIMARY KEY (calendar_name, session_date, calendar_version)
);

CREATE TABLE IF NOT EXISTS atlas.market_observation_version (
    market_observation_version_id uuid PRIMARY KEY,
    observation_key uuid NOT NULL,
    instrument_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    session_date date NOT NULL,
    measure text NOT NULL CHECK (measure <> ''),
    value numeric NOT NULL,
    unit text NOT NULL CHECK (unit <> ''),
    calendar_name text NOT NULL CHECK (calendar_name <> ''),
    adjustment_basis text NOT NULL CHECK (adjustment_basis <> ''),
    adjustment_history_status text NOT NULL
        CHECK (adjustment_history_status IN ('supported', 'latest_only', 'unknown')),
    available_at timestamptz,
    availability_status text NOT NULL
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    source_record text NOT NULL CHECK (source_record <> ''),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    recorded_from timestamptz NOT NULL,
    recorded_to timestamptz,
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (observation_key, recorded_from),
    UNIQUE (source_record, recorded_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_market_observation_current
    ON atlas.market_observation_version (observation_key)
    WHERE recorded_to IS NULL;
CREATE INDEX IF NOT EXISTS ix_market_observation_as_of
    ON atlas.market_observation_version (instrument_node_id, session_date, available_at);

CREATE TABLE IF NOT EXISTS atlas.macro_observation_version (
    macro_observation_version_id uuid PRIMARY KEY,
    series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    reference_period date NOT NULL,
    reference_period_label text NOT NULL CHECK (reference_period_label <> ''),
    measure text NOT NULL DEFAULT 'value' CHECK (measure <> ''),
    frequency text NOT NULL CHECK (frequency <> ''),
    value numeric,
    unit text NOT NULL CHECK (unit <> ''),
    is_missing boolean NOT NULL DEFAULT false,
    vintage text NOT NULL CHECK (vintage <> ''),
    source_valid_through_inclusive date,
    available_at timestamptz,
    availability_status text NOT NULL
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    source_ingested_at timestamptz,
    source_record text NOT NULL CHECK (source_record <> ''),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    recorded_from timestamptz NOT NULL,
    recorded_to timestamptz,
    CHECK (is_missing OR value IS NOT NULL),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (series_node_id, reference_period, measure, vintage, recorded_from),
    UNIQUE (source_record, recorded_from)
);

CREATE INDEX IF NOT EXISTS ix_macro_observation_as_of
    ON atlas.macro_observation_version (series_node_id, reference_period, measure, available_at DESC);

CREATE OR REPLACE FUNCTION atlas.market_observations_as_of(
    p_knowledge_cutoff timestamptz DEFAULT NULL,
    p_system_cutoff timestamptz DEFAULT NULL
)
RETURNS TABLE (
    market_observation_version_id uuid,
    instrument_node_id uuid,
    session_date date,
    measure text,
    value numeric,
    unit text,
    calendar_name text,
    adjustment_basis text,
    source_record text,
    input_manifest_id uuid,
    selection_status text
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        market_observation_version_id, instrument_node_id, session_date, measure,
        value, unit, calendar_name, adjustment_basis, source_record, input_manifest_id,
        CASE
            WHEN p_knowledge_cutoff IS NULL THEN 'current_context'
            WHEN availability_status <> 'known' THEN 'unsupported_history'
            WHEN adjustment_history_status <> 'supported' THEN 'unsupported_adjusted_history'
            ELSE 'supported'
        END AS selection_status
    FROM atlas.market_observation_version
    WHERE (
        (p_system_cutoff IS NULL AND recorded_to IS NULL)
        OR (
            p_system_cutoff IS NOT NULL
            AND recorded_from <= p_system_cutoff
            AND (recorded_to IS NULL OR p_system_cutoff < recorded_to)
        )
    )
      AND (
        p_knowledge_cutoff IS NULL
        OR availability_status <> 'known'
        OR available_at <= p_knowledge_cutoff
      )
$function$;

CREATE OR REPLACE FUNCTION atlas.macro_observations_as_of(
    p_knowledge_cutoff timestamptz DEFAULT NULL,
    p_system_cutoff timestamptz DEFAULT NULL
)
RETURNS TABLE (
    macro_observation_version_id uuid,
    series_node_id uuid,
    reference_period date,
    reference_period_label text,
    measure text,
    frequency text,
    value numeric,
    unit text,
    vintage text,
    available_at timestamptz,
    source_record text,
    input_manifest_id uuid,
    selection_status text
)
LANGUAGE sql
STABLE
AS $function$
    WITH system_visible AS (
        SELECT *
        FROM atlas.macro_observation_version
        WHERE (
            (p_system_cutoff IS NULL AND recorded_to IS NULL)
            OR (
                p_system_cutoff IS NOT NULL
                AND recorded_from <= p_system_cutoff
                AND (recorded_to IS NULL OR p_system_cutoff < recorded_to)
            )
        )
    ), known_ranked AS (
        SELECT
            *,
            row_number() OVER (
                PARTITION BY series_node_id, reference_period, measure
                ORDER BY available_at DESC, recorded_from DESC
            ) AS version_rank
        FROM system_visible
        WHERE availability_status = 'known'
          AND (p_knowledge_cutoff IS NULL OR available_at <= p_knowledge_cutoff)
    ), unknown_ranked AS (
        SELECT
            *,
            row_number() OVER (
                PARTITION BY series_node_id, reference_period, measure
                ORDER BY recorded_from DESC
            ) AS version_rank
        FROM system_visible
        WHERE availability_status <> 'known'
          AND p_knowledge_cutoff IS NOT NULL
    )
    SELECT
        macro_observation_version_id, series_node_id, reference_period,
        reference_period_label, measure, frequency, value, unit, vintage,
        available_at, source_record, input_manifest_id,
        CASE
            WHEN p_knowledge_cutoff IS NULL THEN 'current_context'
            ELSE 'supported'
        END AS selection_status
    FROM known_ranked
    WHERE version_rank = 1

    UNION ALL

    SELECT
        unknown.macro_observation_version_id, unknown.series_node_id,
        unknown.reference_period, unknown.reference_period_label, unknown.measure,
        unknown.frequency, unknown.value, unknown.unit, unknown.vintage,
        unknown.available_at, unknown.source_record, unknown.input_manifest_id,
        'unsupported_history' AS selection_status
    FROM unknown_ranked AS unknown
    WHERE unknown.version_rank = 1
      AND NOT EXISTS (
          SELECT 1
          FROM known_ranked AS known
          WHERE known.series_node_id = unknown.series_node_id
            AND known.reference_period = unknown.reference_period
            AND known.measure = unknown.measure
      )
$function$;

RESET ROLE;
