export interface RevisionQualitySummary {
  series_id: string;
  quality_status: "available" | "unknown";
  observation_count: number | null;
  avg_revision_count: number | null;
  max_revision_count: number | null;
  avg_abs_revision_pct: number | null;
  max_abs_revision_pct: number | null;
  source_extracted_at: string;
  temporal_status: "current_only_revision_quality";
  redistribution_status: "restricted";
  historical_support: "unsupported";
}

export interface RevisionQualityReport {
  publication: "macro_revision_quality";
  status: "selected" | "not_selected" | "not_published";
  series_node_id: string;
  snapshot_id?: string;
  published_at?: string;
  input_manifest_id?: string | null;
  build_run_id?: string | null;
  source_record?: string | null;
  summary: RevisionQualitySummary | null;
}

export function revisionQualityUrl(seriesNodeId: string) {
  return `/api/v1/macro-revision-quality?${new URLSearchParams({ series_node_id: seriesNodeId })}`;
}

export async function loadRevisionQuality(seriesNodeId: string, signal?: AbortSignal): Promise<RevisionQualityReport> {
  const response = await fetch(revisionQualityUrl(seriesNodeId), { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Revision quality API returned ${response.status}`);
  const report = await response.json() as RevisionQualityReport;
  if (report.series_node_id !== seriesNodeId) throw new Error("Revision quality returned a different series");
  return report;
}

export function formatQualityMetric(value: number | null, percent = false) {
  if (value === null || !Number.isFinite(value)) return "Unknown";
  return `${value.toLocaleString("en-US", { maximumFractionDigits: 3 })}${percent ? "%" : ""}`;
}
