DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'marketatlas_source_reader') THEN
        CREATE ROLE marketatlas_source_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'marketatlas_writer') THEN
        CREATE ROLE marketatlas_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'marketatlas_report_reader') THEN
        CREATE ROLE marketatlas_report_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('marketatlas_source_reader', 'marketatlas_writer', 'marketatlas_report_reader')
          AND rolcanlogin
    ) THEN
        RAISE EXCEPTION 'MarketAtlas group roles must be NOLOGIN';
    END IF;

    EXECUTE format('GRANT marketatlas_source_reader TO %I', current_user);
    EXECUTE format('GRANT marketatlas_writer TO %I', current_user);
    EXECUTE format('GRANT marketatlas_report_reader TO %I', current_user);
END
$roles$;

GRANT USAGE ON SCHEMA meta, gold TO marketatlas_source_reader;
GRANT SELECT ON TABLE meta.fred_series, gold.fred_point_in_time TO marketatlas_source_reader;

CREATE SCHEMA IF NOT EXISTS atlas AUTHORIZATION marketatlas_writer;
CREATE SCHEMA IF NOT EXISTS atlas_report AUTHORIZATION marketatlas_writer;
REVOKE ALL ON SCHEMA atlas, atlas_report FROM PUBLIC;
GRANT USAGE ON SCHEMA atlas_report TO marketatlas_report_reader;

SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas.schema_migration (
    version text PRIMARY KEY,
    checksum_sha256 text NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    applied_by text NOT NULL DEFAULT session_user
);

CREATE TABLE IF NOT EXISTS atlas.node_type (
    node_type text PRIMARY KEY CHECK (node_type ~ '^[a-z][a-z0-9_]*$'),
    description text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS atlas.edge_type (
    edge_type text PRIMARY KEY CHECK (edge_type ~ '^[a-z][a-z0-9_]*$'),
    description text NOT NULL,
    direction text NOT NULL DEFAULT 'directed' CHECK (direction IN ('directed', 'undirected')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS atlas.edge_endpoint_rule (
    edge_type text NOT NULL REFERENCES atlas.edge_type(edge_type),
    source_node_type text NOT NULL REFERENCES atlas.node_type(node_type),
    target_node_type text NOT NULL REFERENCES atlas.node_type(node_type),
    PRIMARY KEY (edge_type, source_node_type, target_node_type)
);

CREATE TABLE IF NOT EXISTS atlas.node (
    node_id uuid PRIMARY KEY,
    node_type text NOT NULL REFERENCES atlas.node_type(node_type),
    canonical_key text NOT NULL CHECK (canonical_key <> ''),
    display_label text NOT NULL CHECK (display_label <> ''),
    entity_status text NOT NULL DEFAULT 'active'
        CHECK (entity_status IN ('active', 'inactive', 'disputed', 'unknown')),
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (node_type, canonical_key),
    UNIQUE (node_id, node_type)
);

CREATE TABLE IF NOT EXISTS atlas.node_attribute_version (
    node_attribute_version_id uuid PRIMARY KEY,
    node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    attribute_name text NOT NULL CHECK (attribute_name <> ''),
    attribute_value jsonb NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    available_at timestamptz,
    availability_status text NOT NULL DEFAULT 'known'
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    recorded_from timestamptz NOT NULL DEFAULT clock_timestamp(),
    recorded_to timestamptz,
    provenance jsonb NOT NULL,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (node_id, attribute_name, valid_from, recorded_from)
);

CREATE TABLE IF NOT EXISTS atlas.node_identifier (
    node_identifier_id uuid PRIMARY KEY,
    node_id uuid NOT NULL,
    node_type text NOT NULL,
    source_name text NOT NULL CHECK (source_name <> ''),
    identifier_scheme text NOT NULL CHECK (identifier_scheme <> ''),
    identifier_value text NOT NULL CHECK (identifier_value <> ''),
    valid_from date NOT NULL,
    valid_to date,
    available_at timestamptz,
    availability_status text NOT NULL DEFAULT 'known'
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    recorded_from timestamptz NOT NULL DEFAULT clock_timestamp(),
    recorded_to timestamptz,
    mapping_status text NOT NULL DEFAULT 'accepted'
        CHECK (mapping_status IN ('accepted', 'disputed', 'retracted', 'quarantined')),
    provenance jsonb NOT NULL,
    FOREIGN KEY (node_id, node_type) REFERENCES atlas.node(node_id, node_type),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    UNIQUE (source_name, identifier_scheme, identifier_value, valid_from, recorded_from)
);

CREATE INDEX IF NOT EXISTS ix_node_identifier_lookup
    ON atlas.node_identifier (source_name, identifier_scheme, identifier_value);
CREATE INDEX IF NOT EXISTS ix_node_identifier_node
    ON atlas.node_identifier (node_id, valid_from);

CREATE OR REPLACE FUNCTION atlas.reject_overlapping_identifiers()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, atlas
AS $function$
BEGIN
    IF NEW.mapping_status <> 'accepted' THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            concat_ws(E'\x1f', NEW.source_name, NEW.identifier_scheme, NEW.identifier_value),
            0
        )
    );

    IF EXISTS (
        SELECT 1
        FROM atlas.node_identifier AS existing
        WHERE existing.node_identifier_id <> NEW.node_identifier_id
          AND existing.source_name = NEW.source_name
          AND existing.identifier_scheme = NEW.identifier_scheme
          AND existing.identifier_value = NEW.identifier_value
          AND existing.mapping_status = 'accepted'
          AND existing.recorded_to IS NULL
          AND daterange(existing.valid_from, existing.valid_to, '[)')
              && daterange(NEW.valid_from, NEW.valid_to, '[)')
    ) THEN
        RAISE EXCEPTION USING
            ERRCODE = '23505',
            MESSAGE = 'overlapping accepted source identifier mapping',
            DETAIL = concat_ws(':', NEW.source_name, NEW.identifier_scheme, NEW.identifier_value);
    END IF;
    RETURN NEW;
END
$function$;

DROP TRIGGER IF EXISTS trg_node_identifier_no_overlap ON atlas.node_identifier;
CREATE TRIGGER trg_node_identifier_no_overlap
BEFORE INSERT OR UPDATE ON atlas.node_identifier
FOR EACH ROW EXECUTE FUNCTION atlas.reject_overlapping_identifiers();

CREATE TABLE IF NOT EXISTS atlas.reference_assertion (
    assertion_id uuid PRIMARY KEY,
    edge_type text NOT NULL,
    source_node_id uuid NOT NULL,
    source_node_type text NOT NULL,
    target_node_id uuid NOT NULL,
    target_node_type text NOT NULL,
    relationship_kind text NOT NULL
        CHECK (relationship_kind IN ('reference', 'curated_context')),
    assertion_status text NOT NULL DEFAULT 'accepted'
        CHECK (assertion_status IN ('accepted', 'disputed', 'retracted', 'unknown')),
    rationale text,
    valid_from date NOT NULL,
    valid_to date,
    available_at timestamptz,
    availability_status text NOT NULL DEFAULT 'known'
        CHECK (availability_status IN ('known', 'date_only', 'unknown')),
    recorded_from timestamptz NOT NULL DEFAULT clock_timestamp(),
    recorded_to timestamptz,
    source_record text,
    provenance jsonb NOT NULL,
    FOREIGN KEY (source_node_id, source_node_type)
        REFERENCES atlas.node(node_id, node_type),
    FOREIGN KEY (target_node_id, target_node_type)
        REFERENCES atlas.node(node_id, node_type),
    FOREIGN KEY (edge_type, source_node_type, target_node_type)
        REFERENCES atlas.edge_endpoint_rule(edge_type, source_node_type, target_node_type),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (recorded_to IS NULL OR recorded_to > recorded_from),
    CHECK (relationship_kind <> 'curated_context' OR rationale IS NOT NULL),
    CHECK (source_node_id <> target_node_id),
    UNIQUE (edge_type, source_node_id, target_node_id, valid_from, recorded_from)
);

CREATE INDEX IF NOT EXISTS ix_reference_assertion_source
    ON atlas.reference_assertion (source_node_id, edge_type, valid_from);
CREATE INDEX IF NOT EXISTS ix_reference_assertion_target
    ON atlas.reference_assertion (target_node_id, edge_type, valid_from);

CREATE TABLE IF NOT EXISTS atlas.identity_quarantine (
    quarantine_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name text NOT NULL,
    record_type text NOT NULL,
    source_record text,
    payload jsonb NOT NULL,
    reason_code text NOT NULL,
    reason_detail text NOT NULL,
    quarantined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    CHECK (resolved_at IS NULL OR resolved_at >= quarantined_at)
);

INSERT INTO atlas.node_type (node_type, description) VALUES
    ('instrument', 'Tradable or reference financial instrument'),
    ('listing', 'Instrument listing on a market or venue'),
    ('issuer', 'Legal or economic issuer of an instrument'),
    ('organization', 'Organization not represented specifically as an issuer'),
    ('index', 'Index or basket'),
    ('country', 'Country or economy'),
    ('currency', 'Currency denomination'),
    ('sector', 'Sector classification'),
    ('industry', 'Industry classification'),
    ('economic_concept', 'Economic concept measured by a macro series'),
    ('market', 'Trading market or venue'),
    ('macro_series', 'Economic or macroeconomic time series')
ON CONFLICT (node_type) DO NOTHING;

INSERT INTO atlas.edge_type (edge_type, description, direction) VALUES
    ('lists', 'Listing represents an instrument', 'directed'),
    ('issued_by', 'Instrument was issued by an issuer', 'directed'),
    ('classified_as', 'Issuer or instrument has a classification', 'directed'),
    ('member_of', 'Issuer or instrument belongs to an index', 'directed'),
    ('listed_in', 'Listing belongs to a country or market', 'directed'),
    ('denominated_in', 'Instrument is denominated in a currency', 'directed'),
    ('measures', 'Macro series measures an economic concept', 'directed'),
    ('covers', 'Macro series covers a country', 'directed'),
    ('context_for', 'Macro series is curated context for a classification', 'directed')
ON CONFLICT (edge_type) DO NOTHING;

INSERT INTO atlas.edge_endpoint_rule (edge_type, source_node_type, target_node_type) VALUES
    ('lists', 'listing', 'instrument'),
    ('issued_by', 'instrument', 'issuer'),
    ('classified_as', 'issuer', 'sector'),
    ('classified_as', 'issuer', 'industry'),
    ('classified_as', 'instrument', 'sector'),
    ('classified_as', 'instrument', 'industry'),
    ('member_of', 'issuer', 'index'),
    ('member_of', 'instrument', 'index'),
    ('listed_in', 'listing', 'country'),
    ('listed_in', 'listing', 'market'),
    ('denominated_in', 'instrument', 'currency'),
    ('measures', 'macro_series', 'economic_concept'),
    ('covers', 'macro_series', 'country'),
    ('context_for', 'sector', 'macro_series'),
    ('context_for', 'industry', 'macro_series')
ON CONFLICT (edge_type, source_node_type, target_node_type) DO NOTHING;

GRANT SELECT ON ALL TABLES IN SCHEMA atlas TO marketatlas_report_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE marketatlas_writer IN SCHEMA atlas
    GRANT SELECT ON TABLES TO marketatlas_report_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE marketatlas_writer IN SCHEMA atlas_report
    GRANT SELECT ON TABLES TO marketatlas_report_reader;

RESET ROLE;
