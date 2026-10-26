import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Network, RefreshCw } from "lucide-react";
import { loadLiveMacroGraph, type LiveGraphNode, type LiveMacroGraph } from "@/lib/liveMacroGraph";

interface PositionedNode extends LiveGraphNode { x: number; y: number; }

function positionNodes(graph: LiveMacroGraph): PositionedNode[] {
  const series = graph.nodes.filter((node) => node.node_type === "macro_series");
  const concepts = graph.nodes.filter((node) => node.node_type === "economic_concept");
  const position = (nodes: LiveGraphNode[], x: number) => nodes.map((node, index) => ({
    ...node, x, y: ((index + 1) * 100) / (nodes.length + 1),
  }));
  return [...position(series, 28), ...position(concepts, 72)];
}

function nodeKind(node: LiveGraphNode) {
  return node.node_type === "macro_series" ? "Macro series" : "Economic concept";
}

export function LiveMacroGraph() {
  const [graph, setGraph] = useState<LiveMacroGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    loadLiveMacroGraph(controller.signal)
      .then((loaded) => {
        setGraph(loaded);
        setSelectedId((current) => current ?? loaded.nodes[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load the live graph");
      });
    return () => controller.abort();
  }, [reloadKey]);

  const nodes = useMemo(() => graph ? positionNodes(graph) : [], [graph]);
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const selected = selectedId ? nodeById.get(selectedId) : undefined;

  if (error) return <main className="kg-workspace"><section className="kg-stage"><div className="kg-canvas-wrap flex items-center justify-center p-8"><div className="max-w-lg text-center"><p className="kg-eyebrow">Live macro graph unavailable</p><h1 className="mt-3 text-2xl font-semibold">Start the report API, then retry.</h1><p className="mt-3 text-sm text-slate-300">The browser only requests the local report API; it never connects to PostgreSQL or MacroMedallion directly.</p><button type="button" className="kg-primary-action mt-5" onClick={() => setReloadKey((value) => value + 1)}><RefreshCw size={15} /> Retry</button></div></div></section></main>;
  if (!graph || !selected) return <main className="kg-workspace"><p className="p-8 text-sm text-slate-300">Loading the snapshot-pinned macro economic graph…</p></main>;

  return <main className="kg-workspace">
    <header className="kg-header"><div className="kg-brand"><span className="kg-brand__mark"><Network size={18} /></span><div><p className="kg-eyebrow">MarketAtlas / live evidence workspace</p><h1>Macro economic knowledge graph</h1><p>Source taxonomy projection; current-only, not point-in-time taxonomy history.</p></div></div><div className="kg-health"><span className="kg-health__dot" /><div><strong>Published and report-reader scoped</strong><span>Snapshot {graph.snapshot_id.slice(0, 8)} · {graph.published_at.slice(0, 10)}</span></div></div></header>
    <section className="kg-insights" aria-label="Live graph summary"><article><span>Canonical nodes</span><strong>{graph.nodes.length}</strong><small>published identities</small></article><article><span>Measures edges</span><strong>{graph.edges.length}</strong><small>source-backed assertions</small></article><article><span>Temporal treatment</span><strong>Current</strong><small>taxonomy projection only</small></article><article><span>Input manifest</span><strong>{graph.input_manifest_id.slice(0, 8)}</strong><small>immutable source lineage</small></article></section>
    <section className="kg-stage" aria-label="Live macro economic graph"><div className="kg-stage__ambient" /><div className="kg-canvas-wrap"><div className="kg-canvas"><svg aria-hidden="true" className="kg-edge-layer" viewBox="0 0 100 100" preserveAspectRatio="none">{graph.edges.map((edge) => { const from = nodeById.get(edge.source_node_id); const to = nodeById.get(edge.target_node_id); if (!from || !to) return null; return <g key={edge.id} className={`kg-edge kg-edge--source ${selectedId === from.id || selectedId === to.id ? "is-selected" : ""}`}><line x1={from.x} y1={from.y} x2={to.x} y2={to.y} /><text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 2}>measures</text></g>; })}</svg>{nodes.map((node) => <button type="button" key={node.id} className={`kg-node kg-node--source ${selectedId === node.id ? "is-selected" : ""}`} style={{ left: `${node.x}%`, top: `${node.y}%` }} onClick={() => setSelectedId(node.id)} aria-pressed={selectedId === node.id}><span className="kg-node__dot" /><span className="kg-node__label">{node.display_label}</span><span className="kg-node__kind">{nodeKind(node)}</span></button>)}</div><div className="kg-canvas__caption">Source-backed `measures` assertions · current taxonomy snapshot</div></div><aside className="kg-drawer"><div className="kg-drawer__topline"><span className="kg-eyebrow">Selected published object</span><button type="button" className="kg-icon-button" onClick={() => setReloadKey((value) => value + 1)} aria-label="Refresh live graph"><RefreshCw size={15} /></button></div><h2>{selected.display_label}</h2><p className="kg-drawer__kind">{nodeKind(selected)}</p><span className="kg-status kg-status--source">Source-backed · {selected.temporal_status}</span><p className="kg-drawer__description">This object is shown from the immutable `macro_economic_graph` report publication. It is descriptive source taxonomy, not a causal or sensitivity claim.</p><section className="kg-drawer__section"><h3>Source lineage</h3><dl className="kg-fields"><div><dt>Source record</dt><dd>{selected.source_record}</dd></div><div><dt>Canonical key</dt><dd>{selected.details.canonical_key}</dd></div><div><dt>Input manifest</dt><dd>{graph.input_manifest_id}</dd></div></dl><span className="kg-source-link"><ExternalLink size={14} /> Available through report API only</span></section></aside></section>
  </main>;
}
