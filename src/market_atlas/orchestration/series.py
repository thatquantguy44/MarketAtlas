"""Discover bounded FRED selections within the approved taxonomy and date window."""

from market_atlas.adapters.macro_medallion import _read_only_connection


def select_eligible_series(
    database, observation, *, max_series=1000, max_observations=250000, batch_size=25
):
    with _read_only_connection(database) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.series_id,d.source,m.active,m.title,m.frequency,m.units,m.vintage_enabled
            FROM gold.dim_series d LEFT JOIN meta.fred_series m USING (series_id)
            ORDER BY d.series_id
            LIMIT %s
        """,
            (max_series + 1,),
        )
        metadata = [
            dict(zip([column.name for column in cursor.description], row, strict=True))
            for row in cursor.fetchmany(max_series + 1)
        ]
        if len(metadata) > max_series:
            raise ValueError(
                "approved series catalog exceeds configured discovery limit"
            )
        selected, excluded, candidates = [], [], []
        metadata_by_id = {row["series_id"]: row for row in metadata}
        for row in metadata:
            reason = (
                "unsupported_source_for_fred_adapter"
                if row["source"] != "fred"
                else "inactive_or_missing_source_metadata"
                if not row["active"]
                else "incomplete_source_metadata"
                if any(
                    not isinstance(row[key], str) or not row[key].strip()
                    for key in ("title", "frequency", "units")
                )
                else None
            )
            if reason:
                excluded.append({"series_id": row["series_id"], "reason": reason})
            else:
                candidates.append(row["series_id"])
        total_versions = 0
        counts = {}
        for start in range(0, len(candidates), batch_size):
            cursor.execute(
                """
                SELECT series_id,count(*) AS versions,
                       count(*) FILTER (WHERE is_missing = 0 AND value IS NOT NULL
                         AND value::text NOT IN ('NaN','Infinity','-Infinity')) AS usable,
                       count(*) FILTER (WHERE realtime_start IS NULL OR realtime_end IS NULL OR realtime_start !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR realtime_end !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR realtime_start > realtime_end OR is_missing IS NULL OR is_missing NOT IN (0,1)
                         OR (is_missing = 0 AND (value IS NULL OR value::text IN ('NaN','Infinity','-Infinity')))
                         OR (is_missing <> 0 AND value IS NOT NULL)) AS invalid,
                       count(*) FILTER (WHERE coalesce(realtime_start,'')='' AND coalesce(realtime_end,'')='') AS undated
                FROM gold.fred_point_in_time
                WHERE series_id = ANY(%s) AND observation_date >= %s
                  AND observation_date <= %s AND (realtime_start <= %s OR realtime_start IS NULL)
                GROUP BY series_id
            """,
                (
                    candidates[start : start + batch_size],
                    observation.observation_start,
                    min(observation.observation_end, observation.knowledge_cutoff),
                    observation.knowledge_cutoff,
                ),
            )
            counts.update(
                {
                    row[0]: {
                        "versions": row[1],
                        "usable": row[2],
                        "invalid": row[3],
                        "undated": row[4],
                    }
                    for row in cursor.fetchall()
                }
            )
        for series_id in candidates:
            count = counts.get(
                series_id, {"versions": 0, "usable": 0, "invalid": 0, "undated": 0}
            )
            reason = (
                "current_only_by_source_policy"
                if count["versions"]
                and count["undated"] == count["versions"]
                and metadata_by_id[series_id]["vintage_enabled"] == 0
                else "invalid_observation_state_or_vintage_dates"
                if count["invalid"]
                else "no_usable_observations_in_window"
                if not count["usable"]
                else None
            )
            if reason:
                excluded.append({"series_id": series_id, "reason": reason})
            else:
                selected.append(series_id)
                total_versions += count["versions"]
        if not selected:
            raise ValueError("no eligible FRED series in the configured window")
        if total_versions > max_observations:
            raise ValueError("eligible observations exceed configured row limit")
    return {
        "mode": "all_eligible",
        "catalog_series_count": len(metadata),
        "selected_series_ids": selected,
        "context_series_ids": candidates,
        "context_series_count": len(candidates),
        "selected_series_count": len(selected),
        "expected_observation_versions": total_versions,
        "excluded": excluded,
        "observation_start": observation.observation_start,
        "observation_end": observation.observation_end,
        "knowledge_cutoff": observation.knowledge_cutoff,
        "scope": "approved gold.dim_series entries with FRED source metadata and valid dated point-in-time observations; current context/quality selection is independent",
    }
