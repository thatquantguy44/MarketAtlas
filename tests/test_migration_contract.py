import unittest
from pathlib import Path


class MigrationContractTests(unittest.TestCase):
    def test_identity_migration_contains_required_guards(self):
        sql = Path("sql/migrations/001_identity_ontology.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE SCHEMA IF NOT EXISTS atlas",
            "CREATE SCHEMA IF NOT EXISTS atlas_report",
            "CREATE TABLE IF NOT EXISTS atlas.node",
            "CREATE TABLE IF NOT EXISTS atlas.node_identifier",
            "CREATE TABLE IF NOT EXISTS atlas.reference_assertion",
            "FOREIGN KEY (edge_type, source_node_type, target_node_type)",
            "trg_node_identifier_no_overlap",
            "marketatlas_source_reader",
            "marketatlas_writer",
            "marketatlas_report_reader",
        ):
            self.assertIn(required, sql)

    def test_observation_migration_declares_versions_and_as_of_selection(self):
        sql = Path("sql/migrations/003_observation_versions.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE TABLE IF NOT EXISTS atlas.input_manifest",
            "CREATE TABLE IF NOT EXISTS atlas.market_calendar_session",
            "CREATE TABLE IF NOT EXISTS atlas.market_observation_version",
            "CREATE TABLE IF NOT EXISTS atlas.macro_observation_version",
            "atlas.market_observations_as_of",
            "atlas.macro_observations_as_of",
            "unsupported_adjusted_history",
            "unsupported_history",
        ):
            self.assertIn(required, sql)

    def test_curated_context_migration_requires_provenance_and_label(self):
        sql = Path("sql/migrations/004_curated_macro_context.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE TABLE IF NOT EXISTS atlas.curated_macro_context_version",
            "mapping_owner text NOT NULL",
            "source_reference text NOT NULL",
            "taxonomy_provider text NOT NULL",
            "taxonomy_version text NOT NULL",
            "context_only_not_measured_sensitivity_or_causality",
            "atlas.validate_curated_macro_context_version",
            "atlas.curated_macro_context_as_of",
        ):
            self.assertIn(required, sql)

    def test_correlation_migration_declares_fixed_window_and_statuses(self):
        sql = Path("sql/migrations/005_rolling_correlation_estimates.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE TABLE IF NOT EXISTS atlas.rolling_correlation_estimate_version",
            "window_session_count = 60",
            "minimum_paired_return_count = 45",
            "insufficient_sample",
            "zero_variance",
            "incompatible_input",
            "unsupported_history",
            "input_selection_sha256",
            "atlas.validate_rolling_correlation_estimate_version",
        ):
            self.assertIn(required, sql)

    def test_build_migration_declares_atomic_publication_contract(self):
        sql = Path("sql/migrations/006_build_publication.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE TABLE IF NOT EXISTS atlas.build_run",
            "CREATE TABLE IF NOT EXISTS atlas.serving_snapshot",
            "CREATE TABLE IF NOT EXISTS atlas.publication",
            "rolling_correlation_estimate_snapshot",
            "atlas.publish_serving_snapshot",
            "snapshot_status = 'validated'",
            "snapshot_status = 'superseded'",
            "current_rolling_correlation_estimate",
        ):
            self.assertIn(required, sql)

    def test_reporting_migration_declares_snapshot_pinned_grains(self):
        sql = Path("sql/migrations/007_reporting_provenance.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "CREATE TABLE IF NOT EXISTS atlas_report.node_snapshot",
            "CREATE TABLE IF NOT EXISTS atlas_report.relationship_snapshot",
            "CREATE TABLE IF NOT EXISTS atlas_report.macro_context_snapshot",
            "CREATE TABLE IF NOT EXISTS atlas_report.bounded_path_snapshot",
            "CREATE TABLE IF NOT EXISTS atlas_report.provenance_snapshot",
            "current_snapshot_metadata",
            "current_node_dimension",
            "current_relationship_fact",
            "current_macro_context_fact",
            "current_bounded_path_bridge",
            "current_provenance",
        ):
            self.assertIn(required, sql)

    def test_fixture_publisher_excludes_non_synthetic_nodes(self):
        implementation = Path("src/market_atlas/publishing/fixture_build.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "WHERE provenance->>'source' = 'synthetic-fixture'", implementation
        )

    def test_source_catalog_migration_is_read_only_and_excludes_agent_tables(self):
        sql = Path("sql/migrations/008_source_catalog_reader_scope.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "GRANT SELECT ON ALL TABLES IN SCHEMA audit, bronze, gold, meta, silver",
            sql,
        )
        self.assertIn("marketatlas_source_reader", sql)
        self.assertNotIn("public", sql.split("GRANT USAGE")[1])
        self.assertNotIn("ALTER DEFAULT PRIVILEGES", sql)

    def test_macro_context_publication_preserves_current_only_semantics(self):
        sql = Path("sql/migrations/009_macro_context_publication.sql").read_text(
            encoding="utf-8"
        )
        for required in (
            "atlas.macro_series_taxonomy_current",
            "atlas.macro_release_event_current",
            "atlas.macro_source_coverage_current",
            "atlas_report.macro_source_context_snapshot",
            "temporal_status = 'current_only'",
            "temporal_status = 'scheduled_event'",
            "'macro_source_context'",
            "current_macro_source_context",
        ):
            self.assertIn(required, sql)


if __name__ == "__main__":
    unittest.main()
