import { describe, expect, it } from "vitest";

import type { ContentSegment } from "../api/writingProjects";
import { reconcileDraftSegments } from "./writingSegments";

const segment = (id: string, text: string): ContentSegment => ({
  id,
  text,
  origin: "user_provided",
  citation_ids: [],
  pending_item_id: null,
});

describe("reconcileDraftSegments", () => {
  it("keeps a paragraph id when a new paragraph is inserted before it", () => {
    const previous = [segment("segment-a", "First claim"), segment("segment-b", "Second claim")];

    const reconciled = reconcileDraftSegments(previous, "New introduction\n\nFirst claim\n\nSecond claim");

    expect(reconciled.map((item) => item.id)).toEqual([
      expect.stringMatching(/^segment-/),
      "segment-a",
      "segment-b",
    ]);
  });
});
