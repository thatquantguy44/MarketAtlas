import { useEffect, useState } from "react";
import { formatQualityMetric, loadRevisionQuality, type RevisionQualityReport } from "@/lib/revisionQuality";

function captureTime(value: string) {
  return new Date(value).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

export function RevisionQualityPanel({ seriesNodeId }: { seriesNodeId: string }) {
  const [report, setReport] = useState<RevisionQualityReport | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    loadRevisionQuality(seriesNodeId, controller.signal)
      .then((loaded) => { if (!controller.signal.aborted) setReport(loaded); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [seriesNodeId]);

  const summary = report?.summary;
  return <section className="kg-drawer__section kg-quality" aria-label="Revision quality context" aria-live="polite">
    <h3>Revision quality</h3>
    <p className="kg-quality__notice">Current context · Restricted internal use</p>
    {failed ? <p>Revision quality is unavailable. Refresh to retry.</p>
      : !report ? <p>Loading revision quality…</p>
      : report.status === "not_published" ? <p>No revision-quality snapshot has been published.</p>
      : report.status === "not_selected" ? <p>This series is outside the published revision-quality selection.</p>
      : summary ? <>
        {summary.quality_status === "unknown" ? <p>No summary was returned for this selected series. Revision quality is unknown.</p>
          : <dl className="kg-fields">
            <div><dt>Observations summarized</dt><dd>{formatQualityMetric(summary.observation_count)}</dd></div>
            <div><dt>Average revision count</dt><dd>{formatQualityMetric(summary.avg_revision_count)}</dd></div>
            <div><dt>Maximum revision count</dt><dd>{formatQualityMetric(summary.max_revision_count)}</dd></div>
            <div><dt>Average absolute revision</dt><dd>{formatQualityMetric(summary.avg_abs_revision_pct, true)}</dd></div>
            <div><dt>Maximum absolute revision</dt><dd>{formatQualityMetric(summary.max_abs_revision_pct, true)}</dd></div>
          </dl>}
        <p className="kg-quality__notice">Captured {captureTime(summary.source_extracted_at)}. Historical availability is unsupported.</p>
        <details className="kg-quality__provenance"><summary>Quality publication provenance</summary><dl className="kg-fields">
          <div><dt>Snapshot</dt><dd>{report.snapshot_id}</dd></div>
          <div><dt>Published</dt><dd>{report.published_at ? captureTime(report.published_at) : "Unknown"}</dd></div>
          <div><dt>Input manifest</dt><dd>{report.input_manifest_id}</dd></div>
          <div><dt>Build</dt><dd>{report.build_run_id}</dd></div>
          <div><dt>Source record</dt><dd>{report.source_record}</dd></div>
        </dl></details>
      </> : <p>Revision quality is unknown.</p>}
  </section>;
}
