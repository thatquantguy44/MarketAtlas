"""Source corrections preserve old system-time facts and remain idempotent."""

import contextlib
import copy
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from test_live_ingestion_contract import source_extract

from market_atlas.config import load_target_database
from market_atlas.contracts import sha256
from market_atlas.ingestion.macro_medallion import _connect, ingest, observation_state


class ObservationStateTests(unittest.TestCase):
    def test_capture_time_does_not_change_fact_identity_but_interval_and_value_do(self):
        source = source_extract()
        entity = source["entities"][0]
        obs = source["macro_observations"][0]
        before = observation_state("node", entity, obs)
        obs["source_ingested_at"] = "2026-10-31T12:00:00+00:00"
        self.assertEqual(before, observation_state("node", entity, obs))
        obs["source_valid_through_inclusive"] = "2024-02-28"
        self.assertNotEqual(before, observation_state("node", entity, obs))
        obs["source_valid_through_inclusive"] = "9999-12-31"
        obs["value"] = "102"
        self.assertNotEqual(before, observation_state("node", entity, obs))


@unittest.skipUnless(
    os.environ.get("MARKETATLAS_TEST_DATABASE") == "1",
    "opt-in PostgreSQL correction regression",
)
class ObservationCorrectionDatabaseTests(unittest.TestCase):
    def test_interval_and_value_corrections_preserve_history_and_replay(self):
        config = load_target_database()
        connection = _connect(config)
        sid = "TEST_CORRECTION_" + uuid4().hex
        source = source_extract()
        entity = source["entities"][0]
        obs = source["macro_observations"][0]
        entity.update(
            canonical_key="macro:fred:" + sid,
            source_identifier=sid,
            category="test",
            active=True,
            vintage_enabled=True,
            load_type="incremental",
            source_metadata_updated_at="2026-10-31T00:00:00+00:00",
        )
        obs.update(
            series_canonical_key=entity["canonical_key"],
            source_record=f"gold.fred_point_in_time:{sid}:2024-01-01:2024-02-01:1",
        )
        source["manifest"]["extracted_at"] = "2026-10-31T12:00:00+00:00"
        source["manifest"]["source_rows_sha256"] = sha256(source["macro_observations"])

        @contextlib.contextmanager
        def isolated(_):
            with connection.transaction():
                yield connection

        try:
            with (
                connection.transaction(force_rollback=True),
                patch("market_atlas.ingestion.macro_medallion._connect", isolated),
            ):
                first = ingest(config, source)
                self.assertEqual(first["macro_observation_inserted_count"], 1)
                self.assertEqual(
                    ingest(config, source)["macro_observation_inserted_count"], 0
                )
                corrected = copy.deepcopy(source)
                corrected["manifest"]["extracted_at"] = "2026-10-31T13:00:00+00:00"
                corrected["macro_observations"][0]["source_valid_through_inclusive"] = (
                    "2024-02-28"
                )
                corrected["manifest"]["source_rows_sha256"] = sha256(
                    corrected["macro_observations"]
                )
                result = ingest(config, corrected)
                self.assertEqual(result["macro_observation_corrected_count"], 1)
                self.assertEqual(
                    ingest(config, corrected)["macro_observation_corrected_count"], 0
                )
                with connection.cursor() as q:
                    q.execute(
                        "SELECT source_valid_through_inclusive,recorded_from,recorded_to,available_at FROM atlas.macro_observation_version WHERE source_record=%s ORDER BY recorded_from",
                        (obs["source_record"],),
                    )
                    rows = q.fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(str(rows[0][0]), "9999-12-31")
                self.assertEqual(rows[0][2], datetime(2026, 10, 31, 13, tzinfo=UTC))
                self.assertEqual(str(rows[1][0]), "2024-02-28")
                self.assertIsNone(rows[1][2])
                self.assertEqual(rows[0][3], rows[1][3])
                with self.assertRaisesRegex(ValueError, "advance"):
                    ingest(config, source)
                second = copy.deepcopy(corrected)
                second["manifest"]["extracted_at"] = "2026-10-31T14:00:00+00:00"
                second["macro_observations"][0]["value"] = "102"
                second["manifest"]["source_rows_sha256"] = sha256(
                    second["macro_observations"]
                )
                self.assertEqual(
                    ingest(config, second)["macro_observation_corrected_count"], 1
                )
                self.assertEqual(
                    ingest(config, second)["macro_observation_inserted_count"], 0
                )
                with connection.cursor() as q:
                    for system_time, expected in (
                        ("2026-10-31T12:30:00+00:00", 101),
                        ("2026-10-31T14:30:00+00:00", 102),
                    ):
                        q.execute(
                            "SELECT value FROM atlas.macro_observations_as_of(%s,%s) WHERE series_node_id=(SELECT node_id FROM atlas.node WHERE canonical_key=%s)",
                            (
                                "2024-02-15T00:00:00+00:00",
                                system_time,
                                entity["canonical_key"],
                            ),
                        )
                        self.assertEqual(q.fetchone()[0], expected)
                precise = copy.deepcopy(second)
                precise["manifest"]["extracted_at"] = "2026-10-31T15:00:00+00:00"
                precise["macro_observations"][0]["value"] = 1.2345678901234567
                precise["manifest"]["source_rows_sha256"] = sha256(
                    precise["macro_observations"]
                )
                self.assertEqual(
                    ingest(config, precise)["macro_observation_corrected_count"], 1
                )
                self.assertEqual(
                    ingest(config, precise)["macro_observation_inserted_count"], 0
                )
        finally:
            connection.rollback()
            connection.close()
