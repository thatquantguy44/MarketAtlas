"""Admission rules keep unsupported sources and invalid observations out of FRED ingestion."""

import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from market_atlas.config import MacroMedallionConfig
from market_atlas.orchestration.series import select_eligible_series


class Cursor:
    def __init__(self):
        self.metadata = [
            ("A", "fred", 1, "A title", "m", "Percent", 1),
            ("B", "fred", 1, "B title", "q", "Index", 1),
            ("C", "fred", 1, "C title", "m", "Percent", 1),
            ("D", "ecb", 1, "D title", "d", "Percent", 1),
            ("E", "fred", 0, "E title", "m", "Percent", 1),
            ("F", "fred", 1, "F title", "m", "", 1),
            ("G", "fred", 1, "G title", "m", "Percent", 1),
            ("H", "fred", 1, "H title", "m", "Percent", 0),
        ]
        self.counts = {
            "A": (2, 2, 0, 0),
            "B": (3, 2, 0, 0),
            "G": (1, 0, 1, 0),
            "H": (2, 2, 2, 2),
        }
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, params=None):
        self.calls.append(params)
        self.description = [
            SimpleNamespace(name=name)
            for name in [
                "series_id",
                "source",
                "active",
                "title",
                "frequency",
                "units",
                "vintage_enabled",
            ]
        ]
        self.selected = params[0] if params else None

    def fetchmany(self, size):
        return self.metadata[:size]

    def fetchall(self):
        return [(key, *self.counts[key]) for key in self.selected if key in self.counts]


class SeriesSelectionTests(unittest.TestCase):
    def select(self, cursor, **kwargs):
        @contextlib.contextmanager
        def connect(_):
            yield SimpleNamespace(cursor=lambda: cursor)

        pilot = MacroMedallionConfig(
            ("A",), "2024-01-01", "2026-10-30", "2026-10-30", "restricted"
        )
        with patch("market_atlas.orchestration.series._read_only_connection", connect):
            return select_eligible_series(None, pilot, **kwargs)

    def test_admission_exclusions_and_parameterized_batches(self):
        cursor = Cursor()
        result = self.select(cursor, batch_size=2)
        self.assertEqual(result["selected_series_ids"], ["A", "B"])
        self.assertEqual(result["expected_observation_versions"], 5)
        excluded = {row["series_id"]: row["reason"] for row in result["excluded"]}
        self.assertEqual(excluded["C"], "no_usable_observations_in_window")
        self.assertEqual(excluded["D"], "unsupported_source_for_fred_adapter")
        self.assertEqual(excluded["G"], "invalid_observation_state_or_vintage_dates")
        self.assertEqual(excluded["H"], "current_only_by_source_policy")
        self.assertIn("H", result["context_series_ids"])
        for params in cursor.calls[1:]:
            self.assertLessEqual(len(params[0]), 2)
            self.assertEqual(params[1:], ("2024-01-01", "2026-10-30", "2026-10-30"))

    def test_discovery_and_observation_limits_fail_before_publication(self):
        for limits in ({"max_series": 2}, {"max_observations": 4}):
            with (
                self.subTest(limits=limits),
                self.assertRaisesRegex(ValueError, "limit"),
            ):
                self.select(Cursor(), **limits)
