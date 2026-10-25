import unittest

from market_atlas.source_catalog import build_source_catalog


def inspection_fixture() -> dict:
    return {
        "server": {
            "database": "macro_medallion",
            "server_version": "16.15",
            "transaction_read_only": True,
        },
        "objects": [
            {
                "schema_name": "gold",
                "object_name": "fred_point_in_time",
                "object_type": "view",
                "estimated_rows": 0,
                "can_select": True,
                "can_write": False,
            },
            {
                "schema_name": "silver",
                "object_name": "fred_observation",
                "object_type": "table",
                "estimated_rows": 100,
                "can_select": False,
                "can_write": False,
            },
            {
                "schema_name": "atlas",
                "object_name": "node",
                "object_type": "table",
                "estimated_rows": 15,
                "can_select": False,
                "can_write": False,
            },
        ],
        "columns": [
            {
                "schema_name": "gold",
                "object_name": "fred_point_in_time",
                "ordinal_position": 1,
                "column_name": "series_id",
                "data_type": "text",
                "udt_name": "text",
                "is_nullable": False,
            }
        ],
        "indexes": [],
        "view_definitions": [
            {
                "schema_name": "gold",
                "object_name": "fred_point_in_time",
                "definition_md5": "a" * 32,
            }
        ],
    }


class SourceCatalogTests(unittest.TestCase):
    def test_catalog_marks_only_the_approved_live_view_as_supported(self):
        catalog = build_source_catalog(inspection_fixture())
        objects = {
            f"{item['schema_name']}.{item['object_name']}": item
            for item in catalog["objects"]
        }
        self.assertEqual(
            "supported_live", objects["gold.fred_point_in_time"]["support_state"]
        )
        self.assertEqual(
            "unavailable_to_source_role",
            objects["silver.fred_observation"]["support_state"],
        )
        self.assertEqual("marketatlas_owned", objects["atlas.node"]["support_state"])

    def test_catalog_fingerprint_is_deterministic(self):
        self.assertEqual(
            build_source_catalog(inspection_fixture())["catalog_fingerprint_sha256"],
            build_source_catalog(inspection_fixture())["catalog_fingerprint_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
