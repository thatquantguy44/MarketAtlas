"""Opt-in PostgreSQL tests; every synthetic write rolls back, including publication."""

import copy
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from test_revision_quality_publication import synthetic_extract

from market_atlas.config import load_target_database
from market_atlas.contracts import sha256
from market_atlas.ingestion.macro_medallion import _connect, stable_id
from market_atlas.publishing import revision_quality


@unittest.skipUnless(
    os.environ.get("MARKETATLAS_TEST_DATABASE") == "1", "opt-in local database test"
)
class RevisionQualityDatabaseTests(unittest.TestCase):
    def test_publication_reuse_unknown_versions_failure_rollback_and_permissions(self):
        from psycopg.types.json import Jsonb

        config = load_target_database()
        extract = synthetic_extract()
        baseline_input = stable_id("t017-test-input", "synthetic")
        # Borrow one connection so the outer rollback includes all savepoints.
        with (
            _connect(config) as connection,
            connection.transaction(force_rollback=True),
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """INSERT INTO atlas.input_manifest (
                    input_manifest_id, source_name, source_object, source_snapshot_reference,
                    manifest_sha256, extracted_at, redistribution_status, manifest
                ) VALUES (%s,'synthetic-t017-test','synthetic','synthetic',%s,now(),'synthetic',%s)""",
                (
                    baseline_input,
                    sha256("synthetic-t017-test"),
                    Jsonb({"synthetic": True}),
                ),
            )
            nodes = {}
            for series_id in extract["manifest"]["series_ids"]:
                node_id = stable_id("t017-test-node", series_id)
                nodes[series_id] = node_id
                cursor.execute(
                    """INSERT INTO atlas.node (node_id,node_type,canonical_key,display_label)
                       VALUES (%s,'macro_series',%s,%s)""",
                    (node_id, f"synthetic-t017:{series_id}", series_id),
                )
                cursor.execute(
                    """INSERT INTO atlas.macro_series_taxonomy_current (
                        macro_series_taxonomy_id,series_node_id,series_id,input_manifest_id,
                        source_record,source_extracted_at
                    ) VALUES (%s,%s,%s,%s,%s,now())""",
                    (
                        stable_id("t017-test-taxonomy", series_id),
                        node_id,
                        series_id,
                        baseline_input,
                        f"synthetic-t017:{series_id}",
                    ),
                )

            @contextmanager
            def borrow_connection(_config):
                yield connection

            def publication():
                cursor.execute(
                    "SELECT serving_snapshot_id::text FROM atlas.publication WHERE publication_name=%s",
                    (revision_quality.PUBLICATION_NAME,),
                )
                return cursor.fetchone()[0]

            cursor.execute(
                "SELECT publication_name,serving_snapshot_id FROM atlas.publication WHERE publication_name<>%s ORDER BY 1",
                (revision_quality.PUBLICATION_NAME,),
            )
            other_publications = cursor.fetchall()
            with (
                patch.object(revision_quality, "_connect", borrow_connection),
                patch.object(
                    revision_quality,
                    "_code_revision",
                    return_value="synthetic-t017-test-v1",
                ),
            ):
                first = revision_quality.publish_revision_quality(config, extract)
                self.assertEqual(
                    "revision_quality_snapshot_published", first["status"], first
                )
                self.assertEqual(2, first["row_count"])
                second = revision_quality.publish_revision_quality(config, extract)
                self.assertEqual("revision_quality_snapshot_reused", second["status"])
                self.assertEqual(first["snapshot_id"], second["snapshot_id"])
                cursor.execute(
                    """SELECT series_id, details->>'quality_status', details->'observation_count'
                       FROM atlas_report.macro_revision_quality_snapshot WHERE serving_snapshot_id=%s ORDER BY series_id""",
                    (first["snapshot_id"],),
                )
                self.assertEqual(
                    [("SYNTH_A", "available", 12), ("SYNTH_MISSING", "unknown", None)],
                    cursor.fetchall(),
                )
                cursor.execute(
                    "SELECT count(*) FROM atlas_report.provenance_snapshot WHERE serving_snapshot_id=%s AND provenance_kind='macro_revision_quality'",
                    (first["snapshot_id"],),
                )
                self.assertEqual(2, cursor.fetchone()[0])

                failed_extract = copy.deepcopy(extract)
                failed_extract["manifest"]["extracted_at"] = "2026-10-26T18:01:00+00:00"
                original_materialize = revision_quality._materialize_snapshot

                def fail_after_materialization(*args):
                    original_materialize(*args)
                    raise RuntimeError("synthetic failure after all rows were written")

                with patch.object(
                    revision_quality,
                    "_materialize_snapshot",
                    fail_after_materialization,
                ):
                    failed = revision_quality.publish_revision_quality(
                        config, failed_extract
                    )
                self.assertEqual("revision_quality_snapshot_failed", failed["status"])
                self.assertEqual(first["snapshot_id"], publication())
                for table in (
                    "atlas_report.macro_revision_quality_snapshot",
                    "atlas_report.provenance_snapshot",
                ):
                    cursor.execute(
                        f"SELECT count(*) FROM {table} WHERE serving_snapshot_id=%s",
                        (failed["snapshot_id"],),
                    )
                    self.assertEqual(0, cursor.fetchone()[0])
                cursor.execute(
                    "SELECT count(*) FROM atlas.macro_revision_quality_version WHERE series_id = ANY(%s)",
                    (extract["manifest"]["series_ids"],),
                )
                self.assertEqual(2, cursor.fetchone()[0])

                recovered = revision_quality.publish_revision_quality(
                    config, failed_extract
                )
                self.assertEqual(
                    "revision_quality_snapshot_published", recovered["status"]
                )
                self.assertEqual(failed["snapshot_id"], recovered["snapshot_id"])
                self.assertEqual(recovered["snapshot_id"], publication())
                # Replaying an older file cannot silently roll the pointer back.
                old = revision_quality.publish_revision_quality(config, extract)
                self.assertEqual("superseded", old["snapshot_status"])
                self.assertEqual(recovered["snapshot_id"], publication())
                cursor.execute(
                    "SELECT count(*) FROM atlas.macro_revision_quality_version WHERE series_id = ANY(%s)",
                    (extract["manifest"]["series_ids"],),
                )
                self.assertEqual(4, cursor.fetchone()[0])
            cursor.execute(
                "SELECT publication_name,serving_snapshot_id FROM atlas.publication WHERE publication_name<>%s ORDER BY 1",
                (revision_quality.PUBLICATION_NAME,),
            )
            self.assertEqual(other_publications, cursor.fetchall())
            cursor.execute("SELECT 'atlas'::regnamespace::oid")
            atlas_schema_oid = cursor.fetchone()[0]
            cursor.execute("SET LOCAL ROLE marketatlas_report_reader")
            cursor.execute(
                "SELECT count(*) FROM atlas_report.current_macro_revision_quality"
            )
            self.assertEqual(2, cursor.fetchone()[0])
            cursor.execute(
                "SELECT has_table_privilege(current_user,'atlas_report.macro_revision_quality_snapshot','INSERT,UPDATE,DELETE'), has_schema_privilege(current_user,%s,'USAGE')",
                (atlas_schema_oid,),
            )
            self.assertEqual((False, False), cursor.fetchone())


if __name__ == "__main__":
    unittest.main()
