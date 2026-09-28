import { afterEach, describe, expect, it, vi } from "vitest";

import { resourceLibraryApi } from "./resourceLibrary";

describe("resourceLibraryApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("serializes stable server-side filters before pagination", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, offset: 50, limit: 50 })));
    vi.stubGlobal("fetch", fetchMock);

    await resourceLibraryApi.items({
      query: "  ILD  ",
      sourceIds: [7, 9],
      nodeId: "tree:7:trials",
      fileTypes: ["pdf", "docx"],
      statuses: ["ai_available", "needs_attention"],
      updatedFrom: "2026-08-01",
      updatedTo: "2026-08-30",
      sortBy: "name",
      sortOrder: "asc",
    }, 50, 50);

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/api/v1/library/items?");
    expect(url).toContain("q=ILD");
    expect(url).toContain("source_id=7");
    expect(url).toContain("source_id=9");
    expect(url).toContain("tree_node_id=tree%3A7%3Atrials");
    expect(url).toContain("file_type=pdf");
    expect(url).toContain("health_status=needs_attention");
    expect(url).toContain("sort_by=name");
    expect(url).toContain("sort_order=asc");
    expect(url).toContain("offset=50");
    expect(url).toContain("limit=50");
  });

  it("records recent use only after an explicit open action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ document_id: 12, open_count: 2, last_opened_at: "2026-08-30T00:00:00Z", last_opened_by: null })));
    vi.stubGlobal("fetch", fetchMock);

    await resourceLibraryApi.markOpened(12, "resource-library-open-12");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/library/items/12/opened",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idempotency_key: "resource-library-open-12" }),
      }),
    );
  });
});
