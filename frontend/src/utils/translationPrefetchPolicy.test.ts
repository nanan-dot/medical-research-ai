import { describe, expect, it } from "vitest";

import { rankTranslationCandidates, shouldPrefetch } from "./translationPrefetchPolicy";

describe("translation prefetch policy", () => {
  it("orders active before adjacent and far work, deduplicates, and bounds the queue", () => {
    expect(rankTranslationCandidates([
      { segmentId: 4, priority: "prefetch", distance: 4 },
      { segmentId: 2, priority: "adjacent", distance: 1 },
      { segmentId: 1, priority: "active", distance: 0 },
      { segmentId: 1, priority: "prefetch", distance: 3 },
      { segmentId: 3, priority: "adjacent", distance: 2 },
    ], 3).map(item => item.segmentId)).toEqual([1, 2, 3]);
  });

  it("stops speculative work when following is off or the environment is constrained", () => {
    const normal = { followEnabled: true, isBackground: false, saveData: false, effectiveType: "4g" };
    expect(shouldPrefetch(normal)).toBe(true);
    expect(shouldPrefetch({ ...normal, followEnabled: false })).toBe(false);
    expect(shouldPrefetch({ ...normal, isBackground: true })).toBe(false);
    expect(shouldPrefetch({ ...normal, saveData: true })).toBe(false);
    expect(shouldPrefetch({ ...normal, effectiveType: "2g" })).toBe(false);
  });
});
