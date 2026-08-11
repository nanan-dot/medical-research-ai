import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter, createWebHistory } from "vue-router";

import LiteratureSearchView from "./LiteratureSearchView.vue";

afterEach(() => vi.restoreAllMocks());

// 完整解析/扩展/构建/执行检索的响应链，供"执行检索"测试复用。
function stubSearchChain(router: ReturnType<typeof createRouter>) {
  const fetchMock = vi
    .fn()
    // 1. 文献检索二级导航读取最近结果（空列表表示不展示伪造结果入口）
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, offset: 0, limit: 50 }),
    })
    // 2. parse-query
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        raw_topic: "胃癌 EGFR 免疫治疗",
        candidate_source: "model_candidate",
        prompt_version: "search-intent-v1",
        clarification_questions: [],
        candidate: {
          topic: "胃癌 EGFR 免疫治疗", disease: "胃癌", intervention: "免疫治疗", target: "EGFR", mechanism: null,
          date_range: null, study_types: [], language: [], exclusions: [], retmax: 20,
        },
      }),
    })
    // 3. expand-terms
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        term_groups: [{ name: "disease", core_term: "胃癌", terms: ["stomach neoplasms"], field_tag: "Title/Abstract", source: "curated_local_mapping" }],
        mesh_candidates: [],
        warnings: [],
        user_edits: {},
      }),
    })
    // 4. build-query
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        boolean_query: '"stomach neoplasms"[Title/Abstract]',
        field_tags: { disease: "Title/Abstract" },
        explanations: ["概念组以 AND 连接"],
        user_edits: {},
      }),
    })
    // 5. create-task（POST /literature-search）
    .mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        id: 7,
        original_query: "胃癌 EGFR 免疫治疗",
        structured_query: "",
        search_string: '"stomach neoplasms"[Title/Abstract]',
        database: "pubmed",
        result_count: 42,
        retmax: 20,
        filters: "{}",
        model_version: "search-intent-v1",
        user_edits: "{}",
        status: "succeeded",
        error_message: null,
        created_at: "2026-08-07T00:00:00Z",
        searched_at: "2026-08-07T00:00:01Z",
        latest_result_id: 201,
        versions: [{ version: 1, result_id: 201, searched_at: "2026-08-07T00:00:01Z", result_count: 42, change: null }],
      }),
    });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

test("shows workspace title, tabs, and empty strategy state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [], total: 0 }) }),
  );
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/literature-search", component: { template: "<div>ls</div>" } }],
  });
  router.push("/literature-search");
  await router.isReady();
  const wrapper = mount(LiteratureSearchView, { global: { plugins: [router] } });
  expect(wrapper.text()).toContain("文献检索");
  expect(wrapper.text()).toContain("检索中心");
  expect(wrapper.text()).toContain("结果展示");
  expect(wrapper.text()).toContain("历史记录");
  expect(wrapper.text()).toContain("推荐阅读");
  const resultTab = wrapper.get('button[role="tab"]:nth-child(2)');
  expect(resultTab.attributes("aria-disabled")).toBeUndefined();
  // 桌面工作区将 PICO 与连续策略面板作为同级区域，避免 PICO 占满一整行。
  const workspace = wrapper.get(".search-workspace");
  expect(workspace.findAll(":scope > section")).toHaveLength(3);
  expect(workspace.find(".strategy-builder").exists()).toBe(true);
  expect(workspace.find(".workspace-execution .source-panel").exists()).toBe(true);
  expect(workspace.find(".workspace-execution .readiness-panel").exists()).toBe(true);
  expect(workspace.get("#research-topic").element.compareDocumentPosition(
    workspace.get(".pico-fields").element,
  ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(workspace.get(".topic-section button").text()).toContain("解析研究问题");
  expect(workspace.text()).toContain("解析后的 PICO 条件");
  // 双列工作区保留每个 PICO 字段的可访问标签，检索式为空时不伪造布尔表达式。
  expect(workspace.get("textarea[aria-describedby='query-editor-note']").attributes("placeholder")).toContain("解析研究问题");
  expect(workspace.findAll(".pico-field input")).toHaveLength(4);
  expect(workspace.text()).toContain("本次检索仅提交至 PubMed");
  expect(workspace.text()).toContain("术语依据");
  expect(workspace.text()).toContain("不限发表语言");
  await resultTab.trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("尚无可用的真实检索结果");
});

test("restores the history workspace tab from the URL", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [], total: 0, offset: 0, limit: 50 }) }),
  );
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/literature-search", component: { template: "<div>ls</div>" } }],
  });
  await router.push("/literature-search?tab=history");
  await router.isReady();

  const wrapper = mount(LiteratureSearchView, { global: { plugins: [router] } });
  await flushPromises();

  expect(wrapper.get('button[role="tab"][aria-selected="true"]').text()).toContain("历史记录");
  expect(router.currentRoute.value.query.tab).toBe("history");
});

test("parses topic, fills PICO, builds query, and runs a real search task", async () => {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/literature-search", component: { template: "<div>search</div>" } },
      { path: "/literature-search/results/:id", component: { template: "<div>results</div>" } },
    ],
  });
  router.push("/literature-search");
  await router.isReady();

  const fetchMock = stubSearchChain(router);
  const wrapper = mount(LiteratureSearchView, { global: { plugins: [router] } });

  // 第一步：输入研究问题并生成检索式（parse-query → expand-terms → build-query 自动链）
  const topicInput = wrapper.get("#research-topic");
  await topicInput.setValue("胃癌 EGFR 免疫治疗");
  await flushPromises();
  // jsdom 中点击 submit 按钮不触发 form submit，直接提交 form（等价于浏览器行为）。
  await wrapper.find("form").trigger("submit");
  await flushPromises();

  // 真实候选回填 PICO：人群=胃癌（来自后端 candidate.disease）
  const picoInputs = wrapper.findAll(".pico-field input");
  expect(picoInputs.length).toBe(4);
  expect((picoInputs[0].element as HTMLInputElement).value).toContain("胃癌");

  // 检索式草案展示真实 build-query 结果，并允许用户在执行前编辑。
  expect((wrapper.get("#search-query-draft").element as HTMLTextAreaElement).value).toContain('"stomach neoplasms"[Title/Abstract]');
  expect(wrapper.text()).toContain("胃癌");
  expect(wrapper.text()).toContain("stomach neoplasms");

  await wrapper.get('select[aria-label="文献发表语言"]').setValue("chinese");

  // 第二步：开始检索 → POST /literature-search → 跳转结果页
  const searchButton = wrapper.findAll("button").find((b) => b.text().includes("开始检索"));
  expect(searchButton).toBeTruthy();
  await searchButton!.trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/literature-search",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('AND chinese[la]'),
    }),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/literature-search/201/results?sort=relevance&page=1&page_size=20",
    undefined,
  );
  // 成功后保留文件 3 的固定标题与页签，仅在下方切换至内嵌结果内容。
  expect(wrapper.text()).toContain("文献检索");
  expect(wrapper.text()).toContain("检索中心");
  expect(wrapper.text()).toContain("结果展示");
});

test("rejects empty topic without calling the API", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/literature-search", component: { template: "<div>ls</div>" } }],
  });
  router.push("/literature-search");
  await router.isReady();
  const wrapper = mount(LiteratureSearchView, { global: { plugins: [router] } });
  const generateButton = wrapper.findAll("button").find((b) => b.text().includes("解析研究问题"));
  expect((generateButton!.element as HTMLButtonElement).disabled).toBe(true);
  await wrapper.find("form").trigger("submit");
  // 初始挂载会读取一次历史任务以确定“结果展示”的真实目标；空输入不会产生检索请求。
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/literature-search?offset=0&limit=50", undefined);
});
