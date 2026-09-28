import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import ResultsView from "./ResultsView.vue";

afterEach(() => vi.restoreAllMocks());

test("AC-I12 exposes only all and reading-plan tabs with no duplicate or saved action", async () => {
  const fetchMock = vi.fn((input: string | URL) => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => String(input).endsWith("/literature-search/7")
      ? { id: 7, original_query: "研究主题" }
      : { result_id: 101, query: "test", total_count: 0, filtered_total: 0, page: 1, page_size: 100, sort: "relevance", items: [] },
  }));
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();

  expect(wrapper.text()).toContain("阅读计划");
  expect(wrapper.get(".result-view-tabs").text()).toContain("全部文献");
  expect(wrapper.get(".result-view-tabs").text()).not.toContain("已保存");
  expect(wrapper.text()).not.toContain("取消保存");
  expect(wrapper.get(".result-view-tabs").text()).not.toContain("重复文献");
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes("reading-order"))).toBe(false);
});

test("AC-02 to AC-04 use the final compact three-column replica structure without retired actions", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => String(input).endsWith("/literature-search/7")
      ? { id: 7, original_query: "Interstitial Lung Disease", model_version: "v3", searched_at: "2026-08-14T04:50:00Z", result_count: 500 }
      : { result_id: 101, query: "test", total_count: 12530, filtered_total: 126, page: 1, page_size: 100, sort: "relevance", facets: {}, items: [] },
  })));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();

  expect(wrapper.find(".results-replica").exists()).toBe(true);
  expect(wrapper.find(".replica-main").exists()).toBe(true);
  expect(wrapper.find(".filter-sidebar").exists()).toBe(true);
  expect(wrapper.text()).toContain("Interstitial Lung Disease");
  expect(wrapper.text()).toContain("PubMed 命中 12,530 篇");
  expect(wrapper.text()).not.toContain("LITERATURE RESULTS · LIVE");
  expect(wrapper.text()).not.toContain("加入知识库");
  expect(wrapper.text()).not.toContain("导入已下载 PDF");
});

test("visual rework gate exposes the compact two-line toolbar, active chips, and list density header", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => Promise.resolve({ ok: true, status: 200, json: async () => String(input).endsWith("/literature-search/7") ? { id: 7, original_query: "Interstitial Lung Disease", model_version: "v3", searched_at: "2026-08-14T04:50:00Z" } : { result_id: 101, query: "test", total_count: 12530, filtered_total: 126, page: 1, page_size: 20, sort: "relevance", facets: {}, sort_capabilities: { classic: { available: false, reason: "未生成" } }, items: [] } })));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7"); await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } }); await flushPromises();
  expect(wrapper.find(".result-context").exists()).toBe(true);
  expect(wrapper.find(".result-toolbar-chips").exists()).toBe(true);
  expect(wrapper.text()).toContain("近期热度");
  expect(wrapper.text()).toContain("经典度");
  expect(wrapper.text()).toContain("筛选后 126 篇");
  expect(wrapper.find(".more-actions").classes()).toContain("inline-more-actions");
});

test("AC-UI-REMOVE-01 removes the relevance and list-density controls from the results toolbar", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => String(input).endsWith("/literature-search/7")
      ? { id: 7, original_query: "研究主题" }
      : { result_id: 101, query: "test", total_count: 20, filtered_total: 20, page: 1, page_size: 20, sort: "relevance", facets: {}, items: [] },
  })));
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();

  const toolbar = wrapper.get(".sort");
  expect(toolbar.text()).not.toContain("相关性");
  expect(toolbar.text()).not.toContain("紧凑列表");
  expect(toolbar.text()).not.toContain("舒适列表");
  expect(toolbar.find('[aria-pressed]').exists()).toBe(false);
  expect(toolbar.text()).toContain("文章影响力");
  expect(toolbar.text()).toContain("经典度");
});

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
  expect(wrapper.text()).not.toContain("更多操作");
  expect(wrapper.text()).toContain("检查重复论文");
  expect(wrapper.find(".inline-more-actions").exists()).toBe(true);
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
  expect(wrapper.get(".results-navigation").text()).toContain("第 1 页，共 11 页");
});

test("creates a research context and score run when article-level sorting is requested", async () => {
  const fetchMock = vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes("/reading-order")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, order_source: "rule", generated_at: "2026-08-11T00:00:00Z", items: [] }) });
    if (url.includes("/scoring/status")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: "active", total: 1, completed: 1, active_generation_id: 1, building_generation_id: null, started_at: null, updated_at: null, algorithm_version: "v1", signals: {}, last_error: null, can_retry: false }) });
    if (url.endsWith("/research-contexts")) return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 99 }) });
    if (url.endsWith("/research-intents")) return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 88 }) });
    if (url.includes("/scoring/runs")) return Promise.resolve({ ok: true, status: 201, json: async () => ({ generation_id: 1, status: "active", algorithm_version: "v1", operation: "created" }) });
    if (url.endsWith("/literature-search/7")) return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 7, original_query: "研究主题", research_context_id: null }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ result_id: 101, query: "test", total_count: 1, filtered_total: 1, page: 1, page_size: 20, sort: "relevance", items: [] }) });
  });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search/results/:id", component: { template: "<div />" } }] });
  await router.push("/literature-search/results/101?task=7");
  await router.isReady();
  const wrapper = mount(ResultsView, { global: { plugins: [router] } });
  await flushPromises();
  await wrapper.get(".start-scoring").trigger("click");
  await flushPromises();
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/research-contexts"))).toBe(true);
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/scoring/runs"))).toBe(true);
});
