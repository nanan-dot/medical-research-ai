import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import ResultsIndexView from "./ResultsIndexView.vue";

describe("ResultsIndexView", () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  function createTestRouter() {
    return createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/literature-search/results", component: ResultsIndexView },
        { path: "/literature-search/results/:id", component: { template: "<div>result detail</div>" } },
        { path: "/literature-search/history", component: { template: "<div />" } },
        { path: "/literature-search", component: { template: "<div />" } },
      ],
    });
  }

  it("restores the latest server-backed result when the results entry is reopened", async () => {
    const fetchMock = vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        total: 2,
        offset: 0,
        limit: 100,
        items: [
          { id: 8, latest_result_id: null },
          { id: 7, latest_result_id: 101 },
        ],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    const router = createTestRouter();
    await router.push("/literature-search/results");
    await router.isReady();

    mount(ResultsIndexView, { global: { plugins: [router] } });
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/literature-search/history?offset=0&limit=100"), undefined);
    expect(router.currentRoute.value.path).toBe("/literature-search/results/101");
    expect(router.currentRoute.value.query).toEqual({ task: "7", from: "history" });
  });

  it("AC-NAV-14 exposes recovery routes only when the server has no saved result", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ total: 0, offset: 0, limit: 100, items: [] }),
    })));
    const router = createTestRouter();
    await router.push("/literature-search/results");
    await router.isReady();

    const wrapper = mount(ResultsIndexView, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.get("h1").text()).toBe("检索结果");
    expect(wrapper.text()).toContain("尚未找到可恢复的检索结果");
    expect(wrapper.text()).not.toMatch(/results\/\d+/);
    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual([
      "/literature-search/history",
      "/literature-search",
    ]);
  });
});
