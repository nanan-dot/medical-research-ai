import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import ResultsView from "./ResultsView.vue";

afterEach(() => vi.restoreAllMocks());

test("does not render a duplicate return-to-history button", async () => {
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
  await router.push("/literature-search/results/101?task=7&from=history");
  await router.isReady();

  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();

  expect(wrapper.find('button[aria-label="返回检索历史"]').exists()).toBe(false);
  expect(wrapper.find(".utility-disclosure").exists()).toBe(false);
  expect(wrapper.text()).not.toContain("重复项检查");
});

test("places stateful processing entries above the result list when results exist", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes("/reading-order")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, order_source: "rule", generated_at: "2026-08-11T00:00:00Z", items: [] }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, query: "test", total_count: 1, filtered_total: 1, page: 1, page_size: 100, sort: "relevance", items: [] }) });
  }));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();
  expect(wrapper.text()).toContain("更多操作");
  expect(wrapper.text()).toContain("检查重复论文");
  expect(wrapper.text()).toContain("尚未检查重复论文");
  expect(wrapper.find(".processing-toolbar").exists()).toBe(false);
  expect(wrapper.find(".sort-explanation").exists()).toBe(false);
  expect(wrapper.find(".research-tools").exists()).toBe(false);
  expect(wrapper.find(".utility-disclosure").exists()).toBe(false);
});

test("uses an independent results-list scrollbar in the embedded workspace", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes("/reading-order")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, order_source: "rule", generated_at: "2026-08-11T00:00:00Z", items: [] }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, query: "test", total_count: 1, filtered_total: 1, page: 1, page_size: 20, sort: "relevance", items: [] }) });
  }));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }],
  });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { props: { resultId: 101, embedded: true }, global: { plugins: [router] } });
  await flushPromises();
  expect(wrapper.classes()).toContain("embedded");
  expect(wrapper.find(".results-workspace").exists()).toBe(true);
});

test("keeps the compact research context and result pagination inside the embedded workspace", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes("/reading-order")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, order_source: "rule", generated_at: "2026-08-11T00:00:00Z", items: [] }) });
    if (url.endsWith("/literature-search/7")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 7, original_query: "研究主题" }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, query: "test", total_count: 101, filtered_total: 101, page: 1, page_size: 100, sort: "relevance", items: [] }) });
  }));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { props: { resultId: 101, embedded: true }, global: { plugins: [router] } });
  await flushPromises();
  expect(wrapper.get(".research-brief").text()).toContain("研究主题");
  expect(wrapper.get(".research-brief").text()).not.toContain("第 1 页，共 2 页");
  expect(wrapper.get(".results-navigation").text()).toContain("第 1 页，共 2 页");
});
