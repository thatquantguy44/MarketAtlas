"""Descriptive macro relationships; separate from sourced taxonomy assertions."""

from __future__ import annotations

import math
import statistics
from itertools import combinations

from market_atlas.analytics.macro_series import verify_prepared
from market_atlas.contracts import sha256

METHOD_VERSION = "macro-relationships-pearson-distance-dispersion-v1"


def _correlation(left, right):
    left_mean, right_mean = statistics.mean(left), statistics.mean(right)
    a = [v - left_mean for v in left]
    b = [v - right_mean for v in right]
    a_norm, b_norm = math.hypot(*a), math.hypot(*b)
    if a_norm == 0 or b_norm == 0:
        return None
    if not math.isfinite(a_norm) or not math.isfinite(b_norm):
        # Correlation is invariant to positive rescaling. Avoid interpreting
        # overflowed norms as zero correlation on otherwise finite inputs.
        left_scale, right_scale = max(map(abs, left)), max(map(abs, right))
        return _correlation(
            [x / left_scale for x in left], [x / right_scale for x in right]
        )
    return max(
        -1.0,
        min(
            1.0,
            math.fsum((x / a_norm) * (y / b_norm) for x, y in zip(a, b, strict=True)),
        ),
    )


def panel_estimates(panel, group):
    """Calculate one fixed, aligned panel; undefined fields are always null."""
    base = {
        key: panel[key]
        for key in (
            "group_id",
            "knowledge_date",
            "reference_start",
            "reference_end",
            "input_sha256",
            "max_input_available_on",
        )
    }
    members = sorted(panel["members"], key=lambda m: m["series_id"])
    if [m["series_id"] for m in members] != sorted(
        m["series_id"] for m in group["members"]
    ):
        raise ValueError("panel membership differs from the configured group")
    grid = [p["reference_period"] for p in members[0]["points"]]
    if (
        len(grid) != group["window"]
        or grid != sorted(set(grid))
        or any([p["reference_period"] for p in m["points"]] != grid for m in members)
    ):
        raise ValueError("panel points must share the configured fixed grid")
    pairs = []
    for left, right in combinations(members, 2):
        aligned = [
            (a["value"], b["value"])
            for a, b in zip(left["points"], right["points"], strict=True)
            if a["status"] == b["status"] == "supported"
        ]
        correlation = None
        status = "insufficient_sample"
        if len(aligned) >= group["minimum_pairs"]:
            correlation = _correlation([a for a, _ in aligned], [b for _, b in aligned])
            status = "supported" if correlation is not None else "zero_variance"
        pairs.append(
            {
                **base,
                "series_low_id": left["series_id"],
                "series_high_id": right["series_id"],
                "window_count": group["window"],
                "minimum_pairs": group["minimum_pairs"],
                "paired_count": len(aligned),
                "coverage_ratio": len(aligned) / group["window"],
                "estimate_status": status,
                "correlation": correlation,
                "distance": math.sqrt(2 * (1 - correlation))
                if correlation is not None
                else None,
                "pair_input_sha256": sha256(
                    {"left": left["points"], "right": right["points"]}
                ),
            }
        )
    usable = [m for m in members if m["zscore_status"] == "supported"]
    complete = len(usable) == len(members)
    mean = statistics.mean(m["zscore"] for m in usable) if complete else None
    dispersion = statistics.stdev(m["zscore"] for m in usable) if complete else None
    group_row = {
        **base,
        "member_count": len(members),
        "usable_member_count": len(usable),
        "estimate_status": "supported" if complete else "incomplete_group",
        "group_mean_zscore": mean,
        "dispersion": dispersion,
        "baseline_window": group["baseline"],
        "minimum_baseline": group["minimum_baseline"],
    }
    nodes = []
    for member in members:
        peers = [
            p
            for p in pairs
            if member["series_id"] in (p["series_low_id"], p["series_high_id"])
        ]
        peer_supported = all(p["estimate_status"] == "supported" for p in peers)
        nodes.append(
            {
                **base,
                "series_id": member["series_id"],
                "zscore": member["zscore"],
                "zscore_status": member["zscore_status"],
                "baseline_count": member["baseline_count"],
                "baseline_input_sha256": member["baseline_input_sha256"],
                "current_change": member["points"][-1]["value"],
                "current_change_status": member["points"][-1]["status"],
                "deviation_from_group_mean": member["zscore"] - mean
                if complete
                else None,
                "absolute_deviation_from_group_mean": abs(member["zscore"] - mean)
                if complete
                else None,
                "group_comparison_status": group_row["estimate_status"],
                "peer_count": len(peers),
                "usable_peer_count": sum(
                    p["estimate_status"] == "supported" for p in peers
                ),
                "peer_distance_status": "supported"
                if peer_supported
                else "incomplete_peer_estimates",
                "mean_peer_distance": statistics.mean(p["distance"] for p in peers)
                if peer_supported
                else None,
            }
        )
    return pairs, group_row, nodes


def _add_changes(current, previous, key, prefix, comparison_date):
    status = (
        "current_estimate_unavailable"
        if current[key] is None
        else "insufficient_prior_evaluations"
        if previous is None
        else "prior_estimate_unavailable"
        if previous[key] is None
        else "supported"
    )
    current.update(
        {
            "comparison_knowledge_date": comparison_date,
            f"{prefix}_change_status": status,
            f"{prefix}_change": current[key] - previous[key]
            if status == "supported"
            else None,
        }
    )


def calculate_relationships(prepared):
    verify_prepared(prepared)
    groups = {group["id"]: group for group in prepared["settings"]["groups"]}
    relationships, dispersions, nodes = [], [], []
    histories = {group_id: [] for group_id in groups}
    for panel in prepared["panels"]:
        group = groups[panel["group_id"]]
        pairs, group_row, node_rows = panel_estimates(panel, group)
        history = histories[group["id"]]
        lag = group["change_lag_evaluations"]
        prior = history[-lag] if len(history) >= lag else None
        comparison_date = prior[1]["knowledge_date"] if prior else None
        for i, row in enumerate(pairs):
            _add_changes(
                row,
                prior[0][i] if prior else None,
                "distance",
                "distance",
                comparison_date,
            )
        _add_changes(
            group_row,
            prior[1] if prior else None,
            "dispersion",
            "dispersion",
            comparison_date,
        )
        for i, row in enumerate(node_rows):
            _add_changes(
                row,
                prior[2][i] if prior else None,
                "mean_peer_distance",
                "mean_peer_distance",
                comparison_date,
            )
        history.append((pairs, group_row, node_rows))
        relationships.extend(pairs)
        dispersions.append(group_row)
        nodes.extend(node_rows)
    return {
        "method_version": METHOD_VERSION,
        "prepared_sha256": prepared["prepared_sha256"],
        "settings_sha256": prepared["settings_sha256"],
        "source_rows_sha256": prepared["capture"]["manifest"]["source_rows_sha256"],
        "interpretation": "descriptive_research_not_validated_predictive_or_causal",
        "distance_geometry": "pairwise_missingness_may_prevent_a_common_metric_embedding",
        "relationships": relationships,
        "group_dispersion": dispersions,
        "node_divergence": nodes,
    }
