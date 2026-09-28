import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_NOTE_FILTERS, noteLibraryApi } from "./noteLibrary";

describe("noteLibraryApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("AC-NLF-03/05/06 serializes real list filters and page state", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, all_total: 0, page: 2, page_size: 50 })));
    vi.stubGlobal("fetch", fetchMock);

    await noteLibraryApi.list({ ...DEFAULT_NOTE_FILTERS, view: "favorite", query: " CKD ", tags: ["机制", "RCT"], researchContextIds: [2, 6], page: 2, pageSize: 50 });

    const url = new URL(String(fetchMock.mock.calls[0][0]), "http://local.test");
    expect(url.pathname).toBe("/api/v1/note-library/notes");
    expect(url.searchParams.get("actor_scope")).toBe("local");
    expect(url.searchParams.get("view")).toBe("favorite");
    expect(url.searchParams.get("query")).toBe("CKD");
    expect(url.searchParams.getAll("tags")).toEqual(["机制", "RCT"]);
    expect(url.searchParams.getAll("research_context_ids")).toEqual(["2", "6"]);
    expect(url.searchParams.get("page_size")).toBe("50");
  });

  it("AC-NLF-11/12/13 keeps expected versions and one idempotency key at the API boundary", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ note_id: 1, draft_version: 2, base_revision: 1, title: "x", body: "y", sources: [], save_state: "saved", updated_at: "2026-01-01T00:00:00Z" }))));
    vi.stubGlobal("fetch", fetchMock);

    await noteLibraryApi.saveDraft(1, { expectedDraftVersion: 1, title: "x", body: "y", sources: [] });
    await noteLibraryApi.commit(1, { expectedBaseRevision: 1, expectedDraftVersion: 2, idempotencyKey: "stable-key" });

    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: "PUT", body: JSON.stringify({ actor_scope: "local", expected_draft_version: 1, title: "x", body: "y", sources: [] }) }));
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST", body: JSON.stringify({ actor_scope: "local", expected_base_revision: 1, expected_draft_version: 2, idempotency_key: "stable-key" }) }));
  });

  it("AC-NLF-09/14/16 uses CAS metadata, paginated history, restore, and archive lifecycle endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, page: 2, page_size: 20 }))));
    vi.stubGlobal("fetch", fetchMock);
    await noteLibraryApi.metadata(7, 3, { tags: ["机制"], research_context_ids: [9] });
    await noteLibraryApi.history(7, 2);
    await noteLibraryApi.restore(7, 1, 4, "restore-key");
    await noteLibraryApi.archive(7, true);
    expect(fetchMock.mock.calls[0]).toEqual(["/api/v1/note-library/notes/7/metadata", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ actor_scope: "local", expected_metadata_version: 3, tags: ["机制"], research_context_ids: [9] }) })]);
    expect(fetchMock.mock.calls[1][0]).toContain("page=2&page_size=20");
    expect(fetchMock.mock.calls[2][1]).toEqual(expect.objectContaining({ body: JSON.stringify({ actor_scope: "local", revision_no: 1, expected_base_revision: 4, idempotency_key: "restore-key" }) }));
    expect(fetchMock.mock.calls[3][0]).toBe("/api/v1/note-library/notes/7/archive");
  });
});
