"""A hard SQL result bound prevents client buffering beyond the extraction budget."""

import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from market_atlas.adapters.macro_medallion import extract
from market_atlas.config import MacroMedallionConfig


class Cursor:
    def __init__(self):
        self.calls = []
        self.rows = []
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, params):
        self.calls.append(params)
        self.offset = 0
        if len(params) == 1:
            fields = [
                "series_id",
                "title",
                "category",
                "frequency",
                "units",
                "active",
                "vintage_enabled",
                "load_type",
                "updated_at",
            ]
            self.rows = [
                (
                    key,
                    key,
                    "growth",
                    "m",
                    "Index",
                    1,
                    1,
                    "incremental",
                    "2026-10-30T00:00:00+00:00",
                )
                for key in params[0]
            ]
        else:
            fields = [
                "series_id",
                "observation_date",
                "realtime_start",
                "realtime_end",
                "value",
                "revision_number",
                "is_missing",
                "ingested_at",
            ]
            self.rows = [
                (
                    key,
                    "2024-01-01",
                    "2024-02-01",
                    "9999-12-31",
                    1.0,
                    1,
                    0,
                    "2024-02-01T00:00:00+00:00",
                )
                for key in params[0]
            ][: params[-1]]
        self.description = [SimpleNamespace(name=name) for name in fields]

    def fetchall(self):
        return self.rows

    def fetchmany(self, size):
        rows = self.rows[self.offset : self.offset + size]
        self.offset += len(rows)
        return rows


class ObservationPagingTests(unittest.TestCase):
    def run_extract(self, cursor, limit):
        @contextlib.contextmanager
        def connection(_):
            yield SimpleNamespace(cursor=lambda: cursor)

        pilot = MacroMedallionConfig(
            ("A", "B"), "2024-01-01", "2026-10-30", "2026-10-30", "restricted"
        )
        with patch(
            "market_atlas.adapters.macro_medallion._read_only_connection", connection
        ):
            return extract(None, pilot, max_rows=limit, batch_size=1, page_size=1)

    def test_batches_keep_all_rows_and_shrink_the_sql_budget(self):
        cursor = Cursor()
        result = self.run_extract(cursor, 2)
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(len(result["macro_observations"]), 2)
        self.assertEqual([params[-1] for params in cursor.calls[1:]], [3, 2])

    def test_excess_rows_raise_instead_of_silently_truncating(self):
        with self.assertRaisesRegex(ValueError, "row limit"):
            self.run_extract(Cursor(), 1)
