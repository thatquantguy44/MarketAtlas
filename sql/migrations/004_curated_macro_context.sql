SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas.curated_macro_context_version (
    curated_macro_context_version_id uuid PRIMARY KEY,
    context_key uuid NOT NULL,
    macro_series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    target_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    target_node_type text NOT NULL REFERENCES atlas.node_type(node_type),
    mapping_kind text NOT NULL CHECK (
        mapping_kind IN ('series_country', 'series_concept', 'market_context')
    ),
    evidence_basis text NOT NULL CHECK (evidence_basis IN ('source_backed', 'curated')),
    semantic_label text NOT NULL DEFAULT 'context_only_not_measured_sensitivity_or_causality'
        CHECK (semantic_label = 'context_only_not_measured_sensitivity_or_causality'),
    rationale text NOT NULL CHECK (rationale <> ''),
    mapping_owner text NOT NULL CHECK (mapping_owner <> ''),
    source_reference text NOT NULL CHECK (source_reference <> ''),
    taxonomy_provider text NOT NULL CHECK (taxonomy_provider <> ''),
    taxonomy_version text NOT NULL CHECK (taxonomy_version <> ''),
    supporting_assertion_id uuid NOT NULL REFERENCES atlas.reference_assertion(assertion_id),
    valid_from date NOT NULL,
    valid_to date,
    available_at timestamptz,
    availability_status text NOT NULL
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL CHECK (source_record <> ''),
    recorded_from timestamptz NOT NULL,
    recorded_to timestamptz,
    provenance jsonb NOT NULL,
    CHECK (
        (mapping_kind = 'series_country' AND target_node_type = 'country')
        OR (mapping_kind = 'series_concept' AND target_node_type = 'economic_concept')
        OR (
            mapping_kind = 'market_context'
            AND target_node_type IN ('instrument', 'sector', 'industry', 'index')
        )
    ),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (context_key, recorded_from),
    UNIQUE (source_record, recorded_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_curated_macro_context_current_key
    ON atlas.curated_macro_context_version (context_key)
    WHERE recorded_to IS NULL;
CREATE INDEX IF NOT EXISTS ix_curated_macro_context_as_of
    ON atlas.curated_macro_context_version (
        macro_series_node_id, target_node_id, available_at
    );

CREATE OR REPLACE FUNCTION atlas.validate_curated_macro_context_version()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, atlas
AS $function$
DECLARE
    macro_type text;
    actual_target_type text;
    support atlas.reference_assertion%ROWTYPE;
BEGIN
    SELECT node_type INTO macro_type
    FROM atlas.node
    WHERE node_id = NEW.macro_series_node_id;
    IF macro_type <> 'macro_series' THEN
        RAISE EXCEPTION 'curated context source must be a macro series' USING ERRCODE = '23514';
    END IF;

    SELECT node_type INTO actual_target_type
    FROM atlas.node
    WHERE node_id = NEW.target_node_id;
    IF actual_target_type IS DISTINCT FROM NEW.target_node_type THEN
        RAISE EXCEPTION 'curated context target type does not match target node' USING ERRCODE = '23514';
    END IF;

    SELECT * INTO support
    FROM atlas.reference_assertion
    WHERE assertion_id = NEW.supporting_assertion_id;
    IF NOT FOUND
       OR NOT (
           (support.source_node_id = NEW.macro_series_node_id AND support.target_node_id = NEW.target_node_id)
           OR (support.source_node_id = NEW.target_node_id AND support.target_node_id = NEW.macro_series_node_id)
       ) THEN
        RAISE EXCEPTION 'supporting assertion must connect the macro series and context target'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.evidence_basis = 'source_backed' AND support.relationship_kind <> 'reference' THEN
        RAISE EXCEPTION 'source-backed context requires a reference assertion' USING ERRCODE = '23514';
    END IF;
    IF NEW.evidence_basis = 'curated' AND support.relationship_kind <> 'curated_context' THEN
        RAISE EXCEPTION 'curated context requires a curated-context assertion' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

DROP TRIGGER IF EXISTS trg_validate_curated_macro_context_version
    ON atlas.curated_macro_context_version;
CREATE TRIGGER trg_validate_curated_macro_context_version
BEFORE INSERT OR UPDATE ON atlas.curated_macro_context_version
FOR EACH ROW EXECUTE FUNCTION atlas.validate_curated_macro_context_version();

CREATE OR REPLACE FUNCTION atlas.curated_macro_context_as_of(
    p_effective_as_of date,
    p_knowledge_cutoff timestamptz DEFAULT NULL,
    p_system_cutoff timestamptz DEFAULT NULL
)
RETURNS TABLE (
    curated_macro_context_version_id uuid,
    macro_series_node_id uuid,
    target_node_id uuid,
    target_node_type text,
    mapping_kind text,
    evidence_basis text,
    semantic_label text,
    rationale text,
    mapping_owner text,
    source_reference text,
    taxonomy_provider text,
    taxonomy_version text,
    supporting_assertion_id uuid,
    input_manifest_id uuid,
    source_record text,
    history_support text
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        curated_macro_context_version_id, macro_series_node_id, target_node_id,
        target_node_type, mapping_kind, evidence_basis, semantic_label, rationale,
        mapping_owner, source_reference, taxonomy_provider, taxonomy_version,
        supporting_assertion_id, input_manifest_id, source_record,
        CASE
            WHEN p_knowledge_cutoff IS NULL THEN 'current_context'
            WHEN availability_status = 'known' THEN 'supported'
            ELSE 'unsupported_history'
        END AS history_support
    FROM atlas.curated_macro_context_version
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

RESET ROLE;
