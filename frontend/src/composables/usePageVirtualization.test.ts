import { describe, expect, it } from "vitest";

import { calculatePageWindow } from "./usePageVirtualization";

describe("calculatePageWindow", () => {
  it("keeps the visible page and scroll-direction buffer while releasing remote pages", () => {
    const states = calculatePageWindow({
      pageCount: 10,
      visiblePages: [5],
      scrollDirection: "forward",
      pinnedPages: [1],
      bufferPages: 1,
    });

    expect(states[0]).toBe("parked");
    expect(states[3]).toBe("parked");
    expect(states[4]).toBe("rendered");
    expect(states[5]).toBe("parked");
    expect(states[7]).toBe("released");
  });

  it("never releases a pinned page even when it is far outside the window", () => {
    const states = calculatePageWindow({
      pageCount: 8,
      visiblePages: [2],
      scrollDirection: "backward",
      pinnedPages: [8],
      bufferPages: 1,
    });

    expect(states[7]).toBe("parked");
  });
});
