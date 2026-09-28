import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import NoteLibraryWorkspace from "./NoteLibraryWorkspace.vue";

describe("NoteLibraryWorkspace", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("AC-NLF-02 renders a three-column reading workspace without a duplicate application sidebar", async () => {
    const fetchMock = vi.fn((path: string) => {
      const payload = path.includes("facets")
        ? { tags: [], research_contexts: [], quick_counts: { all: 0, recent: 0, favorite: 0, unlinked_research: 0, archived: 0 } }
        : { items: [], total: 0, all_total: 0, page: 1, page_size: 20, query_fingerprint: "x", as_of: "2026-01-01T00:00:00Z" };
      return Promise.resolve(new Response(JSON.stringify(payload)));
    });
    vi.stubGlobal("fetch", fetchMock);
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/notes", component: NoteLibraryWorkspace }] });
    await router.push("/notes");
    await router.isReady();
    const wrapper = mount(NoteLibraryWorkspace, { global: { plugins: [router] } });
    expect(wrapper.get("[data-testid='note-workspace']").classes()).toContain("note-workspace");
    expect(wrapper.find("[data-testid='note-navigation']").exists()).toBe(true);
    expect(wrapper.find("[data-testid='note-list']").exists()).toBe(true);
    expect(wrapper.find("[data-testid='note-preview']").exists()).toBe(true);
    expect(wrapper.findAll(".sidebar")).toHaveLength(0);
  });

  it("AC-NLF-17 keeps a failed list request recoverable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("离线")));
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/notes", component: NoteLibraryWorkspace }] });
    await router.push("/notes"); await router.isReady();
    const wrapper = mount(NoteLibraryWorkspace, { global: { plugins: [router] } });
    await flushPromises();
    expect(wrapper.get("[role='alert']").text()).toContain("离线");
    expect(wrapper.get("[role='alert'] button").text()).toBe("重试");
  });
});
