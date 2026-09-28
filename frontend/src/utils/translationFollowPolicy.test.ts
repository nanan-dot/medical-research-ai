import { describe, expect, it } from "vitest";

import { createTranslationFollowPolicy } from "./translationFollowPolicy";

describe("translation follow policy", () => {
  it("switches only after the candidate remains active for the dwell threshold", () => {
    const policy = createTranslationFollowPolicy({ dwellMs: 300 });
    expect(policy.observe({ segmentId: 10, now: 0 })).toBeNull();
    expect(policy.observe({ segmentId: 10, now: 299 })).toBeNull();
    expect(policy.observe({ segmentId: 10, now: 300 })).toBe(10);
  });

  it("gives explicit selection, editing, and pinning precedence over following", () => {
    const policy = createTranslationFollowPolicy({ dwellMs: 100 });
    policy.observe({ segmentId: 1, now: 0 });
    expect(policy.observe({ segmentId: 1, now: 100 })).toBe(1);
    expect(policy.observe({ segmentId: 2, now: 300, hasSelection: true })).toBe(1);
    expect(policy.observe({ segmentId: 2, now: 500, isEditing: true })).toBe(1);
    expect(policy.observe({ segmentId: 2, now: 700, pinnedSegmentId: 1 })).toBe(1);
  });

  it("invalidates candidates and current results when the document generation changes", () => {
    const policy = createTranslationFollowPolicy({ dwellMs: 100 });
    policy.setGeneration("doc:1:anchor:2:segments:3:zoom:4");
    policy.observe({ segmentId: 1, now: 0 });
    expect(policy.observe({ segmentId: 1, now: 100 })).toBe(1);
    policy.setGeneration("doc:2:anchor:8:segments:9:zoom:1");
    expect(policy.current()).toBeNull();
    expect(policy.observe({ segmentId: 2, now: 200 })).toBeNull();
  });
});
