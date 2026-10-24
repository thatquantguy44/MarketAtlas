SET ROLE marketatlas_writer;

CREATE TABLE IF NOT EXISTS atlas_report.node_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    node_id uuid NOT NULL,
    node_type text NOT NULL,
    canonical_key text NOT NULL,
    display_label text NOT NULL,
    entity_status text NOT NULL,
    provenance jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, node_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.relationship_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    assertion_id uuid NOT NULL,
    assertion_key uuid NOT NULL,
    edge_type text NOT NULL,
    source_node_id uuid NOT NULL,
    source_node_type text NOT NULL,
    target_node_id uuid NOT NULL,
    target_node_type text NOT NULL,
    relationship_kind text NOT NULL,
    assertion_status text NOT NULL,
    rationale text,
    source_record text,
    provenance jsonb NOT NULL,
    history_support text NOT NULL,
    PRIMARY KEY (serving_snapshot_id, assertion_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.macro_context_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    curated_macro_context_version_id uuid NOT NULL,
    macro_series_node_id uuid NOT NULL,
    target_node_id uuid NOT NULL,
    target_node_type text NOT NULL,
    mapping_kind text NOT NULL,
    evidence_basis text NOT NULL,
    semantic_label text NOT NULL,
    rationale text NOT NULL,
    mapping_owner text NOT NULL,
    source_reference text NOT NULL,
    taxonomy_provider text NOT NULL,
    taxonomy_version text NOT NULL,
    supporting_assertion_id uuid NOT NULL,
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL,
    history_support text NOT NULL,
    PRIMARY KEY (serving_snapshot_id, curated_macro_context_version_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.bounded_path_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    path_key uuid NOT NULL,
    start_node_id uuid NOT NULL,
    endpoint_node_id uuid NOT NULL,
    depth integer NOT NULL CHECK (depth BETWEEN 1 AND 4),
    node_path uuid[] NOT NULL,
    assertion_path uuid[] NOT NULL,
    edge_type_path text[] NOT NULL,
    assertion_status_path text[] NOT NULL,
    PRIMARY KEY (serving_snapshot_id, path_key),
    CHECK (array_length(node_path, 1) = depth + 1),
    CHECK (array_length(assertion_path, 1) = depth),
    CHECK (array_length(edge_type_path, 1) = depth),
    CHECK (array_length(assertion_status_path, 1) = depth)
);

CREATE TABLE IF NOT EXISTS atlas_report.provenance_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    provenance_kind text NOT NULL CHECK (
        provenance_kind IN ('relationship', 'macro_context', 'rolling_correlation')
    ),
    subject_id uuid NOT NULL,
    build_run_id uuid NOT NULL REFERENCES atlas.build_run(build_run_id),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text,
    supporting_assertion_id uuid,
    method_version text,
    configuration_sha256 text,
    input_selection_sha256 text,
    knowledge_cutoff timestamptz,
    details jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, provenance_kind, subject_id)
);

CREATE INDEX IF NOT EXISTS ix_report_relationship_snapshot_source
    ON atlas_report.relationship_snapshot (serving_snapshot_id, source_node_id);
CREATE INDEX IF NOT EXISTS ix_report_context_snapshot_series
    ON atlas_report.macro_context_snapshot (serving_snapshot_id, macro_series_node_id);
CREATE INDEX IF NOT EXISTS ix_report_path_snapshot_start
    ON atlas_report.bounded_path_snapshot (serving_snapshot_id, start_node_id, depth);

CREATE OR REPLACE VIEW atlas_report.current_snapshot_metadata AS
SELECT
    publication.publication_name,
    publication.published_at,
    snapshot.serving_snapshot_id,
    snapshot.build_run_id,
    snapshot.input_manifest_id,
    snapshot.knowledge_cutoff,
    snapshot.output_sha256,
    snapshot.row_count,
    snapshot.validation_summary
FROM atlas.publication AS publication
JOIN atlas.serving_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id;

CREATE OR REPLACE VIEW atlas_report.current_node_dimension AS
SELECT snapshot.*
FROM atlas_report.current_snapshot_metadata AS metadata
JOIN atlas_report.node_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = metadata.serving_snapshot_id;

CREATE OR REPLACE VIEW atlas_report.current_relationship_fact AS
SELECT snapshot.*
FROM atlas_report.current_snapshot_metadata AS metadata
JOIN atlas_report.relationship_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = metadata.serving_snapshot_id;

CREATE OR REPLACE VIEW atlas_report.current_macro_context_fact AS
SELECT snapshot.*
FROM atlas_report.current_snapshot_metadata AS metadata
JOIN atlas_report.macro_context_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = metadata.serving_snapshot_id;

CREATE OR REPLACE VIEW atlas_report.current_bounded_path_bridge AS
SELECT snapshot.*
FROM atlas_report.current_snapshot_metadata AS metadata
JOIN atlas_report.bounded_path_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = metadata.serving_snapshot_id;

CREATE OR REPLACE VIEW atlas_report.current_provenance AS
SELECT snapshot.*
FROM atlas_report.current_snapshot_metadata AS metadata
JOIN atlas_report.provenance_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = metadata.serving_snapshot_id;

GRANT SELECT ON ALL TABLES IN SCHEMA atlas_report TO marketatlas_report_reader;

RESET ROLE;
