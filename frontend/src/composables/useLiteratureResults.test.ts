import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { useLiteratureResults } from "./useLiteratureResults";

afterEach(() => vi.restoreAllMocks());

test("keeps route context such as tab=results while synchronizing pagination", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => ({ result_id: 11, query: "test", total_count: 500, filtered_total: 500, page: 1, page_size: 100, sort: "relevance", items: [] }),
  })));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }],
  });
  await router.push("/literature-search/results/11?tab=results&task=7");
  await router.isReady();

  const Harness = defineComponent({
    setup: () => ({ results: useLiteratureResults(11) }),
    template: "<div />",
  });
  const wrapper = mount(Harness, { global: { plugins: [router] } });
  await flushPromises();
  (wrapper.vm as unknown as { results: { goToPage: (page: number) => void } }).results.goToPage(2);
  await flushPromises();

  expect(router.currentRoute.value.query).toMatchObject({ tab: "results", task: "7", page: "2" });
});
