import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_PAPER_FILTERS, paperLibraryApi } from "./paperLibrary";

describe("paperLibraryApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("serializes every multi-select facet as repeated query parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, offset: 20, limit: 20 })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await paperLibraryApi.items(
      {
        ...DEFAULT_PAPER_FILTERS,
        view: "reading",
        query: "  kidney  ",
        readingStatus: ["reading", "read"],
        analysisStatus: ["analyzing", "completed"],
        paperTypes: ["RCT", "Guideline"],
        researchRoles: ["core_evidence", "method_reference"],
        researchIds: [3, 8],
        tags: ["CKD", "SGLT2"],
        sort: "year",
      },
      20,
      20,
    );

    const url = new URL(String(fetchMock.mock.calls[0][0]), "http://local.test");
    expect(url.pathname).toBe("/api/v1/paper-library/items");
    expect(url.searchParams.get("query")).toBe("kidney");
    expect(url.searchParams.getAll("reading_status")).toEqual(["reading", "read"]);
    expect(url.searchParams.getAll("analysis_status")).toEqual(["analyzing", "completed"]);
    expect(url.searchParams.getAll("paper_type")).toEqual(["RCT", "Guideline"]);
    expect(url.searchParams.getAll("research_role")).toEqual(["core_evidence", "method_reference"]);
    expect(url.searchParams.getAll("research_id")).toEqual(["3", "8"]);
    expect(url.searchParams.getAll("tag")).toEqual(["CKD", "SGLT2"]);
    expect(url.searchParams.get("sort")).toBe("year");
  });

  it("uses the overview and optimistic relation endpoints without client-side substitutes", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 9, relations: [], activities: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ research_context_id: 4, version: 2 })))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await paperLibraryApi.overview(9);
    await paperLibraryApi.upsertRelation(9, 4, {
      role: "core_evidence",
      note: "关键结局",
      expected_version: 1,
    });
    await paperLibraryApi.deleteRelation(9, 4, 2);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/paper-library/items/9/overview");
    expect(fetchMock.mock.calls[1]).toEqual([
      "/api/v1/paper-library/items/9/research-relations/4",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ role: "core_evidence", note: "关键结局", expected_version: 1 }) }),
    ]);
    expect(fetchMock.mock.calls[2][0]).toBe(
      "/api/v1/paper-library/items/9/research-relations/4?expected_version=2",
    );
  });
});
