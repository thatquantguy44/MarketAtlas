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


if __name__ == "__main__":
    unittest.main()
