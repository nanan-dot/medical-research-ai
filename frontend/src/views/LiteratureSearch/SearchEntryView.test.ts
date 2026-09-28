import { mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import SearchEntryView from "./SearchEntryView.vue";

afterEach(() => {
  window.localStorage.clear();
});

test("AC-ENTRY-01 renders the search-center entry", async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search");
  await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });

  expect(wrapper.get("h1").text()).toBe("检索中心");
  expect(wrapper.get("textarea").attributes("maxlength")).toBe("500");
});

test("AC-ENTRY-03, AC-ENTRY-04 and AC-ENTRY-05 keep validation, count and mode independent", async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  const submit = wrapper.get(".submit");
  expect((submit.element as HTMLButtonElement).disabled).toBe(true);
  const input = wrapper.get("textarea");
  await input.setValue("a".repeat(501));
  expect((input.element as HTMLTextAreaElement).value).toHaveLength(500);
  await wrapper.get('input[value="pico"]').setValue();
  expect((input.element as HTMLTextAreaElement).value).toHaveLength(500);
});

test("shows locally stored history questions and refills the selected question", async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  window.localStorage.setItem("rag-medicine.search-question-history.v1", JSON.stringify([{ question: "既往检索问题", mode: "pico", usedAt: "2026-08-29T00:00:00.000Z" }]));
  const historyWrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  await historyWrapper.get(".example-wrap > button").trigger("click");
  await historyWrapper.get('[role="menuitem"]').trigger("click");
  expect((historyWrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("既往检索问题");
  expect((historyWrapper.get('input[value="pico"]').element as HTMLInputElement).checked).toBe(true);
  await wrapper.findAll(".template-grid button")[0].trigger("click");
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toContain("阿司匹林");
});

test("AC-ENTRY-08 through AC-ENTRY-11 sequence real API endpoints and hand off", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ raw_topic: "问题", candidate: { topic: "问题", disease: null, intervention: null, comparison: null, outcome: null, target: null, mechanism: null, date_range: null, study_types: [], language: [], exclusions: [], retmax: 20 }, clarification_questions: [], candidate_source: "rule_fallback", prompt_version: "v1" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ term_groups: [{ name: "disease", core_term: "Test", terms: ["test"], field_tag: "Title/Abstract", source: "curated_local_mapping" }], mesh_candidates: [], warnings: [], user_edits: {} }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ boolean_query: "test", field_tags: {}, explanations: [], user_edits: {} }) })
    .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ id: 41 }) });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("问题"); await wrapper.get(".submit").trigger("click");
  await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/v1/literature-search/parse-query", "/api/v1/literature-search/expand-terms", "/api/v1/literature-search/build-query", "/api/v1/literature-search/strategies"]);
  expect(JSON.parse(fetchMock.mock.calls[3][1]?.body as string)).toMatchObject({
    intent_mode: "unstructured",
    terms: [{ text: "test", concept_group: "disease", source: "smart_expansion" }],
  });
  expect(JSON.parse(window.localStorage.getItem("rag-medicine.search-question-history.v1") ?? "[]")).toMatchObject([
    { question: "问题", mode: "auto" },
  ]);
  expect(router.currentRoute.value.path).toBe("/literature-search/workspace");
  vi.unstubAllGlobals();
});

test("AC-ENTRY-10 preserves the question after a failed request and retries", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: "服务暂不可用" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ raw_topic: "胃癌", candidate: { topic: "胃癌", disease: null, intervention: null, comparison: null, outcome: null, target: null, mechanism: null, date_range: null, study_types: [], language: [], exclusions: [], retmax: 20 }, clarification_questions: [], candidate_source: "rule_fallback", prompt_version: "v1" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ term_groups: [{ name: "disease", core_term: "Test", terms: ["test"], field_tag: "Title/Abstract", source: "curated_local_mapping" }], mesh_candidates: [], warnings: [], user_edits: {} }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ boolean_query: "test", field_tags: {}, explanations: [], user_edits: {} }) })
    .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ id: 42 }) });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("胃癌"); await wrapper.get(".submit").trigger("click");
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("胃癌");
  await wrapper.get(".error button").trigger("click");
  await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));
  expect(router.currentRoute.value.path).toBe("/literature-search/workspace");
  vi.unstubAllGlobals();
});

test("does not send an invalid empty term group to build-query", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ raw_topic: "未映射问题", candidate: { topic: "未映射问题", disease: null, intervention: null, comparison: null, outcome: null, target: null, mechanism: null, date_range: null, study_types: [], language: [], exclusions: [], retmax: 20 }, clarification_questions: [], candidate_source: "rule_fallback", prompt_version: "v1" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ term_groups: [], mesh_candidates: [], warnings: [], user_edits: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  await wrapper.get("textarea").setValue("未映射问题"); await wrapper.get(".submit").trigger("click");
  await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));

  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(wrapper.text()).toContain("未能将该问题映射为可执行的 PubMed 英文术语");
  vi.unstubAllGlobals();
});

test("AC-ENTRY-14 submits only with Control plus Enter", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: "服务暂不可用" }) });
  vi.stubGlobal("fetch", fetchMock);
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/literature-search", component: SearchEntryView }, { path: "/literature-search/history", component: { template: "<div />" } }, { path: "/literature-search/workspace", component: { template: "<div />" } }] });
  await router.push("/literature-search"); await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });
  const textarea = wrapper.get("textarea"); await textarea.setValue("问题"); await textarea.trigger("keydown", { key: "Enter" });
  expect(fetchMock).not.toHaveBeenCalled();
  await textarea.trigger("keydown", { key: "Enter", ctrlKey: true });
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(fetchMock).toHaveBeenCalledOnce();
  vi.unstubAllGlobals();
});
