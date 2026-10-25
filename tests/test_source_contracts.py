import unittest

from market_atlas.source_contracts import (
    load_source_contract_registry,
    verify_source_contracts,
)


def valid_catalog() -> dict:
    """Build a catalog-shaped result that agrees exactly with the tracked registry."""
    registry = load_source_contract_registry()
    objects = []
    for contract in registry["contracts"]:
        objects.append(
            {
                "schema_name": contract["schema_name"],
                "object_name": contract["object_name"],
                "object_type": contract["object_type"],
                "can_select": True,
                "can_write": False,
                "read_probe_status": "passed",
                "columns": [
                    {"column_name": name}
                    for name in contract["required_columns"]
                ],
                "column_fingerprint_sha256": contract[
                    "expected_column_fingerprint_sha256"
                ],
                "view_definition_md5": contract.get(
                    "expected_view_definition_md5"
                ),
            }
        )
    return {
        "catalog_version": "source-catalog-v2",
        "catalog_fingerprint_sha256": "a" * 64,
        "objects": objects,
    }


class SourceContractTests(unittest.TestCase):
    def test_tracked_live_contracts_verify_against_a_matching_catalog(self):
        result = verify_source_contracts(valid_catalog())

        self.assertEqual("valid", result["status"])
        self.assertEqual(5, result["contract_count"])
        self.assertEqual(5, result["supported_live_count"])
        self.assertEqual([], result["errors"])

    def test_registry_declares_the_three_promoted_macro_context_interfaces(self):
        registry = load_source_contract_registry()
        contracts = {
            f"{contract['schema_name']}.{contract['object_name']}": contract
            for contract in registry["contracts"]
        }

        self.assertEqual("supported_live", contracts["gold.dim_series"]["lifecycle_state"])
        self.assertEqual(
            ["release_id", "release_date"],
            contracts["gold.release_calendar"]["business_key"],
        )
        self.assertEqual("view", contracts["gold.v_source_coverage"]["object_type"])

    def test_schema_fingerprint_drift_blocks_a_live_contract(self):
        catalog = valid_catalog()
        next(
            item
            for item in catalog["objects"]
            if item["object_name"] == "fred_point_in_time"
        )["column_fingerprint_sha256"] = "b" * 64

        result = verify_source_contracts(catalog)

        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "gold.fred_point_in_time: column fingerprint differs from contract",
            result["errors"],
        )

    def test_missing_registered_object_blocks_contract_promotion(self):
        catalog = valid_catalog()
        catalog["objects"] = [
            item
            for item in catalog["objects"]
            if item["object_name"] != "fred_series"
        ]

        result = verify_source_contracts(catalog)

        self.assertEqual("invalid", result["status"])
        self.assertIn("meta.fred_series: object is absent from catalog", result["errors"])


if __name__ == "__main__":
    unittest.main()
