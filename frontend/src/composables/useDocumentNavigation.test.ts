import { nextTick } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDocumentNavigation } from "./useDocumentNavigation";

afterEach(() => vi.unstubAllGlobals());

describe("useDocumentNavigation", () => {
  it("keeps the newest response when requests race", async () => {
    let resolveFirst!: (value: Response) => void;
    const first = new Promise<Response>((resolve) => { resolveFirst = resolve; });
    const fetchMock = vi.fn().mockReturnValueOnce(first).mockResolvedValueOnce(new Response(JSON.stringify({ query: "new", knowledge_source_id: null, indexed_only: true, searchable_document_count: 1, results: [] })));
    vi.stubGlobal("fetch", fetchMock);
    const navigation = useDocumentNavigation();
    const oldSearch = navigation.search("old", null, true);
    await navigation.search("new", null, true);
    resolveFirst(new Response(JSON.stringify({ query: "old", knowledge_source_id: null, indexed_only: true, searchable_document_count: 1, results: [] })));
    await oldSearch; await nextTick();
    expect(navigation.result.value?.query).toBe("new");
  });

  it("reports API failures and can retry", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "服务暂不可用" } }), { status: 503 })).mockResolvedValueOnce(new Response(JSON.stringify({ query: "PD-1", knowledge_source_id: null, indexed_only: true, searchable_document_count: 0, results: [] })));
    vi.stubGlobal("fetch", fetchMock);
    const navigation = useDocumentNavigation();
    await navigation.search("PD-1", null, true);
    expect(navigation.error.value).toBe("服务暂不可用");
    await navigation.retry();
    expect(navigation.result.value?.results).toEqual([]);
  });
});
