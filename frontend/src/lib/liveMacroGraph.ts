export interface LiveGraphNode {
  id: string;
  node_type: "macro_series" | "economic_concept";
  display_label: string;
  temporal_status: "current_only";
  source_record: string;
  details: { canonical_key: string; temporal_status: "current_only" };
}

export interface LiveGraphEdge {
  id: string;
  edge_type: "measures";
  source_node_id: string;
  target_node_id: string;
  temporal_status: "current_only";
  source_record: string;
  provenance: Record<string, string>;
}

export interface LiveMacroGraph {
  publication: "macro_economic_graph";
  snapshot_id: string;
  published_at: string;
  input_manifest_id: string;
  nodes: LiveGraphNode[];
  edges: LiveGraphEdge[];
}

const graphUrl = "/api/v1/macro-economic-graph";

export async function loadLiveMacroGraph(signal?: AbortSignal): Promise<LiveMacroGraph> {
  const response = await fetch(graphUrl, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Live graph API returned ${response.status}`);
  return response.json() as Promise<LiveMacroGraph>;
}
