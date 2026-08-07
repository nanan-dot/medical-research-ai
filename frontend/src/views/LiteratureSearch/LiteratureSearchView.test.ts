import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";

import LiteratureSearchView from "./LiteratureSearchView.vue";

afterEach(() => vi.restoreAllMocks());

// 完整解析/扩展/构建/执行检索的响应链，供“执行检索”测试复用。
function stubSearchChain(router: ReturnType<typeof createRouter>) {
  const fetchMock = vi
    .fn()
    // 1. parse-query
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
    // 2. expand-terms
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
    // 3. build-query
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
    // 4. create-task（POST /literature-search）
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

test("shows raw topic, rule fallback, and editable candidate", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        raw_topic: "胃癌",
        candidate_source: "rule_fallback",
        prompt_version: "search-intent-v1",
        clarification_questions: ["需要限定发表时间范围吗？"],
        candidate: {
          topic: "胃癌", disease: "胃癌", intervention: null, target: null, mechanism: null,
          date_range: null, study_types: [], language: [], exclusions: [], retmax: 50,
        },
      }),
    }),
  );
  const wrapper = mount(LiteratureSearchView);
  await wrapper.get("input[required]").setValue("胃癌");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("原始主题：胃癌");
  expect(wrapper.text()).toContain("规则候选");
  expect(wrapper.text()).toContain("可编辑检索条件");
});

test("executes a search task from the built query and navigates to the results page", async () => {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/literature-search/results/:id", component: { template: "<div>results</div>" } }],
  });
  router.push("/literature-search");
  await router.isReady();

  const fetchMock = stubSearchChain(router);
  const wrapper = mount(LiteratureSearchView, { global: { plugins: [router] } });

  // 第一步：解析主题
  await wrapper.get("input[required]").setValue("胃癌 EGFR 免疫治疗");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.text()).toContain("模型候选");

  // 第二步：扩展关键词
  await wrapper.get(".expand-button").trigger("click");
  await flushPromises();

  // 第三步：构建检索式（SearchTermsEditor 的"生成 PubMed 检索式"按钮）
  const buildButton = wrapper.findAll("button").find((b) => b.text().includes("生成 PubMed 检索式"));
  expect(buildButton).toBeTruthy();
  await buildButton!.trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("执行 PubMed 检索");

  // 第四步：执行检索 → POST /literature-search → 跳转结果页
  await wrapper.get(".execute-button").trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/v1/literature-search",
    expect.objectContaining({ method: "POST" }),
  );
  expect(router.currentRoute.value.path).toBe("/literature-search/results/201");
});
