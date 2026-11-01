import React, { useEffect, useState } from "react";
import { Button, DataComponent, useDataApp } from "../../data-app-public.jsx";

function stamp(value) {
  return value ? new Date(value).toLocaleString(undefined, {timeZoneName:"short"}) : "Unknown";
}

export function RefreshStatus() {
  const { queries } = useDataApp();
  const embedded = queries.refresh_status?.rows?.[0];
  const [monitor, setMonitor] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    const read = () => fetch("/refresh-status.json", {cache:"no-store", signal:controller.signal})
      .then(response => response.ok ? response.json() : null)
      .then(value => { if (!controller.signal.aborted) setMonitor(value); })
      .catch(() => {});
    read();
    const timer = setInterval(read, 30000);
    return () => { clearInterval(timer); controller.abort(); };
  }, []);
  if (!embedded) return null;
  const newer = monitor?.last_success?.pack_id && (monitor.last_success.pack_id !== embedded.pack_id ||
    monitor.last_success.analytics_pack_id !== embedded.analytics_pack_id);
  const failed = monitor?.last_attempt?.status === "failed";
  return <DataComponent id="report-refresh-status" queryId="refresh_status" kind="metric"
    title="Report refresh and source freshness" sourceRows={[embedded]} displayRows={[embedded]}>
    <div role="status" aria-live="polite" data-reviewed-rows>
      <p>Report refreshed {stamp(embedded.refreshed_at)} · {embedded.stale_coverage_records} records
        flagged stale by upstream age rules out of {embedded.source_coverage_records} · {embedded.unknown_coverage_records} unknown.</p>
      <p>Age rules use observation periods. A flag can remain when the database matches the latest provider release.</p>
      <p>Upstream ingestion: {embedded.upstream_ingestion.replaceAll("_", " ")}.</p>
      {failed && <p>Refresh attempt failed at {monitor.last_attempt.stage} ({stamp(monitor.last_attempt.at)}).
        The last successful report is still available.</p>}
      {newer && <p>Newer validated data are available. <Button onClick={() => window.location.reload()}>Reload report</Button></p>}
    </div>
  </DataComponent>;
}
