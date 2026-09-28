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

test("cancels the prior result request when URL-driven filters change", async () => {
  const signals: AbortSignal[] = [];
  vi.stubGlobal("fetch", vi.fn((_url: string, init?: RequestInit) => {
    signals.push(init?.signal as AbortSignal);
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ result_id: 11, query: "test", total_count: 1, filtered_total: 1, page: 1, page_size: 100, sort: "relevance", items: [] }),
    });
  }));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }],
  });
  await router.push("/literature-search/results/11?year=2024");
  await router.isReady();
  const Harness = defineComponent({ setup: () => ({ results: useLiteratureResults(11) }), template: "<div />" });
  mount(Harness, { global: { plugins: [router] } });
  await flushPromises();
  await router.replace("/literature-search/results/11?year=2023");
  await flushPromises();

  expect(signals).toHaveLength(2);
  expect(signals[0].aborted).toBe(true);
  expect(signals[1].aborted).toBe(false);
});

test("AC-FT-14 updates only the matching row without reloading or changing route state", async () => {
  const fetchMock = vi.fn(() => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => ({
      result_id: 11, query: "test", total_count: 2, filtered_total: 2, page: 2,
      page_size: 100, sort: "newest",
      items: ["1", "2"].map((pmid) => ({ item: { pmid }, sort_reason: "", state: null, library_item: null })),
    }),
  }));
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/11?page=2&sort=newest&year=2024");
  await router.isReady();
  const Harness = defineComponent({ setup: () => ({ results: useLiteratureResults(11) }), template: "<div />" });
  const wrapper = mount(Harness, { global: { plugins: [router] } });
  await flushPromises();
  const results = (wrapper.vm as unknown as { results: ReturnType<typeof useLiteratureResults> }).results;

  results.updateLibraryItem("1", { id: 9, pmid: "1", pmcid: null, doi: null, title: null, journal: null, year: null, document_id: 44, source_search_id: 11, fulltext_status: "local_pdf_available", fulltext_status_reason: "linked", created_at: "2026-08-26", updated_at: "2026-08-26" });

  expect(results.page.value?.items[0].library_item?.document_id).toBe(44);
  expect(results.page.value?.items[1].library_item).toBeNull();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(router.currentRoute.value.query).toMatchObject({ page: "2", sort: "newest", year: "2024" });
});
