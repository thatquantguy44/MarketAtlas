import { useMemo, useState } from "react";
import {
  ChevronDown, ExternalLink, Maximize2, Minus, Network, PanelRightOpen, Plus,
  RotateCcw, Search, ShieldCheck, SlidersHorizontal, X
} from "lucide-react";
import {
  evidenceCopy, knowledgeEdges, knowledgeNodes, resolveConfiguredReviewer, reviewCandidates,
  type EvidenceState, type KnowledgeEdge, type KnowledgeNode, type ReviewCandidate, type ReviewStatus
} from "@/data/knowledgeGraph";
import { fixtureReportSnapshot } from "@/data/reportSnapshot";

const nodeById = new Map(knowledgeNodes.map((node) => [node.id, node]));
const lensOptions = knowledgeNodes.filter((node) => ["I-A", "O-A", "M-GROWTH"].includes(node.id));

function effectiveCandidateState(candidate: ReviewCandidate | undefined): EvidenceState {
  if (!candidate || candidate.reviewStatus === "unreviewed") return "candidate";
  return candidate.reviewStatus === "accepted" ? "reviewed" : "unavailable";
}

function statusClass(state: EvidenceState) {
  return `kg-status kg-status--${state}`;
}

function EdgeLayer({ edges, candidates, selectedId }: { edges: KnowledgeEdge[]; candidates: ReviewCandidate[]; selectedId: string }) {
  const candidateById = new Map(candidates.map((candidate) => [candidate.candidateId, candidate]));
  return <svg aria-hidden="true" className="kg-edge-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
    {edges.map((edge) => {
      const from = nodeById.get(edge.from)!;
      const to = nodeById.get(edge.to)!;
      const state = edge.candidateId ? effectiveCandidateState(candidateById.get(edge.candidateId)) : edge.evidenceState;
      const selected = edge.from === selectedId || edge.to === selectedId;
      return <g key={edge.id} className={`kg-edge kg-edge--${state} ${selected ? "is-selected" : ""}`}>
        <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
        <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 2}>{edge.label}</text>
      </g>;
    })}
  </svg>;
}

function GraphNodeButton({ node, selected, dimmed, onSelect }: { node: KnowledgeNode; selected: boolean; dimmed: boolean; onSelect: (id: string) => void }) {
  return <button
    type="button"
    className={`kg-node kg-node--${node.evidenceState} ${selected ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""}`}
    style={{ left: `${node.x}%`, top: `${node.y}%` }}
    onClick={() => onSelect(node.id)}
    aria-pressed={selected}
    aria-label={`${node.label}, ${node.kind}, ${evidenceCopy[node.evidenceState].label}`}
  >
    <span className="kg-node__dot" aria-hidden="true" />
    <span className="kg-node__label">{node.label}</span>
    <span className="kg-node__kind">{node.kind}</span>
  </button>;
}

function EvidenceDrawer({ node, candidate, onOpenEvidence, onReview }: { node: KnowledgeNode; candidate?: ReviewCandidate; onOpenEvidence: () => void; onReview: () => void }) {
  const state = candidate ? effectiveCandidateState(candidate) : node.evidenceState;
  const copy = evidenceCopy[state];
  return <aside aria-label="Evidence drawer" className="kg-drawer">
    <div className="kg-drawer__topline"><span className="kg-eyebrow">Selected object</span><PanelRightOpen size={16} aria-hidden="true" /></div>
    <h2>{node.label}</h2>
    <p className="kg-drawer__kind">{node.kind}</p>
    <span className={statusClass(state)}>{copy.label}</span>
    <p className="kg-drawer__description">{candidate?.reviewStatus === "rejected" ? "This candidate was rejected and remains visible only in review history." : copy.description}</p>
    <section className="kg-drawer__section">
      <h3>Source lineage</h3>
      <ol className="kg-lineage">{node.lineage.map((item) => <li key={item}>{item}</li>)}</ol>
      <a className="kg-source-link" href={node.sourceUrl}><ExternalLink size={14} /> Open original fixture record</a>
    </section>
    <section className="kg-drawer__section">
      <h3>Record details</h3>
      <dl className="kg-fields">{node.fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </section>
    {candidate && <section className="kg-candidate-callout"><span className="kg-eyebrow">Review treatment</span><p>{candidate.reviewStatus === "unreviewed" ? "A configured reviewer must decide this candidate with a written note." : "Review history is retained; a later action appends another decision."}</p>{candidate.reviewHistory.at(-1) && <p className="kg-review-history">Latest: {candidate.reviewHistory.at(-1)?.action} by {candidate.reviewHistory.at(-1)?.reviewer}</p>}<button type="button" className="kg-primary-action" onClick={onReview}>{candidate.reviewStatus === "unreviewed" ? "Review candidate" : "View review decision"}</button></section>}
    <button type="button" className="kg-secondary-action" onClick={onOpenEvidence}>Open scoped evidence <Maximize2 size={15} /></button>
  </aside>;
}

function ReviewQueue({ candidates, onSelect }: { candidates: ReviewCandidate[]; onSelect: (candidate: ReviewCandidate) => void }) {
  return <aside aria-label="Candidate review queue" className="kg-review-queue">
    <div className="kg-review-queue__header"><div><span className="kg-eyebrow">Review queue</span><h2>{candidates.length} candidate{candidates.length === 1 ? "" : "s"}</h2></div><ShieldCheck size={20} aria-hidden="true" /></div>
    {candidates.length === 0 ? <p className="kg-muted-copy">No candidates match this lens.</p> : candidates.map((candidate) => <button key={candidate.candidateId} type="button" className="kg-candidate-row" onClick={() => onSelect(candidate)}>
      <span className={statusClass(effectiveCandidateState(candidate))}>{candidate.reviewStatus === "unreviewed" ? "Unreviewed" : candidate.reviewStatus}</span>
      <strong>{nodeById.get(candidate.candidateEntityId)?.label}</strong>
      <span>{Math.round(candidate.matchScore * 100)}% · {candidate.matchMethod}</span>
    </button>)}
  </aside>;
}

function EvidenceWorkspace({ selectedNode, edges, onSelect, onClose }: { selectedNode: KnowledgeNode; edges: KnowledgeEdge[]; onSelect: (id: string) => void; onClose: () => void }) {
  const direct = edges.filter((edge) => edge.from === selectedNode.id || edge.to === selectedNode.id);
  return <div className="kg-modal-backdrop" role="presentation"><section role="dialog" aria-modal="true" aria-labelledby="evidence-workspace-title" className="kg-modal kg-evidence-modal">
    <button type="button" className="kg-icon-button kg-modal__close" onClick={onClose} aria-label="Close full evidence workspace"><X size={18} /></button>
    <span className="kg-eyebrow">Full scoped evidence</span><h2 id="evidence-workspace-title">Evidence paths for {selectedNode.label}</h2>
    <p>Direct relationships are listed first. Source-path records retain their treatment so this view does not imply a broader conclusion.</p>
    <div className="kg-evidence-list">{direct.map((edge) => {
      const related = nodeById.get(edge.from === selectedNode.id ? edge.to : edge.from)!;
      return <button type="button" key={edge.id} onClick={() => { onSelect(related.id); onClose(); }}>
        <span className={statusClass(edge.evidenceState)}>{evidenceCopy[edge.evidenceState].label}</span>
        <strong>{edge.label}</strong><span>{related.label} · {related.kind}</span>
      </button>;
    })}</div>
  </section></div>;
}

function ReviewModal({ candidate, onClose, onDecision }: { candidate: ReviewCandidate; onClose: () => void; onDecision: (action: "accepted" | "rejected" | "reopened", note: string) => void }) {
  const [note, setNote] = useState("");
  const reviewer = resolveConfiguredReviewer(candidate.sector);
  const canDecide = note.trim().length > 0;
  const handleDecision = (action: "accepted" | "rejected" | "reopened") => {
    if (!canDecide) return;
    onDecision(action, note.trim());
    onClose();
  };
  return <div className="kg-modal-backdrop" role="presentation"><section role="dialog" aria-modal="true" aria-labelledby="review-candidate-title" className="kg-modal">
    <button type="button" className="kg-icon-button kg-modal__close" onClick={onClose} aria-label="Close review decision"><X size={18} /></button>
    <span className="kg-eyebrow">Candidate decision</span><h2 id="review-candidate-title">Review {nodeById.get(candidate.candidateEntityId)?.label}</h2>
    <p className="kg-review-meta">{candidate.matchMethod} · {Math.round(candidate.matchScore * 100)}% match · {reviewer}</p>
    <p className="kg-modal__notice">Demo mode only: a production decision endpoint must resolve this reviewer server-side and append an audit event rather than overwrite history.</p>
    <label className="kg-note-label" htmlFor="review-note">Decision note <span>required</span></label>
    <textarea id="review-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="State the evidence used for this decision." rows={4} />
    <div className="kg-modal__actions">{candidate.reviewStatus === "unreviewed" && <><button type="button" className="kg-secondary-action" disabled={!canDecide} onClick={() => handleDecision("rejected")}>Reject candidate</button><button type="button" className="kg-primary-action" disabled={!canDecide} onClick={() => handleDecision("accepted")}>Approve connection</button></>}{candidate.reviewStatus !== "unreviewed" && <button type="button" className="kg-primary-action" disabled={!canDecide} onClick={() => handleDecision("reopened")}>Reopen for review</button>}</div>
  </section></div>;
}

export function KnowledgeGraphWorkspace() {
  const [selectedId, setSelectedId] = useState("I-A");
  const [lensId, setLensId] = useState("I-A");
  const [scope, setScope] = useState<"one-hop" | "evidence">("one-hop");
  const [showCandidates, setShowCandidates] = useState(false);
  const [search, setSearch] = useState("");
  const [zoom, setZoom] = useState(1);
  const [expandedCluster, setExpandedCluster] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [reviewingCandidateId, setReviewingCandidateId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState(reviewCandidates);
  const selectedNode = nodeById.get(selectedId) ?? knowledgeNodes[0];
  const candidateForSelected = candidates.find((candidate) => candidate.sourceRecordId === selectedId);
  const reviewingCandidate = candidates.find((candidate) => candidate.candidateId === reviewingCandidateId);
  const query = search.trim().toLocaleLowerCase();

  const visibleEdges = useMemo(() => knowledgeEdges.filter((edge) => {
    const candidate = edge.candidateId ? candidates.find((item) => item.candidateId === edge.candidateId) : undefined;
    if (edge.candidateId && (!showCandidates || candidate?.reviewStatus === "rejected")) return false;
    if (scope === "one-hop" && edge.from !== lensId && edge.to !== lensId) return false;
    if (scope === "evidence" && !expandedCluster && edge.evidenceState === "source" && edge.from.startsWith("SRC-") && edge.from !== "SRC-A4") return false;
    return true;
  }), [candidates, expandedCluster, lensId, scope, showCandidates]);

  const visibleNodeIds = useMemo(() => new Set([lensId, ...visibleEdges.flatMap((edge) => [edge.from, edge.to])]), [lensId, visibleEdges]);
  const queueCandidates = candidates.filter((candidate) => candidate.reviewStatus === "unreviewed" || candidate.sourceRecordId === selectedId);
  const setLens = (id: string) => { setLensId(id); setSelectedId(id); setExpandedCluster(false); };
  const resetWorkspace = () => { setSelectedId("I-A"); setLensId("I-A"); setScope("one-hop"); setShowCandidates(false); setSearch(""); setZoom(1); setExpandedCluster(false); };
  const recordDecision = (action: "accepted" | "rejected" | "reopened", note: string) => {
    if (!reviewingCandidate) return;
    setCandidates((current) => current.map((candidate) => candidate.candidateId !== reviewingCandidate.candidateId ? candidate : {
      ...candidate,
      reviewStatus: action === "reopened" ? "unreviewed" : action,
      reviewHistory: [...candidate.reviewHistory, { id: `${candidate.candidateId}-${candidate.reviewHistory.length + 1}`, action, reviewer: resolveConfiguredReviewer(candidate.sector), note, timestamp: new Date().toISOString() }]
    }));
  };
  const { counts } = fixtureReportSnapshot.metadata;

  return <main className="kg-workspace">
    <header className="kg-header">
      <div className="kg-brand"><span className="kg-brand__mark"><Network size={18} /></span><div><p className="kg-eyebrow">MarketAtlas / evidence workspace</p><h1>Knowledge graph review</h1><p>Explore only what the current fixture can support.</p></div></div>
      <div className="kg-health"><span className="kg-health__dot" /><div><strong>Data health: ready</strong><span>Snapshot pinned · fixture only</span></div></div>
    </header>

    <section aria-label="Graph controls" className="kg-toolbar">
      <label className="kg-select"><span>Pipeline</span><select aria-label="Pipeline filter" defaultValue="published"><option value="published">Published snapshot</option><option value="fixture">Synthetic fixture</option></select><ChevronDown size={14} /></label>
      <label className="kg-select"><span>Lens</span><select aria-label="Knowledge graph lens" value={lensId} onChange={(event) => setLens(event.target.value)}>{lensOptions.map((node) => <option value={node.id} key={node.id}>{node.label}</option>)}</select><ChevronDown size={14} /></label>
      <label className="kg-select"><span>Relationship scope</span><select aria-label="Relationship scope" value={scope} onChange={(event) => setScope(event.target.value as "one-hop" | "evidence")}><option value="one-hop">One hop</option><option value="evidence">This entity’s evidence</option></select><ChevronDown size={14} /></label>
      <button type="button" className={`kg-toggle ${showCandidates ? "is-on" : ""}`} aria-pressed={showCandidates} onClick={() => setShowCandidates((value) => !value)}><ShieldCheck size={15} /> Review candidates</button>
      <label className="kg-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search this view" aria-label="Search graph" /></label>
      <button type="button" className="kg-reset" onClick={resetWorkspace}><RotateCcw size={15} /> Reset</button>
    </section>

    <section className="kg-insights" aria-label="Graph summary">
      <article><span>Canonical entities</span><strong>{counts.nodes}</strong><small>in this snapshot</small></article>
      <article><span>Source-backed links</span><strong>{counts.relationships}</strong><small>assertion facts</small></article>
      <article><span>Curated context</span><strong>{counts.contexts}</strong><small>not causal claims</small></article>
      <article><span>Pending review</span><strong>{candidates.filter((candidate) => candidate.reviewStatus === "unreviewed").length}</strong><small>candidate connection</small></article>
    </section>

    <section className="kg-stage" aria-label="Knowledge graph canvas">
      <div className="kg-stage__ambient" aria-hidden="true" />
      {showCandidates && <ReviewQueue candidates={queueCandidates} onSelect={(candidate) => setSelectedId(candidate.sourceRecordId)} />}
      <div className="kg-canvas-wrap">
        <div className="kg-canvas" style={{ transform: `scale(${zoom})` }}>
          <EdgeLayer edges={visibleEdges} candidates={candidates} selectedId={selectedId} />
          {knowledgeNodes.filter((node) => visibleNodeIds.has(node.id)).map((node) => <GraphNodeButton key={node.id} node={node} selected={node.id === selectedId} dimmed={Boolean(query) && !`${node.label} ${node.kind}`.toLocaleLowerCase().includes(query)} onSelect={setSelectedId} />)}
          <button type="button" className={`kg-cluster ${expandedCluster ? "is-expanded" : ""}`} onClick={() => setExpandedCluster((value) => !value)} aria-pressed={expandedCluster}><span>{expandedCluster ? "9 records expanded" : "9 more records"}</span><small>{expandedCluster ? "Collapse this cluster" : "Expand for evidence paths"}</small></button>
        </div>
        <div className="kg-canvas__caption"><SlidersHorizontal size={15} /> {scope === "one-hop" ? "Focused one-hop neighborhood" : "Full entity-scoped evidence"} · shared hubs stop traversal</div>
        <div className="kg-view-controls" aria-label="Canvas controls"><button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.8, Number((value - 0.1).toFixed(1))))}><Minus size={16} /></button><span>{Math.round(zoom * 100)}%</span><button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.2, Number((value + 0.1).toFixed(1))))}><Plus size={16} /></button><button type="button" onClick={() => setZoom(1)}>Recenter</button></div>
      </div>
      <EvidenceDrawer node={selectedNode} candidate={candidateForSelected} onOpenEvidence={() => setEvidenceOpen(true)} onReview={() => setReviewingCandidateId(candidateForSelected?.candidateId ?? null)} />
    </section>

    <section className="kg-legend" aria-label="Evidence legend"><div><span className="kg-eyebrow">Evidence legend</span><p>Color, line treatment, and labels work together—never color alone.</p></div><div className="kg-legend__items"><span className={statusClass("source")}>Source-backed</span><span className={statusClass("reviewed")}>Reviewed</span><span className={statusClass("candidate")}>Candidate</span><span className={statusClass("inferred")}>Context only</span><span className={statusClass("unavailable")}>Unavailable</span></div></section>
    {evidenceOpen && <EvidenceWorkspace selectedNode={selectedNode} edges={visibleEdges} onSelect={setSelectedId} onClose={() => setEvidenceOpen(false)} />}
    {reviewingCandidate && <ReviewModal candidate={reviewingCandidate} onClose={() => setReviewingCandidateId(null)} onDecision={recordDecision} />}
  </main>;
}
