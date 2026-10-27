import copy
import math
import unittest

from market_atlas.adapters.macro_context import build_revision_summary_extract
from market_atlas.contracts import sha256
from market_atlas.publishing.revision_quality import (
    quality_records,
    validate_revision_extract,
)


def synthetic_extract():
    extract = build_revision_summary_extract(
        ["SYNTH_A", "SYNTH_MISSING"],
        [
            {
                "series_id": "SYNTH_A",
                "observation_count": 12,
                "avg_revision_count": 1.25,
                "max_revision_count": 3,
                "avg_abs_revision_pct": 0.4,
                "max_abs_revision_pct": 1.1,
            }
        ],
    )
    extract["manifest"]["source_contract_verification"] = {
        "status": "valid",
        "registry_version": "synthetic-contract-v1",
        "catalog_fingerprint_sha256": "a" * 64,
    }
    return extract


def rehash_rows(extract):
    extract["manifest"]["source_rows_sha256"] = sha256(
        {key: extract[key] for key in ("revision_summaries", "missing_series_ids")}
    )


class RevisionQualityPublicationTests(unittest.TestCase):
    def test_missing_summary_is_unknown_with_null_metrics(self):
        extract = synthetic_extract()
        validate_revision_extract(extract)
        records = quality_records(extract)
        self.assertEqual(2, len(records))
        self.assertEqual("available", records[0]["quality_status"])
        self.assertEqual("unknown", records[1]["quality_status"])
        self.assertIsNone(records[1]["observation_count"])
        self.assertIsNone(records[1]["avg_revision_count"])

    def test_rejects_tampering_even_with_valid_rows(self):
        extract = synthetic_extract()
        extract["revision_summaries"][0]["observation_count"] = 13
        with self.assertRaisesRegex(ValueError, "source rows hash"):
            validate_revision_extract(extract)

    def test_rejects_false_missing_accounting(self):
        extract = synthetic_extract()
        extract["missing_series_ids"] = []
        rehash_rows(extract)
        with self.assertRaisesRegex(ValueError, "missing series"):
            validate_revision_extract(extract)

    def test_rejects_unverified_history_or_rights_claims(self):
        for field, value in (
            ("temporal_status", "point_in_time"),
            ("redistribution_status", "approved"),
            ("source_contract_verification", {"status": "invalid"}),
        ):
            with self.subTest(field=field):
                extract = synthetic_extract()
                extract["manifest"][field] = value
                with self.assertRaises(ValueError):
                    validate_revision_extract(extract)

    def test_rejects_invalid_metrics_before_any_database_access(self):
        for field, value in (
            ("observation_count", True),
            ("max_revision_count", True),
            ("avg_revision_count", float("nan")),
            ("max_abs_revision_pct", -1),
            ("avg_revision_count", 4),
        ):
            with self.subTest(field=field, value=value):
                extract = synthetic_extract()
                extract["revision_summaries"][0][field] = value
                if not isinstance(value, float) or math.isfinite(value):
                    rehash_rows(extract)
                with self.assertRaises(ValueError):
                    validate_revision_extract(extract)

    def test_rejects_selection_tampering_and_duplicate_rows(self):
        extract = synthetic_extract()
        extract["manifest"]["series_ids"].append("ANOTHER")
        with self.assertRaisesRegex(ValueError, "selection hash"):
            validate_revision_extract(extract)
        extract = synthetic_extract()
        extract["revision_summaries"].append(
            copy.deepcopy(extract["revision_summaries"][0])
        )
        rehash_rows(extract)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_revision_extract(extract)


if __name__ == "__main__":
    unittest.main()
