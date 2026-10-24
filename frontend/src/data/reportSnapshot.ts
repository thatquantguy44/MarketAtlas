export type ProvenanceKind = "relationship" | "macro_context" | "rolling_correlation";

export interface ReportSnapshot {
  metadata: {
    snapshotId: string;
    publishedAt: string;
    knowledgeCutoff: string | null;
    fixtureOnly: true;
    counts: { nodes: number; relationships: number; contexts: number; paths: number; correlations: number; provenance: number };
  };
  nodes: Array<{ id: string; label: string; type: string }>;
  relationships: Array<{ id: string; source: string; target: string; edge: string; status: "accepted" | "disputed"; sourceRecord: string }>;
  contexts: Array<{ id: string; target: string; kind: string; basis: "source_backed" | "curated"; rationale: string; owner: string; label: string; sourceRecord: string }>;
  correlations: Array<{ id: string; endpoint: string; pair: string; correlation: number | null; pairedReturns: number; status: "supported" | "zero_variance" }>;
  provenance: Array<{ kind: ProvenanceKind; subjectId: string; source: string; method?: string; inputIdentity: string; note: string }>;
}

export const fixtureReportSnapshot: ReportSnapshot = {
  metadata: {
    snapshotId: "fixture-snapshot-0b918c49",
    publishedAt: "2026-10-24T16:00:00Z",
    knowledgeCutoff: null,
    fixtureOnly: true,
    counts: { nodes: 15, relationships: 14, contexts: 3, paths: 24, correlations: 32, provenance: 49 }
  },
  nodes: [
    { id: "I-A", label: "Synthetic Alpha Share", type: "instrument" },
    { id: "O-A", label: "Alpha Fictional Corp", type: "issuer" },
    { id: "S-TECH", label: "Synthetic Technology", type: "sector" },
    { id: "M-GROWTH", label: "Synthetic Growth Index", type: "macro series" },
    { id: "EC-GROWTH", label: "Growth", type: "economic concept" },
    { id: "C-US", label: "Synthetic US", type: "country" }
  ],
  relationships: [
    { id: "A4", source: "I-A", target: "O-A", edge: "issued_by", status: "accepted", sourceRecord: "synthetic-fixture:A4" },
    { id: "A6", source: "O-A", target: "S-TECH", edge: "classified_as", status: "accepted", sourceRecord: "synthetic-fixture:A6" },
    { id: "A11", source: "M-GROWTH", target: "EC-GROWTH", edge: "measures", status: "accepted", sourceRecord: "synthetic-fixture:A11" },
    { id: "A12", source: "M-GROWTH", target: "C-US", edge: "covers", status: "accepted", sourceRecord: "synthetic-fixture:A12" }
  ],
  contexts: [
    { id: "CTX1", target: "Synthetic US", kind: "series_country", basis: "source_backed", rationale: "Synthetic coverage mapping for the series.", owner: "synthetic-mapping-owner", label: "Context only — not measured sensitivity or causality", sourceRecord: "synthetic-fixture:CTX1" },
    { id: "CTX2", target: "Growth", kind: "series_concept", basis: "source_backed", rationale: "Synthetic measurement mapping for the series.", owner: "synthetic-mapping-owner", label: "Context only — not measured sensitivity or causality", sourceRecord: "synthetic-fixture:CTX2" },
    { id: "CTX3", target: "Synthetic Technology", kind: "market_context", basis: "curated", rationale: "Illustrative sector context chosen by the mapping owner.", owner: "synthetic-mapping-owner", label: "Context only — not measured sensitivity or causality", sourceRecord: "synthetic-fixture:CTX3" }
  ],
  correlations: [
    { id: "corr-1", endpoint: "2024-04-09", pair: "Synthetic Alpha / Synthetic Beta", correlation: 0.9912, pairedReturns: 55, status: "supported" },
    { id: "corr-2", endpoint: "2024-04-10", pair: "Synthetic Alpha / Synthetic Beta", correlation: 0.9931, pairedReturns: 55, status: "supported" },
    { id: "corr-3", endpoint: "2024-04-11", pair: "Synthetic Alpha / Synthetic Beta", correlation: 0.9927, pairedReturns: 55, status: "supported" },
    { id: "corr-4", endpoint: "2024-04-12", pair: "Synthetic Alpha / Synthetic Beta", correlation: 0.9950, pairedReturns: 55, status: "supported" },
    { id: "corr-5", endpoint: "2024-04-15", pair: "Synthetic Alpha / Synthetic Beta", correlation: 0.994545932823383, pairedReturns: 55, status: "supported" },
    { id: "corr-constant", endpoint: "2024-04-15", pair: "Synthetic Alpha / Synthetic Constant", correlation: null, pairedReturns: 59, status: "zero_variance" }
  ],
  provenance: [
    { kind: "relationship", subjectId: "A11", source: "synthetic-fixture:A11", inputIdentity: "fixture manifest 15e24…87da", note: "Series-to-concept sourced relationship" },
    { kind: "macro_context", subjectId: "CTX3", source: "synthetic-fixture:CTX3", inputIdentity: "fixture manifest 15e24…87da", note: "Curated sector context with a supporting assertion" },
    { kind: "rolling_correlation", subjectId: "corr-5", source: "synthetic-price-I-A / synthetic-price-I-B", method: "rolling-pearson-simple-return-v1", inputIdentity: "input-selection hash and published snapshot", note: "Fixed 60-session window; 55 paired returns" }
  ]
};
