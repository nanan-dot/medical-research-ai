import { describe, expect, it, vi } from "vitest";
import { knowledgeSourcesApi } from "../api/knowledgeSources";
import { useKnowledgeSources } from "./useKnowledgeSources";

vi.mock("../api/knowledgeSources", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/knowledgeSources")>();
  return { ...actual, knowledgeSourcesApi: { ...actual.knowledgeSourcesApi, page: vi.fn(), summary: vi.fn() } };
});

describe("useKnowledgeSources", () => {
  it("ignores an obsolete response that resolves after a newer query", async () => {
    let resolveFirst: ((value: { items: []; total: number; offset: number; limit: number }) => void) | undefined;
    const page = vi.mocked(knowledgeSourcesApi.page);
    page.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }));
    page.mockResolvedValueOnce({ items: [], total: 2, offset: 0, limit: 10 });
    vi.mocked(knowledgeSourcesApi.summary).mockResolvedValue({ source_count: 0, local_folder_count: 0, obsidian_count: 0, total_item_count: 0, available_item_count: 0, processing_item_count: 0, needs_attention_count: 0, affected_source_count: 0, availability_percent: null, issue_breakdown: { parse_failed: 0, unsupported_format: 0, unavailable_file: 0, index_failed: 0, other: 0 } });
    const state = useKnowledgeSources();
    const first = state.load({ q: "old", sortBy: "name", sortOrder: "desc", offset: 0, limit: 10 });
    await state.load({ q: "new", sortBy: "name", sortOrder: "desc", offset: 0, limit: 10 });
    resolveFirst?.({ items: [], total: 1, offset: 0, limit: 10 });
    await first;
    expect(state.total.value).toBe(2);
  });
});
