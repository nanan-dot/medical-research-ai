import { shallowRef } from "vue";
import { expect, it, vi } from "vitest";
import type { ReadingSegment } from "../types/readingContext";

const readPage = vi.hoisted(() => vi.fn());
vi.mock("../api/readingSegments", () => ({ readPageSegments: readPage }));
import { useVisibleSegments } from "./useVisibleSegments";

it("aborts old page requests and never publishes their late reading context", async () => {
  let finish!: (items: ReadingSegment[]) => void;
  readPage.mockImplementationOnce(() => new Promise<ReadingSegment[]>(resolve => { finish = resolve; }));
  const publish = vi.fn();
  const root = document.createElement("div");
  const observer = useVisibleSegments({ root: shallowRef(root), mappings: () => [], publish });
  const request = observer.loadPage(1, { expected_file_hash: "a".repeat(64), expected_anchor_revision_id: 1, expected_segmentation_revision_id: 1 }, 1);
  const signal = readPage.mock.calls[0]![3] as AbortSignal;
  observer.clear(); finish([]); await request;
  expect(signal.aborted).toBe(true);
  expect(observer.context.value).toBeNull();
  expect(publish.mock.calls).toEqual([[null]]);
});
