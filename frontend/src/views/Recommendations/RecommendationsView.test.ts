import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import RecommendationsView from "./RecommendationsView.vue";

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

const citation = (overrides = {}) => ({
  pmid: "12345678",
  doi: null,
  title: "Server returned citation title",
  authors: ["Chen A", "Wang B"],
  journal: "Medical Journal",
  year: 2024,
  entry_type: "article",
  verified: true,
  verified_by: "pubmed",
  verified_on: "2026-08-11",
  has_abstract: true,
  abstract: "The exact abstract returned by the server.",
  publication_types: ["Journal Article"],
  withdrawn: false,
  ...overrides,
});

const response = (overrides = {}) => ({
  query: "test topic",
  status: "completed",
  warnings: [],
  items: [{ citation: citation(), recommendation_reason: "Exact server recommendation reason." }],
  ...overrides,
});

test("submits the topic to the recommendations API and renders server reason", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response())));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(RecommendationsView);

  await wrapper.get("textarea").setValue("test topic");
  await wrapper.get("select").setValue("3");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/recommendations",
    expect.objectContaining({ body: JSON.stringify({ query: "test topic", candidate_count: 3 }) }),
  );
  expect(wrapper.text()).toContain("Exact server recommendation reason.");
  expect(wrapper.text()).toContain("Server returned citation title");
});

test("restores the last real server response from this browser after remount", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response())));
  vi.stubGlobal("fetch", fetchMock);
  const first = mount(RecommendationsView);
  await first.get("textarea").setValue("test topic");
  await first.get("form").trigger("submit");
  await flushPromises();
  first.unmount();

  const restored = mount(RecommendationsView);
  await flushPromises();
  expect(restored.text()).toContain("Server returned citation title");
  expect(restored.text()).toContain("已保存在本浏览器");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await restored.get(".clear-saved").trigger("click");
  expect(window.localStorage.getItem("rag-medicine:recommendations:last-response")).toBeNull();
});

test("discloses only a returned abstract and makes missing abstracts unavailable", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(response())))
    .mockResolvedValueOnce(new Response(JSON.stringify(response({ items: [{ citation: citation({ abstract: null, has_abstract: false }), recommendation_reason: "Reason" }] }))));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(RecommendationsView);

  await wrapper.get("textarea").setValue("topic");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.text()).not.toContain("The exact abstract returned by the server.");
  await wrapper.get(".abstract-disclosure button").trigger("click");
  expect(wrapper.text()).toContain("The exact abstract returned by the server.");

  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.find(".abstract-disclosure button").exists()).toBe(false);
  expect(wrapper.text()).toContain("摘要不可用");
});

test("uses a safe PubMed link and states full-text access is restricted without a library item", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(response()))));
  const wrapper = mount(RecommendationsView);
  await wrapper.get("textarea").setValue("topic");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  const link = wrapper.get('a[href="https://pubmed.ncbi.nlm.nih.gov/12345678/"]');
  expect(link.attributes("target")).toBe("_blank");
  expect(link.attributes("rel")).toBe("noopener noreferrer");
  expect(wrapper.text()).toContain("全文获取受限");
});

test("renders warning, empty, unavailable, and request-error states", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(response({ status: "completed_with_warnings", warnings: ["Partial server warning"] }))))
    .mockResolvedValueOnce(new Response(JSON.stringify(response({ items: [] }))))
    .mockResolvedValueOnce(new Response(JSON.stringify(response({ status: "unavailable", items: [], warnings: ["PubMed unavailable"] }))))
    .mockRejectedValueOnce(new Error("Network request failed"));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(RecommendationsView);
  await wrapper.get("textarea").setValue("topic");

  for (const expected of ["Partial server warning", "没有找到可核验文献", "PubMed unavailable", "Network request failed"]) {
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain(expected);
  }
});
