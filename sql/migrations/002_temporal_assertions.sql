SET ROLE marketatlas_writer;

ALTER TABLE atlas.reference_assertion
    ADD COLUMN IF NOT EXISTS assertion_key uuid;

UPDATE atlas.reference_assertion
SET assertion_key = assertion_id
WHERE assertion_key IS NULL;

ALTER TABLE atlas.reference_assertion
    ALTER COLUMN assertion_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_reference_assertion_current_key
    ON atlas.reference_assertion (assertion_key)
    WHERE recorded_to IS NULL;

CREATE OR REPLACE FUNCTION atlas.supersede_reference_assertion(
    p_previous_assertion_id uuid,
    p_replacement_assertion_id uuid,
    p_assertion_status text,
    p_available_at timestamptz,
    p_availability_status text,
    p_recorded_at timestamptz,
    p_rationale text,
    p_source_record text,
    p_provenance jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SET search_path = pg_catalog, atlas
AS $function$
DECLARE
    previous_assertion atlas.reference_assertion%ROWTYPE;
BEGIN
    SELECT * INTO previous_assertion
    FROM atlas.reference_assertion
    WHERE assertion_id = p_previous_assertion_id
      AND recorded_to IS NULL
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'current assertion % does not exist', p_previous_assertion_id
            USING ERRCODE = 'P0002';
    END IF;
    IF p_recorded_at <= previous_assertion.recorded_from THEN
        RAISE EXCEPTION 'replacement record time must follow prior version'
            USING ERRCODE = '22007';
    END IF;

    UPDATE atlas.reference_assertion
    SET recorded_to = p_recorded_at
    WHERE assertion_id = previous_assertion.assertion_id;

    INSERT INTO atlas.reference_assertion (
        assertion_id, assertion_key, edge_type,
        source_node_id, source_node_type, target_node_id, target_node_type,
        relationship_kind, assertion_status, rationale,
        valid_from, valid_to, available_at, availability_status,
        recorded_from, source_record, provenance
    ) VALUES (
        p_replacement_assertion_id, previous_assertion.assertion_key,
        previous_assertion.edge_type,
        previous_assertion.source_node_id, previous_assertion.source_node_type,
        previous_assertion.target_node_id, previous_assertion.target_node_type,
        previous_assertion.relationship_kind, p_assertion_status, p_rationale,
        previous_assertion.valid_from, previous_assertion.valid_to,
        p_available_at, p_availability_status, p_recorded_at,
        p_source_record, p_provenance
    );
    RETURN p_replacement_assertion_id;
END
$function$;

CREATE OR REPLACE FUNCTION atlas.relationships_as_of(
    p_effective_as_of date,
    p_knowledge_cutoff timestamptz DEFAULT NULL,
    p_system_cutoff timestamptz DEFAULT NULL
)
RETURNS TABLE (
    assertion_id uuid,
    assertion_key uuid,
    edge_type text,
    source_node_id uuid,
    source_node_type text,
    target_node_id uuid,
    target_node_type text,
    relationship_kind text,
    assertion_status text,
    valid_from date,
    valid_to date,
    available_at timestamptz,
    availability_status text,
    recorded_from timestamptz,
    recorded_to timestamptz,
    source_record text,
    provenance jsonb,
    history_support text
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        assertion_id, assertion_key, edge_type,
        source_node_id, source_node_type, target_node_id, target_node_type,
        relationship_kind, assertion_status,
        valid_from, valid_to, available_at, availability_status,
        recorded_from, recorded_to, source_record, provenance,
        CASE
            WHEN p_knowledge_cutoff IS NULL THEN 'current_context'
            WHEN availability_status = 'known' THEN 'supported'
            ELSE 'unsupported_history'
        END AS history_support
    FROM atlas.reference_assertion
    WHERE valid_from <= p_effective_as_of
      AND (valid_to IS NULL OR p_effective_as_of < valid_to)
      AND (
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

CREATE OR REPLACE FUNCTION atlas.bounded_paths(
    p_start_node_id uuid,
    p_effective_as_of date,
    p_knowledge_cutoff timestamptz DEFAULT NULL,
    p_system_cutoff timestamptz DEFAULT NULL,
    p_max_depth integer DEFAULT 4
)
RETURNS TABLE (
    endpoint_node_id uuid,
    depth integer,
    node_path uuid[],
    assertion_path uuid[],
    edge_type_path text[],
    assertion_status_path text[]
)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
    IF p_max_depth NOT BETWEEN 1 AND 6 THEN
        RAISE EXCEPTION 'max depth must be between 1 and 6' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    WITH RECURSIVE visible AS (
        SELECT *
        FROM atlas.relationships_as_of(
            p_effective_as_of, p_knowledge_cutoff, p_system_cutoff
        )
        WHERE assertion_status IN ('accepted', 'disputed')
          AND history_support IN ('supported', 'current_context')
    ), paths AS (
        SELECT
            visible.target_node_id AS endpoint_node_id,
            1 AS depth,
            ARRAY[p_start_node_id, visible.target_node_id] AS node_path,
            ARRAY[visible.assertion_id] AS assertion_path,
            ARRAY[visible.edge_type] AS edge_type_path,
            ARRAY[visible.assertion_status] AS assertion_status_path
        FROM visible
        WHERE visible.source_node_id = p_start_node_id

        UNION ALL

        SELECT
            visible.target_node_id,
            paths.depth + 1,
            paths.node_path || visible.target_node_id,
            paths.assertion_path || visible.assertion_id,
            paths.edge_type_path || visible.edge_type,
            paths.assertion_status_path || visible.assertion_status
        FROM paths
        JOIN visible ON visible.source_node_id = paths.endpoint_node_id
        WHERE paths.depth < p_max_depth
          AND NOT visible.target_node_id = ANY(paths.node_path)
    )
    SELECT * FROM paths;
END
$function$;

RESET ROLE;
