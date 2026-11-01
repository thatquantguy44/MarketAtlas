import React from "react";
import { RefreshStatus } from "./RefreshStatus.jsx";
import { MacroAnalytics } from "./MacroAnalytics.jsx";
import { DataComponent, DataTable, EvidenceChart, Filters, MetricCard, Section,
  SortableItem, SortableRegion, useDataApp, useDashboardTabs, useSectionFilters } from "../../data-app-public.jsx";

const tabs = [
  { id: "catalog", label: "Catalog coverage" },
  { id: "freshness", label: "Releases and freshness" },
  { id: "quality", label: "Revision quality" },
  { id: "publications", label: "Publications and evidence" },
  { id: "analytics", label: "Relationship research" },
];
const columns = (pairs) => pairs.map(([field, label]) => ({ field, label }));

function EvidenceTable({ id, queryId, title, rows, fields, ...scope }) {
  return <DataComponent variant="card" id={id} kind="table" queryId={queryId}
    title={title} {...scope} sourceRows={rows} displayRows={rows}>
    <DataTable rows={rows} columns={columns(fields)} label={title} />
  </DataComponent>;
}

export function DashboardContent() {
  const { reviewedRows } = useDataApp();
  const { activeTabId } = useDashboardTabs(tabs);
  const catalogScope = useSectionFilters([
    { id: "concept", label: "Economic concept", field: "concept", defaultValue: "all",
      queryIds: ["catalog", "concept_coverage"] },
  ], {}, { id: "catalog-concept" });
  const qualityScope = useSectionFilters([
    { id: "series", label: "Series", field: "series_id", defaultValue: "all", queryIds: ["revision_quality"] },
  ], {}, { id: "quality-series" });
  const coverage = catalogScope.componentProps("concept_coverage", ["concept"]);
  const catalog = catalogScope.componentProps("catalog", ["concept", "node_id"]);
  const quality = qualityScope.componentProps("revision_quality", ["series_id"]);
  const contexts = reviewedRows("source_context");
  const releases = contexts.filter(row => row.context_kind === "release_event").sort((a,b) => a.effective_date.localeCompare(b.effective_date));
  const sourceCoverage = contexts.filter(row => row.context_kind === "source_coverage");
  if (activeTabId === "analytics") return <article><RefreshStatus/><MacroAnalytics/></article>;
  const blocks = [];
  const add = (id, title, content, kind="table", span=12) => blocks.push({id,title,content,kind,span});
  if (activeTabId === "catalog") {
    add("catalog-count", "Cataloged series", <MetricCard id="catalog-count" queryId="catalog"
      title="Cataloged series" value={new Set(catalog.displayRows.map(row=>row.node_id)).size}
      {...catalog} />, "metric", 6);
    add("concept-count", "Economic concepts", <MetricCard id="concept-count" queryId="concept_coverage"
      title="Economic concepts" value={coverage.displayRows.length} {...coverage} />, "metric", 6);
    add("catalog-concepts", "Series by economic concept", <EvidenceChart variant="card"
      id="catalog-concepts" queryId="concept_coverage" title="Series by economic concept"
      spec={{type:"horizontalBar",x:"concept",y:"series",sortOrder:"descending",valueDecimals:0,
        colors:{series:"var(--chart-1)"},stackable:false}}
      {...coverage} rows={coverage.displayRows} height={440} />, "chart");
    add("catalog-series", "Series catalog", <EvidenceTable id="catalog-series" queryId="catalog"
      title="Series catalog" {...catalog} rows={catalog.displayRows}
      fields={[["series","Series"],["concept","Concept"],["frequency","Frequency"],["units","Units"],["source_record","Source record"]]} />);
  } else if (activeTabId === "freshness") {
    add("release-calendar", "Captured release calendar", <EvidenceTable id="release-calendar"
      queryId="source_context" title="Captured release calendar" rows={releases}
      fields={[["effective_date","Release date"],["details_release_name","Release"],["details_importance","Importance"],["details_source_extracted_at","Source captured (UTC)"]]} />);
    add("source-coverage", "Coverage and source freshness", <EvidenceTable id="source-coverage"
      queryId="source_context" title="Coverage and source freshness" rows={sourceCoverage}
      fields={[["details_series_id","Series"],["details_latest_observation_date","Latest observation"],["details_observation_count","Observations"],["details_is_stale","Source stale flag"],["details_source_extracted_at","Source captured (UTC)"]]} />);
  } else if (activeTabId === "quality") {
    add("quality-details", "Captured-current revision summaries", <EvidenceTable id="quality-details"
      queryId="revision_quality" title="Captured-current revision summaries" {...quality} rows={quality.displayRows}
      fields={[["series_id","Series"],["details_quality_status","Status"],["details_observation_count","Observations"],["details_avg_revision_count","Mean revisions"],["details_max_revision_count","Max revisions"],["details_avg_abs_revision_pct","Mean absolute revision (%)"],["details_source_extracted_at","Source captured (UTC)"]]} />);
    add("quality-evidence", "Revision-quality evidence", <EvidenceTable id="quality-evidence"
      queryId="quality_provenance" title="Revision-quality evidence"
      rows={reviewedRows("quality_provenance").filter(row=>quality.displayRows.some(q=>q.revision_quality_version_id===row.subject_id))}
      fields={[["subject_id","Subject"],["source_record","Source record"],["method_version","Method"],["knowledge_cutoff","Knowledge cutoff (UTC)"],["build_run_id","Build run"]]} />);
  } else {
    add("publication-status", "Independent publication snapshots", <EvidenceTable id="publication-status"
      queryId="publications" title="Independent publication snapshots" rows={reviewedRows("publications")}
      fields={[["publication_name","Publication"],["serving_snapshot_id","Snapshot"],["published_at","Published (UTC)"],["knowledge_cutoff","Knowledge cutoff (UTC)"]]} />);
    for (const [id, queryId, title] of [["graph-evidence","macro_graph_provenance","Graph evidence"],
      ["context-evidence","source_context_provenance","Context evidence"]]) {
      add(id,title,<EvidenceTable id={id} queryId={queryId} title={title} rows={reviewedRows(queryId)}
        fields={[["provenance_kind","Kind"],["subject_id","Subject"],["source_record","Source record"],["input_manifest_id","Input manifest"],["build_run_id","Build run"],["knowledge_cutoff","Knowledge cutoff (UTC)"]]} />);
    }
  }
  return <article>
    <RefreshStatus />
    <p data-editable-id="report-scope" data-editable-narrative>
      Restricted internal data · current economic taxonomy. Catalog membership does not imply observation ingestion.
      Publication time is separate from source freshness. Unknown metrics remain blank.
    </p>
    <Section id="macro-report-section" title={tabs.find(tab=>tab.id===activeTabId)?.label || "Catalog coverage"}
      filters={activeTabId==="catalog" ? <Filters {...catalogScope.filterProps}/> : activeTabId==="quality" ? <Filters {...qualityScope.filterProps}/> : null}>
      <SortableRegion id={`macro-report:${activeTabId}`} variant="canvas" columns={12} spacing="standard"
        rows={[...(activeTabId==="catalog" ? [{id:"row:catalog-metrics",items:["catalog-count","concept-count"],kind:"metrics"}] : []), ...blocks.filter(block=>block.kind!=="metric").map(block=>({id:`row:${block.id}`,items:[block.id]}))]}>
        {blocks.map(block=><SortableItem key={block.id} id={block.id} label={block.title} kind={block.kind} span={block.span}>
          {block.content}
        </SortableItem>)}
      </SortableRegion>
    </Section>
  </article>;
}
