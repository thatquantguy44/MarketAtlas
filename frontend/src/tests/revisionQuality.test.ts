import { afterEach, describe, expect, it, vi } from "vitest";
import { formatQualityMetric, loadRevisionQuality, revisionQualityUrl } from "@/lib/revisionQuality";

afterEach(() => vi.unstubAllGlobals());

describe("revision quality context", () => {
  it("queries only one selected series", () => {
    expect(revisionQualityUrl("selected-id")).toBe("/api/v1/macro-revision-quality?series_node_id=selected-id");
  });
  it("keeps zero distinct from missing and preserves percentage units", () => {
    expect(formatQualityMetric(null)).toBe("Unknown");
    expect(formatQualityMetric(0)).toBe("0");
    expect(formatQualityMetric(0.4, true)).toBe("0.4%");
  });
  it("rejects a response for another selected series", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ series_node_id: "other-id" }) }));
    await expect(loadRevisionQuality("selected-id")).rejects.toThrow("different series");
  });
  it("makes unavailable quality recoverable without fabricating a summary", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(loadRevisionQuality("selected-id")).rejects.toThrow("503");
  });
});
