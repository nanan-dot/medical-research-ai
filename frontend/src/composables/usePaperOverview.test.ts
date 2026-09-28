import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { paperLibraryApi } from "../api/paperLibrary";
import { usePaperOverview } from "./usePaperOverview";

describe("usePaperOverview", () => {
  it("keeps the newest selection when an older overview responds last", async () => {
    let resolveFirst: ((value: unknown) => void) | undefined;
    vi.spyOn(paperLibraryApi, "overview")
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }) as never)
      .mockResolvedValueOnce({ id: 2, title: "第二篇", relations: [], activities: [] } as never);
    const overview = usePaperOverview();

    void overview.load(1);
    await overview.load(2);
    resolveFirst?.({ id: 1, title: "第一篇", relations: [], activities: [] });
    await flushPromises();

    expect(overview.paper.value?.id).toBe(2);
    overview.cancel();
  });
});
