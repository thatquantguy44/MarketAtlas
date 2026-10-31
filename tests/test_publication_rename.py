"""The fixture rename preserves snapshots and never replaces a live pointer."""

import os
import unittest
from pathlib import Path

from market_atlas.publishing.fixture_build import PUBLICATION_NAME, _build_configuration
from market_atlas.reporting.export import TABLES

MIGRATION = Path("sql/migrations/012_rename_synthetic_fixture_publication.sql")


class PublicationNameTests(unittest.TestCase):
    def test_fixture_producer_exporter_and_template_use_the_explicit_name(self):
        self.assertEqual(PUBLICATION_NAME, "synthetic_fixture")
        self.assertEqual(
            _build_configuration(None, None)["publication"], PUBLICATION_NAME
        )
        self.assertIn(PUBLICATION_NAME, TABLES)
        self.assertNotIn("default", TABLES)
        template = Path("powerbi/MarketAtlas.model.template.tmdl").read_text()
        self.assertIn('expression pPublicationName = "synthetic_fixture"', template)


@unittest.skipUnless(
    os.environ.get("MARKETATLAS_TEST_DATABASE") == "1",
    "opt-in rollback-isolated database test",
)
class PublicationRenameDatabaseTests(unittest.TestCase):
    def test_rename_preserves_history_is_repeatable_and_rejects_conflicts(self):
        import psycopg

        from market_atlas.config import load_target_database

        with (
            psycopg.connect(**load_target_database().connection_kwargs()) as connection,
            connection.transaction(force_rollback=True),
            connection.cursor() as cursor,
        ):
            cursor.execute("SET LOCAL ROLE marketatlas_writer")
            cursor.execute(
                "SELECT publication_name, serving_snapshot_id, published_at FROM atlas.publication ORDER BY publication_name"
            )
            before = {
                name: (snapshot, timestamp)
                for name, snapshot, timestamp in cursor.fetchall()
            }
            fixture = before.get("synthetic_fixture", before.get("default"))
            if fixture is None:
                self.skipTest("a retained fixture publication is required")
            others = {
                k: v
                for k, v in before.items()
                if k not in {"default", "synthetic_fixture"}
            }
            # Recreate the pre-migration state only inside this rollback.
            cursor.execute(
                "ALTER TABLE atlas.publication DROP CONSTRAINT IF EXISTS publication_explicit_fixture_name"
            )
            cursor.execute(
                "DELETE FROM atlas.publication WHERE publication_name IN ('default', 'synthetic_fixture')"
            )
            cursor.execute(
                "INSERT INTO atlas.publication VALUES ('default', %s, %s)", fixture
            )
            cursor.execute("SELECT count(*) FROM atlas.serving_snapshot")
            snapshot_count = cursor.fetchone()[0]
            migration = MIGRATION.read_text()
            cursor.execute(migration)
            cursor.execute(migration)
            cursor.execute(
                "SELECT publication_name, serving_snapshot_id, published_at FROM atlas.publication ORDER BY publication_name"
            )
            after = {
                name: (snapshot, timestamp)
                for name, snapshot, timestamp in cursor.fetchall()
            }
            self.assertEqual(after, {**others, "synthetic_fixture": fixture})
            cursor.execute("SELECT count(*) FROM atlas.serving_snapshot")
            self.assertEqual(cursor.fetchone()[0], snapshot_count)
            with (
                self.assertRaises(psycopg.errors.CheckViolation),
                connection.transaction(),
            ):
                cursor.execute(
                    "INSERT INTO atlas.publication VALUES ('default', %s, %s)",
                    fixture,
                )
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            cursor.execute(
                "SELECT serving_snapshot_id, published_at FROM atlas_report.current_snapshot_metadata WHERE publication_name = 'synthetic_fixture'"
            )
            self.assertEqual(cursor.fetchone(), fixture)
            cursor.execute("SET LOCAL ROLE marketatlas_writer")
            cursor.execute(
                "ALTER TABLE atlas.publication DROP CONSTRAINT publication_explicit_fixture_name"
            )
            cursor.execute(
                "INSERT INTO atlas.publication VALUES ('default', %s, %s)", fixture
            )
            with (
                self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "refusing to replace either pointer",
                ),
                connection.transaction(),
            ):
                cursor.execute(migration)
            cursor.execute(
                "SELECT count(*) FROM atlas.publication WHERE publication_name IN ('default', 'synthetic_fixture')"
            )
            self.assertEqual(cursor.fetchone()[0], 2)
