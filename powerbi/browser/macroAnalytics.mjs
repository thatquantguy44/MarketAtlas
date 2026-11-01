// Pure view selections. Values come from validated reviewed rows, never refitted.
export const PREFIX = "macro_analytics_";
export const queryId = name => PREFIX + name;
export const isSupported = row => row?.estimate_status === "supported";
export const dateLabel = day => day ? new Intl.DateTimeFormat("en-US", {
  year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
}).format(new Date(`${day}T12:00:00Z`)) : "Unavailable";
export const numberLabel = value => value == null ? "Unavailable" : Number(value).toFixed(3);
export const statusLabel = value => (value || "unavailable").replaceAll("_", " ");

export function atDate(rows, group, date) {
  return rows.filter(row => row.group_id === group && row.knowledge_date === date);
}

export function historyThrough(rows, group, date) {
  return rows.filter(row => row.group_id === group && row.knowledge_date <= date)
    .sort((a, b) => a.knowledge_date.localeCompare(b.knowledge_date));
}

export function symmetricPairs(rows) {
  // The diagonal stays absent. Undefined pairs keep their null values.
  return rows.flatMap(row => {
    const values = Object.fromEntries(["correlation", "paired_count", "window_count", "distance",
      "distance_change", "estimate_status", "pair_key"].map(field=>[field,row[field]]));
    return [{...values,column:row.series_low_id,row:row.series_high_id},
      {...values,column:row.series_high_id,row:row.series_low_id}];
  });
}

export function rankNodes(rows) {
  return rows.filter(row => row.group_comparison_status === "supported" &&
    Number.isFinite(row.absolute_deviation_from_group_mean))
    .sort((a, b) => b.absolute_deviation_from_group_mean - a.absolute_deviation_from_group_mean || a.series_id.localeCompare(b.series_id))
    .map(({series_id,absolute_deviation_from_group_mean})=>({series_id,divergence:absolute_deviation_from_group_mean}));
}

export function windowEvidence(evidence, pointIndex, pair) {
  if (!pair) return {points: [], rows: []};
  const selected = evidence.filter(row => row.series_id === pair.series_low_id || row.series_id === pair.series_high_id);
  const points = selected.flatMap(row => JSON.parse(row.window_point_ids).map(id => {
    const point = pointIndex.get(id);
    if (!point || point.series_id !== row.series_id) throw new Error("Invalid reviewed point reference");
    return point;
  }));
  const periods = new Map();
  for (const point of points) {
    const side = point.series_id === pair.series_low_id ? "left" : "right";
    const row = periods.get(point.reference_period) || {reference_period: point.reference_period};
    Object.assign(row, {[`${side}_value`]: point.value, [`${side}_status`]: point.status,
      [`${side}_source_records`]: point.source_records, [`${side}_available_on`]: point.available_on});
    periods.set(point.reference_period, row);
  }
  return {points, rows: [...periods.values()].sort((a, b) => a.reference_period.localeCompare(b.reference_period))};
}
