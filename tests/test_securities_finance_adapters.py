import json
import unittest
from unittest.mock import patch

from market_atlas.securities_finance.adapters import decode_table, encode_table
from market_atlas.securities_finance.catalog import build_reference_catalog
from market_atlas.securities_finance.contracts import ContractError


class CodecTests(unittest.TestCase):
    def setUp(self):
        reference = build_reference_catalog().instruments[0]
        self.row = {
            name: getattr(reference, name)
            for name in (
                "instrument_node_id",
                "canonical_key",
                "node_type",
                "asset_class",
                "label",
                "provenance_reference",
            )
        }
        self.row["label"] = 'Synthetic, "quoted"\nlabel'

    def test_json_csv_preserve_quotes_newlines_and_unicode(self):
        self.row["label"] += " — α"
        for format in ("json", "csv"):
            with self.subTest(format=format):
                data = encode_table("instrument_catalog", [self.row], format)
                self.assertEqual(
                    (self.row,), decode_table("instrument_catalog", data, format)
                )

    def test_empty_tables_keep_explicit_csv_header(self):
        for format in ("json", "csv"):
            self.assertEqual(
                (),
                decode_table(
                    "instrument_catalog",
                    encode_table("instrument_catalog", [], format),
                    format,
                ),
            )

    def test_duplicate_json_keys_and_nonfinite_or_decimal_literals_fail(self):
        data = (
            json.dumps([self.row])
            .replace(
                '"asset_class": "equity"',
                '"asset_class": "equity", "asset_class": "equity"',
            )
            .encode()
        )
        with self.assertRaisesRegex(ContractError, "duplicate_json_key"):
            decode_table("instrument_catalog", data, "json")
        for literal in (b"NaN", b"Infinity", b"1.0", b"1e309"):
            with self.subTest(literal=literal), self.assertRaises(ContractError):
                decode_table(
                    "instrument_catalog", b'[{"label":' + literal + b"}]", "json"
                )

    def test_missing_extra_duplicate_headers_ragged_and_malformed_csv_fail(self):
        valid = encode_table("instrument_catalog", [self.row], "csv")
        for data in (
            b"label,label\nx,y\n",
            b"label\nx\n",
            valid.split(b"\n", 1)[0] + b"\nx\n",
            b'"unterminated',
        ):
            with self.subTest(data=data), self.assertRaises(ContractError):
                decode_table("instrument_catalog", data, "csv")
        for changes in ({"extra": "x"}, {"label": "\\N"}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                encode_table("instrument_catalog", [{**self.row, **changes}], "json")

    def test_invalid_encoding_format_and_unknown_table_fail(self):
        for args in (
            ("instrument_catalog", b"\xff", "json"),
            ("instrument_catalog", b"\xff", "csv"),
            ("instrument_catalog", b"[]", "yaml"),
            ("typo", b"[]", "json"),
        ):
            with self.subTest(args=args), self.assertRaises(ContractError):
                decode_table(*args)

    def test_declared_scalar_types_and_resource_limits_are_enforced(self):
        for field, value in (("label", 10), ("node_type", True)):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ContractError, "invalid_field_type"),
            ):
                decode_table(
                    "instrument_catalog",
                    json.dumps([{**self.row, field: value}]).encode(),
                    "json",
                )
        with patch("market_atlas.securities_finance.adapters.MAX_TABLE_ROWS", 1):
            with self.assertRaisesRegex(ContractError, "too_many_rows"):
                encode_table("instrument_catalog", [self.row, self.row], "csv")
        with patch("market_atlas.securities_finance.adapters.MAX_FILE_BYTES", 4):
            with self.assertRaisesRegex(ContractError, "file_too_large"):
                decode_table("instrument_catalog", b"[     ]", "json")


if __name__ == "__main__":
    unittest.main()
