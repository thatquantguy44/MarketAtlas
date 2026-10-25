import copy
import unittest

from market_atlas.contracts import sha256
from market_atlas.publishing.macro_context import validate_context_extract


def valid_extract():
    rows = {
        "series_taxonomy": [{"series_id": "CPIAUCSL", "title": "CPI"}],
        "release_events": [
            {
            "release_id": 10,
                "release_date": "2026-10-14",
                "is_future": 1,
                "fetched_at": "2026-10-01T00:00:00Z",
            }
        ],
        "source_coverage": [
            {
                "source": "fred",
                "series_id": "CPIAUCSL",
                "latest_observation_date": "2026-09-01",
                "is_stale": 0,
            }
        ],
    }
    extract = {
        "manifest": {
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
            "redistribution_status": "unresolved",
            "source": "macro_medallion_postgresql",
            "objects": [
                "gold.dim_series",
                "gold.release_calendar",
                "gold.v_source_coverage",
            ],
            "series_ids": ["CPIAUCSL"],
            "release_start": "2026-10-01",
            "release_end": "2026-10-31",
            "input_selection_sha256": "a" * 64,
            "source_rows_sha256": "b" * 64,
            "extracted_at": "2026-10-01T00:00:00Z",
            "series_taxonomy_temporal_status": "current_only",
            "release_event_temporal_status": "scheduled_date_with_source_fetched_at",
            "coverage_temporal_status": "current_only",
            "source_contract_verification": {
                "status": "valid",
                "registry_version": "source-contracts-v1",
                "catalog_fingerprint_sha256": "c" * 64,
            },
        },
        **rows,
    }
    extract["manifest"]["input_selection_sha256"] = sha256(
        {
            key: extract["manifest"][key]
            for key in ("source", "objects", "series_ids", "release_start", "release_end")
        }
    )
    extract["manifest"]["source_rows_sha256"] = sha256(rows)
    return extract


class MacroContextPublicationTests(unittest.TestCase):
    def test_validated_extract_preserves_current_and_scheduled_semantics(self):
        extract = valid_extract()
        validate_context_extract(extract)

    def test_rejects_any_claim_of_point_in_time_taxonomy_history(self):
        extract = valid_extract()
        extract["manifest"]["series_taxonomy_temporal_status"] = "point_in_time"
        with self.assertRaisesRegex(ValueError, "current_only"):
            validate_context_extract(extract)

    def test_rejects_an_extract_without_contract_gate(self):
        extract = valid_extract()
        extract["manifest"]["source_contract_verification"]["status"] = "invalid"
        with self.assertRaisesRegex(ValueError, "source-contract verification"):
            validate_context_extract(extract)

    def test_rejects_duplicate_release_grain(self):
        extract = valid_extract()
        extract["release_events"].append(copy.deepcopy(extract["release_events"][0]))
        extract["manifest"]["source_rows_sha256"] = sha256(
            {
                key: extract[key]
                for key in ("series_taxonomy", "release_events", "source_coverage")
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate release"):
            validate_context_extract(extract)


if __name__ == "__main__":
    unittest.main()
