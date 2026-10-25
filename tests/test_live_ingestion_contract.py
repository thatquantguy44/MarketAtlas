import copy
import unittest

from market_atlas.ingestion.macro_medallion import validate_extract


def source_extract() -> dict:
    return {
        "manifest": {
            "status": "source_contract_extracted; not_loaded_to_marketatlas_graph",
            "redistribution_status": "unresolved",
            "input_selection_sha256": "a" * 64,
            "source_rows_sha256": "b" * 64,
            "extracted_at": "2026-10-24T12:00:00+00:00",
        },
        "entities": [
            {
                "canonical_key": "macro:fred:TEST",
                "type": "macro_series",
                "label": "Test series",
                "frequency": "Monthly",
                "unit": "Index",
                "source_identifier": "TEST",
            }
        ],
        "macro_observations": [
            {
                "series_canonical_key": "macro:fred:TEST",
                "reference_period": "2024-01-01",
                "value": "101.0",
                "available_on": "2024-02-01",
                "availability_precision": "date",
                "source_valid_through_inclusive": "9999-12-31",
                "revision_number": 1,
                "is_missing": False,
                "source_ingested_at": "2024-02-01T01:00:00+00:00",
                "source_record": "gold.fred_point_in_time:TEST:2024-01-01:2024-02-01:1",
            }
        ],
    }


class LiveIngestionContractTests(unittest.TestCase):
    def test_accepts_a_valid_bounded_source_extract(self):
        validate_extract(source_extract())

    def test_rejects_observation_outside_the_declared_series(self):
        extract = source_extract()
        extract["macro_observations"][0]["series_canonical_key"] = "macro:fred:OTHER"
        with self.assertRaisesRegex(ValueError, "unknown macro series"):
            validate_extract(extract)

    def test_rejects_a_missing_value_that_claims_to_be_present(self):
        extract = copy.deepcopy(source_extract())
        extract["macro_observations"][0]["value"] = None
        with self.assertRaisesRegex(ValueError, "requires a value"):
            validate_extract(extract)


if __name__ == "__main__":
    unittest.main()
