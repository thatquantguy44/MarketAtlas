export type EvidenceState = "source" | "reviewed" | "candidate" | "inferred" | "unavailable";
export type ReviewStatus = "unreviewed" | "accepted" | "rejected";

export interface KnowledgeNode {
  id: string;
  label: string;
  kind: string;
  evidenceState: EvidenceState;
  sourceLabel: string;
  sourceUrl: string;
  description: string;
  lineage: string[];
  fields: Array<[string, string]>;
  x: number;
  y: number;
}

export interface KnowledgeEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  evidenceState: EvidenceState;
  candidateId?: string;
}

export interface ReviewEvent {
  id: string;
  action: "accepted" | "rejected" | "reopened";
  reviewer: string;
  note: string;
  timestamp: string;
}

export interface ReviewCandidate {
  candidateId: string;
  sourceRecordId: string;
  candidateEntityId: string;
  sector: string;
  matchScore: number;
  matchMethod: string;
  reviewStatus: ReviewStatus;
  reviewHistory: ReviewEvent[];
}

export const knowledgeNodes: KnowledgeNode[] = [
  {
    id: "I-A", label: "Synthetic Alpha Share", kind: "Canonical instrument", evidenceState: "source",
    sourceLabel: "Fixture instrument record", sourceUrl: "#fixture-instrument", description: "The selected instrument is the anchor for this bounded evidence neighborhood.",
    lineage: ["Synthetic fixture", "Instrument identity", "Published snapshot"], fields: [["Identifier", "SYN-A"], ["Status", "Active fixture identity"], ["Snapshot", "fixture-snapshot-0b918c49"]], x: 42, y: 51
  },
  {
    id: "O-A", label: "Alpha Fictional Corp", kind: "Issuer", evidenceState: "source",
    sourceLabel: "Fixture relationship A4", sourceUrl: "#fixture-a4", description: "A source-backed issuer relationship for the selected instrument.",
    lineage: ["Synthetic fixture A4", "issued_by assertion", "Published snapshot"], fields: [["Relationship", "issued_by"], ["Evidence", "Source-derived"], ["Record", "synthetic-fixture:A4"]], x: 68, y: 31
  },
  {
    id: "S-TECH", label: "Synthetic Technology", kind: "Classification", evidenceState: "reviewed",
    sourceLabel: "Fixture classification A6", sourceUrl: "#fixture-a6", description: "A reviewed classification connection with retained fixture evidence.",
    lineage: ["Synthetic fixture A6", "classified_as assertion", "Published snapshot"], fields: [["Relationship", "classified_as"], ["Review status", "Analyst-reviewed fixture"], ["Taxonomy", "Synthetic sector v1"]], x: 84, y: 63
  },
  {
    id: "M-GROWTH", label: "Synthetic Growth Index", kind: "Macro series", evidenceState: "inferred",
    sourceLabel: "Fixture macro context CTX3", sourceUrl: "#fixture-context", description: "Curated macro context. This is explanatory context, not a sensitivity or causal claim.",
    lineage: ["Curated fixture mapping CTX3", "Context-only treatment", "Published snapshot"], fields: [["Treatment", "Context only"], ["Owner", "synthetic-mapping-owner"], ["Taxonomy", "Synthetic macro v1"]], x: 69, y: 81
  },
  {
    id: "SRC-A4", label: "Issuer source record", kind: "Original record", evidenceState: "source",
    sourceLabel: "synthetic-fixture:A4", sourceUrl: "#source-a4", description: "The original synthetic record supporting the issuer relationship.",
    lineage: ["Synthetic fixture", "Source record A4"], fields: [["Source", "Synthetic fixture"], ["Retrieved", "Fixture build"], ["Evidence", "Original record"]], x: 17, y: 24
  },
  {
    id: "SRC-CTX", label: "Context source record", kind: "Original record", evidenceState: "source",
    sourceLabel: "synthetic-fixture:CTX3", sourceUrl: "#source-context", description: "The supporting record for the curated market-context mapping.",
    lineage: ["Synthetic fixture", "Curated context CTX3"], fields: [["Source", "Synthetic fixture"], ["Retrieved", "Fixture build"], ["Evidence", "Context support"]], x: 17, y: 76
  },
  {
    id: "SRC-CAND", label: "Unresolved issuer record", kind: "Candidate record", evidenceState: "candidate",
    sourceLabel: "synthetic-fixture:C-001", sourceUrl: "#source-candidate", description: "A candidate match. It requires human review and cannot support a conclusion yet.",
    lineage: ["Synthetic fixture C-001", "Candidate matcher v1"], fields: [["Match score", "0.87"], ["Method", "fixture-token-match-v1"], ["Review", "Unreviewed"]], x: 18, y: 51
  }
];

export const knowledgeEdges: KnowledgeEdge[] = [
  { id: "A4", from: "I-A", to: "O-A", label: "issued by", evidenceState: "source" },
  { id: "A6", from: "O-A", to: "S-TECH", label: "classified as", evidenceState: "reviewed" },
  { id: "CTX3", from: "I-A", to: "M-GROWTH", label: "context only", evidenceState: "inferred" },
  { id: "P-A4", from: "SRC-A4", to: "I-A", label: "source path", evidenceState: "source" },
  { id: "P-CTX", from: "SRC-CTX", to: "M-GROWTH", label: "source path", evidenceState: "source" },
  { id: "C-001", from: "SRC-CAND", to: "I-A", label: "candidate identity", evidenceState: "candidate", candidateId: "candidate-001" }
];

export const reviewCandidates: ReviewCandidate[] = [
  {
    candidateId: "candidate-001", sourceRecordId: "SRC-CAND", candidateEntityId: "I-A", sector: "technology",
    matchScore: 0.87, matchMethod: "fixture-token-match-v1", reviewStatus: "unreviewed", reviewHistory: []
  }
];

const reviewerBySector: Record<string, string> = { technology: "Sector reviewer · Technology" };

export function resolveConfiguredReviewer(sector: string) {
  // The production adapter resolves this server-side. The static fixture has one configured sector reviewer.
  return reviewerBySector[sector] ?? "Unassigned reviewer";
}

export const evidenceCopy: Record<EvidenceState, { label: string; description: string }> = {
  source: { label: "Source-backed", description: "This connection is directly supported by a retained source record." },
  reviewed: { label: "Reviewed", description: "This connection passed the configured analyst review treatment in the fixture." },
  candidate: { label: "Needs review", description: "This candidate is unreviewed and cannot support a conclusion yet." },
  inferred: { label: "Context only", description: "This is curated explanatory context, not a measured sensitivity or causal conclusion." },
  unavailable: { label: "Unavailable", description: "This connection is not available in the active evidence view." }
};
