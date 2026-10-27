export interface LiveGraphNode {
  id: string;
  node_type: "macro_series" | "economic_concept" | "catalog_source";
  display_label: string;
  temporal_status: "current_only";
  source_record: string;
  details: { canonical_key: string; temporal_status: "current_only"; frequency?: string; series_count?: number };
}

export interface LiveGraphEdge {
  id: string;
  edge_type: "measures" | "contains";
  source_node_id: string;
  target_node_id: string;
  temporal_status: "current_only";
  source_record: string;
  provenance: Record<string, string | number>;
  aggregate?: boolean;
  series_count?: number;
}

export interface LiveMacroGraph {
  publication: "macro_economic_graph";
  snapshot_id: string;
  published_at: string;
  input_manifest_id: string;
  view: "catalog_summary" | "concept_neighborhood";
  facets: {
    series_count: number;
    concept_count: number;
    frequency: Array<{ frequency: string; series_count: number }>;
  };
  pagination: { limit: number; offset: number; total: number };
  nodes: LiveGraphNode[];
  edges: LiveGraphEdge[];
}

const graphUrl = "/api/v1/macro-economic-graph";

// The report API is validated at a larger bounded page size. The interactive
// canvas intentionally requests fewer nodes so a category remains readable.
export const LIVE_GRAPH_VISUAL_PAGE_SIZE = 12;

export interface LiveGraphRequest {
  conceptId?: string | null;
  query?: string;
  limit?: number;
  offset?: number;
}

export function liveGraphUrl(request: LiveGraphRequest = {}) {
  const params = new URLSearchParams();
  if (request.conceptId) params.set("concept_id", request.conceptId);
  if (request.query?.trim()) params.set("q", request.query.trim());
  if (request.limit) params.set("limit", String(request.limit));
  if (request.offset) params.set("offset", String(request.offset));
  const suffix = params.toString();
  return suffix ? `${graphUrl}?${suffix}` : graphUrl;
}

export async function loadLiveMacroGraph(request: LiveGraphRequest = {}, signal?: AbortSignal): Promise<LiveMacroGraph> {
  const response = await fetch(liveGraphUrl(request), { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Live graph API returned ${response.status}`);
  return response.json() as Promise<LiveMacroGraph>;
}
