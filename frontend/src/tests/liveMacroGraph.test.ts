import { describe, expect, it } from "vitest";
import { LIVE_GRAPH_VISUAL_PAGE_SIZE, liveGraphUrl } from "@/lib/liveMacroGraph";

describe("live macro graph requests", () => {
  it("keeps the catalog request compact until a category is selected", () => {
    expect(liveGraphUrl()).toBe("/api/v1/macro-economic-graph");
  });

  it("encodes a bounded category neighborhood", () => {
    expect(liveGraphUrl({ conceptId: "concept-id", query: "oregon", limit: 50, offset: 50 }))
      .toBe("/api/v1/macro-economic-graph?concept_id=concept-id&q=oregon&limit=50&offset=50");
  });

  it("keeps the interactive graph page small enough to remain legible", () => {
    expect(LIVE_GRAPH_VISUAL_PAGE_SIZE).toBe(12);
  });
});
