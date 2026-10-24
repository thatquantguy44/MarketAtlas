import { describe, expect, it } from "vitest";
import { fixtureReportSnapshot } from "@/data/reportSnapshot";

describe("fixture report snapshot", () => {
  it("keeps snapshot counts and provenance visible for the demo", () => {
    expect(fixtureReportSnapshot.metadata.fixtureOnly).toBe(true);
    expect(fixtureReportSnapshot.metadata.counts.correlations).toBe(32);
    expect(fixtureReportSnapshot.provenance).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: "relationship" }),
        expect.objectContaining({ kind: "macro_context" }),
        expect.objectContaining({ kind: "rolling_correlation" })
      ])
    );
  });

  it("labels all macro contexts as non-causal context", () => {
    expect(fixtureReportSnapshot.contexts.every((context) => context.label.includes("not measured sensitivity or causality"))).toBe(true);
  });
});
