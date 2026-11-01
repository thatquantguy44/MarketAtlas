"""Independent Decimal arithmetic check against a retained macro research pack.

Does not import the production preparation or relationship implementation.
Run analytics validate-macro separately for file integrity and method contracts.
"""

import argparse
import json
import math
from datetime import date, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

TOLERANCE = 1e-10


def check(actual, expected):
    if actual is None or not math.isclose(
        float(actual), float(expected), rel_tol=0, abs_tol=TOLERANCE
    ):
        raise ValueError("independent numerical comparison failed")


def previous(period, frequency):
    if frequency == "m":
        return date(
            period.year - (period.month == 1),
            12 if period.month == 1 else period.month - 1,
            1,
        )
    result = period - timedelta(days=1)
    while result.weekday() in (5, 6):
        result -= timedelta(days=1)
    return result


def mean(values):
    return sum(values) / len(values)


def sample_sd(values):
    center = mean(values)
    return (sum((v - center) ** 2 for v in values) / (len(values) - 1)).sqrt()


def verify(directory):
    prepared = json.loads((directory / "prepared.json").read_text())
    results = json.loads((directory / "results.json").read_text())
    groups = {g["id"]: g for g in prepared["settings"]["groups"]}
    records = {r["source_record"]: r for r in prepared["capture"]["macro_observations"]}
    raw_index = {}
    for row in records.values():
        raw_index.setdefault(
            (row["series_canonical_key"], row["reference_period"]), []
        ).append(row)

    def level(sid, period, cutoff):
        versions = raw_index.get((f"macro:fred:{sid}", period.isoformat()), [])
        if any(
            not v["available_on"] or not v["source_valid_through_inclusive"]
            for v in versions
        ):
            return None
        eligible = [
            v
            for v in versions
            if v["available_on"] <= cutoff <= v["source_valid_through_inclusive"]
        ]
        if (
            len(eligible) != 1
            or eligible[0]["is_missing"]
            or eligible[0]["value"] is None
        ):
            return None
        value = Decimal(str(eligible[0]["value"]))
        return value if value.is_finite() else None

    def change(member, period, cutoff, frequency):
        old = level(member["series_id"], previous(period, frequency), cutoff)
        new = level(member["series_id"], period, cutoff)
        if old is None or new is None:
            return None
        if member["transform"] == "log_change":
            if min(old, new) <= 0:
                return None
            result = (new / old).ln() * 100
        else:
            result = new - old
        return result * member["orientation"]

    vectors, zscores = {}, {}
    counts = {
        "supported_transformed_points_checked": 0,
        "supported_correlations_checked": 0,
        "supported_zscores_checked": 0,
        "supported_group_dispersions_checked": 0,
    }
    for panel in prepared["panels"]:
        group = groups[panel["group_id"]]
        cutoff = panel["knowledge_date"]
        if panel["max_input_available_on"] and panel["max_input_available_on"] > cutoff:
            raise ValueError("input availability exceeds the result knowledge date")
        definitions = {m["series_id"]: m for m in group["members"]}
        for member in panel["members"]:
            definition = definitions[member["series_id"]]
            key = (panel["group_id"], cutoff, member["series_id"])
            vector = []
            for point in member["points"]:
                if point["status"] != "supported":
                    if point["value"] is not None:
                        raise ValueError("unavailable transformed point has a value")
                    vector.append(None)
                    continue
                period = date.fromisoformat(point["reference_period"])
                expected = change(definition, period, cutoff, group["frequency"])
                if expected is None or len(point["source_records"]) != 2:
                    raise ValueError(
                        "supported change lacks adjacent dated source inputs"
                    )
                for record in point["source_records"]:
                    raw = records[record]
                    if (
                        not raw["available_on"]
                        <= cutoff
                        <= raw["source_valid_through_inclusive"]
                    ):
                        raise ValueError("selected source input was unavailable")
                check(point["value"], expected)
                vector.append(expected)
                counts["supported_transformed_points_checked"] += 1
            vectors[key] = vector
            if member["zscore_status"] == "supported":
                period = date.fromisoformat(panel["reference_end"])
                values = []
                for _ in range(group["baseline"]):
                    period = previous(period, group["frequency"])
                    value = change(definition, period, cutoff, group["frequency"])
                    if value is not None:
                        values.append(value)
                if (
                    len(values) != member["baseline_count"]
                    or len(values) < group["minimum_baseline"]
                ):
                    raise ValueError("standardization baseline count differs")
                zscore = (vector[-1] - mean(values)) / sample_sd(values)
                check(member["zscore"], zscore)
                zscores[key] = zscore
                counts["supported_zscores_checked"] += 1
    for row in results["relationships"]:
        if row["estimate_status"] != "supported":
            if row["correlation"] is not None or row["distance"] is not None:
                raise ValueError("unavailable relationship has an estimate")
            continue
        key = (row["group_id"], row["knowledge_date"])
        aligned = [
            (a, b)
            for a, b in zip(
                vectors[(*key, row["series_low_id"])],
                vectors[(*key, row["series_high_id"])],
                strict=True,
            )
            if a is not None and b is not None
        ]
        if len(aligned) != row["paired_count"]:
            raise ValueError("paired sample count differs")
        left, right = [a for a, _ in aligned], [b for _, b in aligned]
        n = Decimal(len(aligned))
        numerator = n * sum(a * b for a, b in aligned) - sum(left) * sum(right)
        denominator = (
            (n * sum(a * a for a in left) - sum(left) ** 2)
            * (n * sum(b * b for b in right) - sum(right) ** 2)
        ).sqrt()
        correlation = max(Decimal(-1), min(Decimal(1), numerator / denominator))
        check(row["correlation"], correlation)
        check(row["distance"], (2 * (1 - correlation)).sqrt())
        counts["supported_correlations_checked"] += 1
    for row in results["group_dispersion"]:
        if row["estimate_status"] != "supported":
            if row["dispersion"] is not None:
                raise ValueError("unavailable group has a dispersion estimate")
            continue
        values = [
            zscores[(row["group_id"], row["knowledge_date"], m["series_id"])]
            for m in groups[row["group_id"]]["members"]
        ]
        check(row["group_mean_zscore"], mean(values))
        check(row["dispersion"], sample_sd(values))
        counts["supported_group_dispersions_checked"] += 1
    return {
        "status": "passed",
        "prepared_sha256": prepared["prepared_sha256"],
        "absolute_tolerance": TOLERANCE,
        "decimal_precision": 50,
        **counts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with localcontext() as context:
        context.prec = 50
        proof = verify(args.input)
    payload = json.dumps(proof, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload, end="")
