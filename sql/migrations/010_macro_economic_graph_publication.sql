SET ROLE marketatlas_writer;

-- A projection of current source taxonomy. It deliberately does not claim taxonomy history.
CREATE TABLE IF NOT EXISTS atlas.macro_taxonomy_concept_current (
    macro_taxonomy_concept_id uuid PRIMARY KEY,
    series_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    economic_concept_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL UNIQUE,
    temporal_status text NOT NULL DEFAULT 'current_only'
        CHECK (temporal_status = 'current_only'),
    source_extracted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (series_node_id, economic_concept_node_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.macro_economic_graph_node_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    node_type text NOT NULL,
    display_label text NOT NULL,
    temporal_status text NOT NULL CHECK (temporal_status = 'current_only'),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL,
    details jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, node_id)
);

CREATE TABLE IF NOT EXISTS atlas_report.macro_economic_graph_edge_snapshot (
    serving_snapshot_id uuid NOT NULL REFERENCES atlas.serving_snapshot(serving_snapshot_id),
    assertion_id uuid NOT NULL REFERENCES atlas.reference_assertion(assertion_id),
    edge_type text NOT NULL CHECK (edge_type = 'measures'),
    source_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    target_node_id uuid NOT NULL REFERENCES atlas.node(node_id),
    temporal_status text NOT NULL CHECK (temporal_status = 'current_only'),
    input_manifest_id uuid NOT NULL REFERENCES atlas.input_manifest(input_manifest_id),
    source_record text NOT NULL,
    provenance jsonb NOT NULL,
    PRIMARY KEY (serving_snapshot_id, assertion_id)
);

ALTER TABLE atlas_report.provenance_snapshot
    DROP CONSTRAINT IF EXISTS provenance_snapshot_provenance_kind_check;
ALTER TABLE atlas_report.provenance_snapshot
    ADD CONSTRAINT provenance_snapshot_provenance_kind_check CHECK (
        provenance_kind IN (
            'relationship', 'macro_context', 'rolling_correlation',
            'macro_source_context', 'macro_economic_graph'
        )
    );

CREATE INDEX IF NOT EXISTS ix_report_macro_economic_graph_edges_source
    ON atlas_report.macro_economic_graph_edge_snapshot (serving_snapshot_id, source_node_id);

CREATE OR REPLACE VIEW atlas_report.current_macro_economic_graph_node AS
SELECT publication.publication_name, publication.published_at, snapshot.*
FROM atlas.publication AS publication
JOIN atlas_report.macro_economic_graph_node_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id
WHERE publication.publication_name = 'macro_economic_graph';

CREATE OR REPLACE VIEW atlas_report.current_macro_economic_graph_edge AS
SELECT publication.publication_name, publication.published_at, snapshot.*
FROM atlas.publication AS publication
JOIN atlas_report.macro_economic_graph_edge_snapshot AS snapshot
  ON snapshot.serving_snapshot_id = publication.serving_snapshot_id
WHERE publication.publication_name = 'macro_economic_graph';

GRANT SELECT ON ALL TABLES IN SCHEMA atlas_report TO marketatlas_report_reader;

RESET ROLE;
