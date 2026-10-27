import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, ExternalLink, Network, RefreshCw } from "lucide-react";
import { LIVE_GRAPH_VISUAL_PAGE_SIZE, loadLiveMacroGraph, type LiveGraphNode, type LiveMacroGraph } from "@/lib/liveMacroGraph";

import { RevisionQualityPanel } from "@/app/RevisionQualityPanel";

interface PositionedNode extends LiveGraphNode { x: number; y: number; }

function positionNodes(graph: LiveMacroGraph): PositionedNode[] {
  const series = graph.nodes.filter((node) => node.node_type === "macro_series");
  const concepts = graph.nodes.filter((node) => node.node_type === "economic_concept");
  const catalog = graph.nodes.filter((node) => node.node_type === "catalog_source");
  const position = (nodes: LiveGraphNode[], x: number) => nodes.map((node, index) => ({
    ...node, x, y: ((index + 1) * 100) / (nodes.length + 1),
  }));
  if (graph.view === "catalog_summary") return [...position(catalog, 20), ...position(concepts, 72)];
  const columns = Math.min(3, Math.max(1, Math.ceil(series.length / 4)));
  const rows = Math.max(1, Math.ceil(series.length / columns));
  const positionedSeries = series.map((node, index) => ({
    ...node,
    x: 16 + (index % columns) * (48 / Math.max(1, columns - 1)),
    y: ((Math.floor(index / columns) + 1) * 100) / (rows + 1),
  }));
  return [...positionedSeries, ...position(concepts, 84)];
}

function nodeKind(node: LiveGraphNode) {
  if (node.node_type === "macro_series") return "Macro series";
  return node.node_type === "catalog_source" ? "Catalog hub" : "Economic concept";
}

export function LiveMacroGraph() {
  const [graph, setGraph] = useState<LiveMacroGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [conceptId, setConceptId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = LIVE_GRAPH_VISUAL_PAGE_SIZE;

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    loadLiveMacroGraph({ conceptId, query: search, limit: pageSize, offset: page * pageSize }, controller.signal)
      .then((loaded) => {
        setGraph(loaded);
        setSelectedId((current) => loaded.nodes.some((node) => node.id === current) ? current : loaded.nodes[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load the live graph");
      });
    return () => controller.abort();
  }, [conceptId, page, reloadKey, search]);

  const nodes = useMemo(() => graph ? positionNodes(graph) : [], [graph]);
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const selected = selectedId ? nodeById.get(selectedId) : undefined;

  if (error) return <main className="kg-workspace"><section className="kg-stage"><div className="kg-canvas-wrap flex items-center justify-center p-8"><div className="max-w-lg text-center"><p className="kg-eyebrow">Live macro graph unavailable</p><h1 className="mt-3 text-2xl font-semibold">Start the report API, then retry.</h1><p className="mt-3 text-sm text-slate-300">The browser only requests the local report API; it never connects to PostgreSQL or MacroMedallion directly.</p><button type="button" className="kg-primary-action mt-5" onClick={() => setReloadKey((value) => value + 1)}><RefreshCw size={15} /> Retry</button></div></div></section></main>;
  if (!graph || !selected) return <main className="kg-workspace"><p className="p-8 text-sm text-slate-300">Loading the snapshot-pinned macro economic graph…</p></main>;

  const selectNode = (node: LiveGraphNode) => {
    setSelectedId(node.id);
    if (graph.view === "catalog_summary" && node.node_type === "economic_concept") {
      setConceptId(node.id);
      setPage(0);
      setSearch("");
    }
  };
  const hasPreviousPage = graph.pagination.offset > 0;
  const hasNextPage = graph.pagination.offset + graph.pagination.limit < graph.pagination.total;
  const selectedCount = typeof selected.details.series_count === "number" ? selected.details.series_count : null;

  return <main className="kg-workspace">
    <header className="kg-header"><div className="kg-brand"><span className="kg-brand__mark"><Network size={18} /></span><div><p className="kg-eyebrow">MarketAtlas / live evidence workspace</p><h1>Macro economic knowledge graph</h1><p>Approved source taxonomy; current-only, not point-in-time taxonomy history.</p></div></div><div className="kg-health"><span className="kg-health__dot" /><div><strong>Published and report-reader scoped</strong><span>Snapshot {graph.snapshot_id.slice(0, 8)} · {graph.published_at.slice(0, 10)}</span></div></div></header>
    {graph.view === "concept_neighborhood" && <div className="kg-toolbar"><button type="button" className="kg-toggle" onClick={() => { setConceptId(null); setPage(0); setSearch(""); }}><ArrowLeft size={14} /> All categories</button><label className="kg-search">Find a series<input value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} placeholder="Search this category" /></label></div>}
    <section className="kg-insights" aria-label="Live graph summary"><article><span>Approved series</span><strong>{graph.facets.series_count}</strong><small>published identities</small></article><article><span>Economic concepts</span><strong>{graph.facets.concept_count}</strong><small>taxonomy hubs</small></article><article><span>View</span><strong>{graph.view === "catalog_summary" ? "Catalog" : `${graph.pagination.total}`}</strong><small>{graph.view === "catalog_summary" ? "choose a category" : "matching series"}</small></article><article><span>Input manifest</span><strong>{graph.input_manifest_id.slice(0, 8)}</strong><small>immutable source lineage</small></article></section>
    <section className="kg-stage" aria-label="Live macro economic graph"><div className="kg-stage__ambient" /><div className="kg-canvas-wrap"><div className="kg-canvas"><svg aria-hidden="true" className="kg-edge-layer" viewBox="0 0 100 100" preserveAspectRatio="none">{graph.edges.map((edge) => { const from = nodeById.get(edge.source_node_id); const to = nodeById.get(edge.target_node_id); if (!from || !to) return null; return <g key={edge.id} className={`kg-edge kg-edge--source ${selectedId === from.id || selectedId === to.id ? "is-selected" : ""}`}><line x1={from.x} y1={from.y} x2={to.x} y2={to.y} />{graph.view === "catalog_summary" && edge.aggregate && <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 2}>{edge.series_count} series</text>}</g>; })}</svg>{nodes.map((node) => <button type="button" key={node.id} className={`kg-node kg-node--source ${selectedId === node.id ? "is-selected" : ""}`} style={{ left: `${node.x}%`, top: `${node.y}%` }} onClick={() => selectNode(node)} aria-pressed={selectedId === node.id}><span className="kg-node__dot" /><span className="kg-node__label">{node.display_label}</span><span className="kg-node__kind">{nodeKind(node)}{node.details.series_count ? ` · ${node.details.series_count} series` : ""}</span></button>)}</div><div className="kg-canvas__caption">{graph.view === "catalog_summary" ? "Category hubs are navigation summaries, not assertions" : graph.pagination.total === 0 ? "No approved series match this category search" : `Source-backed measures assertions · ${pageSize} visual nodes per page`}</div></div><aside className="kg-drawer"><div className="kg-drawer__topline"><span className="kg-eyebrow">Selected published object</span><button type="button" className="kg-icon-button" onClick={() => setReloadKey((value) => value + 1)} aria-label="Refresh live graph"><RefreshCw size={15} /></button></div><h2>{selected.display_label}</h2><p className="kg-drawer__kind">{nodeKind(selected)}</p><span className="kg-status kg-status--source">Source-backed · {selected.temporal_status}</span><p className="kg-drawer__description">{selectedCount ? `${selectedCount} approved series are available through this taxonomy hub. Select it to open a bounded neighborhood.` : "This object is shown from the immutable report publication. It is descriptive source taxonomy, not a causal or sensitivity claim."}</p><section className="kg-drawer__section"><h3>Source lineage</h3><dl className="kg-fields"><div><dt>Source record</dt><dd>{selected.source_record}</dd></div><div><dt>Canonical key</dt><dd>{selected.details.canonical_key}</dd></div><div><dt>Input manifest</dt><dd>{graph.input_manifest_id}</dd></div></dl><span className="kg-source-link"><ExternalLink size={14} /> Available through report API only</span></section>{selected.node_type === "macro_series" && <RevisionQualityPanel key={`${selected.id}:${reloadKey}`} seriesNodeId={selected.id} />}{graph.view === "concept_neighborhood" && <section className="kg-drawer__section"><h3>Page {Math.floor(graph.pagination.offset / pageSize) + 1} of {Math.max(1, Math.ceil(graph.pagination.total / pageSize))}</h3><div className="flex gap-2"><button type="button" className="kg-icon-button" disabled={!hasPreviousPage} onClick={() => setPage((value) => Math.max(0, value - 1))} aria-label="Previous series page"><ChevronLeft size={15} /></button><button type="button" className="kg-icon-button" disabled={!hasNextPage} onClick={() => setPage((value) => value + 1)} aria-label="Next series page"><ChevronRight size={15} /></button></div></section>}</aside></section>
  </main>;
}
