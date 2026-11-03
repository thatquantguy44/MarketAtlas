import unittest
from dataclasses import asdict, replace
from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime
from decimal import localcontext

from market_atlas.securities_finance.contracts import (
    ContractError,
    QuantityConvention,
    QuantityValue,
    RecordEnvelope,
    RecordKey,
    TimestampEvidence,
    validate_unique_envelopes,
)


class QuantityContractTests(unittest.TestCase):
    def setUp(self):
        self.bond = QuantityConvention(
            "bond-v1", "bond-id", "nominal", "USD", 0, "1500", "1000"
        )

    def test_exact_normalization_does_not_depend_on_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            value = QuantityValue("123456789.1200", "nominal", "USD", 2)
        self.assertEqual(value.units, 12345678912)
        self.assertEqual(value.amount, "123456789.12")
        self.assertEqual(value, QuantityValue("123456789.12", "nominal", "USD", 2))

    def test_unknown_and_zero_remain_distinct(self):
        unknown = QuantityValue(None, "nominal", "USD", 0)
        zero = QuantityValue("0", "nominal", "USD", 0)
        self.assertIsNone(self.bond.validate_quantity(unknown))
        self.assertEqual(0, self.bond.validate_quantity(zero, for_allocation=True))
        with self.assertRaisesRegex(ContractError, "unknown_quantity"):
            self.bond.validate_quantity(unknown, for_allocation=True)

    def test_whole_shares_and_invalid_numeric_representations(self):
        self.assertEqual(QuantityValue("5.00", "share", None, 0).units, 5)
        for amount in [
            "1.5",
            "-1",
            "NaN",
            "Infinity",
            "1e3",
            " 1",
            "01",
            "",
            1,
            1.0,
            True,
        ]:
            with self.subTest(amount=amount), self.assertRaises(ContractError):
                QuantityValue(amount, "share", None, 0)

    def test_invalid_metadata_and_conventions(self):
        for unit, currency, precision in [
            ("share", "USD", 0),
            ("share", None, 1),
            ("nominal", None, 0),
            ("nominal", "usd", 0),
            ("nominal", "USD", True),
            ("nominal", "USD", 1000000),
        ]:
            with self.subTest(unit=unit, currency=currency, precision=precision):
                with self.assertRaises(ContractError):
                    QuantityValue("1", unit, currency, precision)
        for changes in [
            {"minimum_allocation": "0"},
            {"allocation_increment": "0"},
            {"increment_origin": "zero"},
            {"minimum_scope": "request"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.bond, **changes)

    def test_bond_balance_remainder_is_valid_but_new_proposal_must_fit(self):
        for amount in ["0", "1500", "2500", "3500"]:
            self.assertEqual(
                int(amount),
                self.bond.validate_quantity(
                    QuantityValue(amount, "nominal", "USD", 0), for_allocation=True
                ),
            )
        for amount in ["500", "1000", "2000"]:
            value = QuantityValue(amount, "nominal", "USD", 0)
            self.assertEqual(int(amount), self.bond.validate_quantity(value))
            with self.assertRaisesRegex(ContractError, "invalid_allocation_quantity"):
                self.bond.validate_quantity(value, for_allocation=True)

    def test_units_currency_and_precision_are_not_substituted(self):
        for value in [
            QuantityValue("1500", "share", None, 0),
            QuantityValue("1500", "nominal", "EUR", 0),
            QuantityValue("1500", "nominal", "USD", 2),
        ]:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ContractError, "quantity_convention_mismatch"),
            ):
                self.bond.validate_quantity(value)

    def test_normalized_mappings_reject_missing_unknown_and_computed_fields(self):
        valid = {
            "amount": "1",
            "quantity_unit": "share",
            "quantity_currency": None,
            "quantity_precision": 0,
        }
        self.assertEqual(
            QuantityValue("1", "share", None, 0), QuantityValue.from_mapping(valid)
        )
        for fields in [
            {**valid, "units": 100},
            {**valid, "typo": "value"},
            {key: value for key, value in valid.items() if key != "amount"},
        ]:
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                QuantityValue.from_mapping(fields)

    def test_numeric_bounds_and_fractional_nominal_precision_are_explicit(self):
        value = QuantityValue("1.25", "nominal", "USD", 2)
        convention = QuantityConvention(
            "fractional-v1", "bond-id", "nominal", "USD", 2, "1.25", "0.50"
        )
        self.assertEqual(125, convention.validate_quantity(value, for_allocation=True))
        self.assertEqual(
            175,
            convention.validate_quantity(
                replace(value, amount="1.75"), for_allocation=True
            ),
        )
        with self.assertRaisesRegex(ContractError, "quantity_precision_mismatch"):
            QuantityValue("1.251", "nominal", "USD", 2)
        with self.assertRaisesRegex(ContractError, "invalid_quantity"):
            QuantityValue("1" * 129, "nominal", "USD", 0)
        with self.assertRaisesRegex(ContractError, "invalid_validation_mode"):
            convention.validate_quantity(value, for_allocation="false")


class EnvelopeContractTests(unittest.TestCase):
    def setUp(self):
        self.envelope = RecordEnvelope(
            key=RecordKey("fixture", "inventory_position", "p1", "v1"),
            effective_from=TimestampEvidence("2026-11-01", "date", "UTC"),
            effective_to=None,
            source_available_at=TimestampEvidence("2026-11-02T12:00:00Z", "instant"),
            source_confirmed_at=None,
            recorded_from=TimestampEvidence("2026-11-03T12:00:00Z", "instant"),
            recorded_to=None,
            source_record_reference="fixture:position:p1:v1",
        )

    def test_three_clocks_and_missing_evidence_are_retained_separately(self):
        self.assertEqual("2026-11-01", self.envelope.effective_from.value)
        self.assertEqual(
            "2026-11-02T12:00:00Z", self.envelope.source_available_at.value
        )
        self.assertEqual("2026-11-03T12:00:00Z", self.envelope.recorded_from.value)
        self.assertIsNone(self.envelope.source_confirmed_at)

    def test_offsets_normalize_without_promoting_dates_to_instants(self):
        timed = TimestampEvidence("2026-11-03T07:00:00-05:00", "instant")
        self.assertEqual(datetime(2026, 11, 3, 12, tzinfo=UTC), timed.as_utc())
        self.assertEqual("2026-11-03T12:00:00Z", timed.normalized_value)
        self.assertEqual("2026-11-03T07:00:00-05:00", timed.value)
        day = TimestampEvidence("2026-11-03", "date")
        self.assertIsNone(day.as_utc())
        self.assertIsNone(day.source_timezone)
        self.assertEqual("2026-11-03", day.normalized_value)

    def test_malformed_times_naive_times_and_truncated_precision_are_rejected(self):
        for value, precision, zone in [
            ("2026-11-03T12:00:00", "instant", None),
            ("2026-11-03T12:00:00.1234567Z", "instant", None),
            ("2026-11-03T12:00:00+00:99", "instant", None),
            ("0001-01-01T00:00:00+01:00", "instant", None),
            ("2026-02-30", "date", None),
            ("20261103", "date", None),
            ("2026-11-03", "date", "Not/AZone"),
            ("2026-11-03", "week", None),
        ]:
            with (
                self.subTest(value=value, precision=precision),
                self.assertRaises(ContractError),
            ):
                TimestampEvidence(value, precision, zone)

    def test_versions_and_source_names_are_distinct_but_duplicate_keys_fail(self):
        updated = replace(
            self.envelope, key=replace(self.envelope.key, version_id="v2")
        )
        other = replace(
            self.envelope, key=replace(self.envelope.key, source_name="other")
        )
        self.assertEqual(
            3, len(validate_unique_envelopes([self.envelope, updated, other]))
        )
        with self.assertRaisesRegex(ContractError, "duplicate_record_key"):
            validate_unique_envelopes([self.envelope, self.envelope])
        with self.assertRaisesRegex(ContractError, "duplicate_record_key"):
            validate_unique_envelopes(
                [
                    self.envelope,
                    replace(self.envelope, source_confirmed_at=updated.recorded_from),
                ]
            )

    def test_unknown_versions_keys_and_extra_fields_cannot_pass_validation(self):
        for version in [0, 2, True, "1"]:
            with self.subTest(version=version), self.assertRaises(ContractError):
                replace(self.envelope, schema_version=version)
        for key in [RecordKey, None, "not-a-key"]:
            with self.subTest(key=key), self.assertRaises(ContractError):
                replace(self.envelope, key=key)
        for source, kind, identifier in [
            ("", "loan", "p1"),
            ("fixture", "typo", "p1"),
            ("fixture", "loan", " p1"),
        ]:
            with (
                self.subTest(source=source, kind=kind),
                self.assertRaises(ContractError),
            ):
                RecordKey(source, kind, identifier, "v1")
        with self.assertRaisesRegex(ContractError, "unexpected_fields"):
            RecordEnvelope.from_mapping({**asdict(self.envelope), "eligible": True})

    def test_normalized_mapping_preserves_typed_missing_values_and_rejects_missing_fields(
        self,
    ):
        values = {
            item.name: getattr(self.envelope, item.name)
            for item in dataclass_fields(self.envelope)
        }
        self.assertEqual(self.envelope, RecordEnvelope.from_mapping(values))
        del values["source_available_at"]
        with self.assertRaisesRegex(ContractError, "missing_fields"):
            RecordEnvelope.from_mapping(values)
        with self.assertRaisesRegex(ContractError, "invalid_envelope"):
            validate_unique_envelopes([None])

    def test_record_times_intervals_and_event_envelopes_are_explicit(self):
        for changes in [
            {"recorded_from": None},
            {"recorded_from": TimestampEvidence("2026-11-03", "date")},
            {"recorded_to": self.envelope.recorded_from},
            {"effective_at": self.envelope.source_available_at},
            {
                "effective_from": self.envelope.recorded_from,
                "effective_to": self.envelope.source_available_at,
            },
        ]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.envelope, **changes)
        event = replace(
            self.envelope,
            key=replace(self.envelope.key, record_type="lifecycle_event"),
            effective_from=None,
            effective_at=self.envelope.source_available_at,
        )
        self.assertIsNone(event.effective_from)
        with self.assertRaisesRegex(ContractError, "invalid_event_envelope"):
            replace(event, effective_from=self.envelope.effective_from)


if __name__ == "__main__":
    unittest.main()
