import { describe, expect, it, vi } from "vitest";

import { resourceLibraryApi } from "../api/resourceLibrary";
import { useResourceLibrary } from "./useResourceLibrary";

vi.mock("../api/resourceLibrary", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/resourceLibrary")>();
  return {
    ...actual,
    resourceLibraryApi: {
      ...actual.resourceLibraryApi,
      items: vi.fn(),
      facets: vi.fn(),
    },
  };
});

describe("useResourceLibrary", () => {
  it("discards a stale query response instead of replacing the newest results", async () => {
    let resolveFirst: ((value: { items: Array<{ id: number }>; total: number; offset: number; limit: number }) => void) | undefined;
    vi.mocked(resourceLibraryApi.items)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }) as never)
      .mockResolvedValueOnce({ items: [{ id: 2 }], total: 1, offset: 0, limit: 25 } as never);
    vi.mocked(resourceLibraryApi.facets).mockResolvedValue({ sources: [], source_types: [], file_types: [], statuses: [] });

    const library = useResourceLibrary();
    const first = library.loadPage({ query: "old" });
    const second = library.loadPage({ query: "new" });
    await second;
    resolveFirst?.({ items: [{ id: 1 }], total: 1, offset: 0, limit: 25 });
    await first;

    expect(library.items.value.map((item) => item.id)).toEqual([2]);
    expect(library.filters.query).toBe("new");
  });
});
