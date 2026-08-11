import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import ResultsView from "./ResultsView.vue";

afterEach(() => vi.restoreAllMocks());

test("returns to the history workspace tab through the explicit result-page entry", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes("/reading-order")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ result_id: 101, order_source: "rule", generated_at: "2026-08-11T00:00:00Z", items: [] }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ result_id: 101, query: "test", total_count: 0, filtered_total: 0, page: 1, page_size: 20, sort: "relevance", items: [] }),
    });
  }));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/literature-search", component: { template: "<div>workspace</div>" } },
      { path: "/literature-search/results/:id", component: { template: "<div>result</div>" } },
    ],
  });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();

  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();

  const returnButton = wrapper.get('button[aria-label="返回检索历史"]');
  expect(returnButton.text()).toContain("返回历史记录");
  await returnButton.trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.fullPath).toBe("/literature-search?tab=history");
});
