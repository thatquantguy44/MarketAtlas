import { describe, expect, it } from "vitest";
import { evidenceCopy, knowledgeEdges, knowledgeNodes, reviewCandidates } from "@/data/knowledgeGraph";

describe("knowledge graph fixture", () => {
  it("keeps source records, canonical entities, and candidate links distinct", () => {
    expect(knowledgeNodes.some((node) => node.kind === "Original record")).toBe(true);
    expect(knowledgeNodes.some((node) => node.kind === "Canonical instrument")).toBe(true);
    expect(knowledgeEdges.filter((edge) => edge.candidateId)).toHaveLength(1);
  });

  it("makes candidate treatment explicit before any review decision", () => {
    expect(reviewCandidates[0].reviewStatus).toBe("unreviewed");
    expect(evidenceCopy.candidate.description).toContain("cannot support a conclusion");
  });
});
