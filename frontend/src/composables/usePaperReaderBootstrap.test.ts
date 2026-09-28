import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { paperReaderApi } from "../api/paperReader";
import { usePaperReaderBootstrap } from "./usePaperReaderBootstrap";

describe("usePaperReaderBootstrap", () => {
  it("keeps only the newest paper bootstrap after a rapid route change", async () => {
    const itemId = ref(1);
    const oldResult = new Promise<never>(() => undefined);
    vi.spyOn(paperReaderApi, "bootstrap").mockImplementation((id) => id === 1 ? oldResult : Promise.resolve({ paper: { paper_item_id: 2 }, document: { file_hash: "f", page_count: 1, content_url: "" }, resume: { session_id: 9, page: 1, viewport_offset_ratio: 0 } } as never));
    const state = usePaperReaderBootstrap(itemId);
    itemId.value = 2;
    await Promise.resolve(); await Promise.resolve();
    expect(state.bootstrap.value?.paper.paper_item_id).toBe(2);
  });
});
