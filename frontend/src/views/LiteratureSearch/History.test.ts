import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { LiteratureSearchHistoryEntry } from "../../api/literatureSearch";
import History from "./History.vue";
import { formatSearchChangeNotice } from "./searchChangeNotice";

const routerStubs = { RouterLink: { template: "<a><slot /></a>" } };
const record: LiteratureSearchHistoryEntry = {
  id: 1, original_query: "胃癌 EGFR 免疫治疗", result_count: 3, status: "succeeded",
  error_message: null, searched_at: "2026-08-05T10:01:00Z", latest_result_id: 101,
  latest_change: null,
};
afterEach(() => vi.unstubAllGlobals());

test("renders one research record without exposing its boolean strategy or version", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] }))));
  const wrapper = mount(History, { global: { stubs: routerStubs } }); await flushPromises();
  expect(wrapper.text()).toContain("研究主题");
  expect(wrapper.text()).toContain("最新结果 3 篇");
  expect(wrapper.text()).not.toContain("Title/Abstract");
  expect(wrapper.text()).not.toContain("版本变化");
  expect(wrapper.findAll(".history-item")).toHaveLength(1);
  expect(wrapper.html()).toContain("/literature-search/results/101?task=1&amp;from=history");
});

test("rerun reloads the aggregated history and selects the returned result", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ task: { id: 1 }, new_result_id: 102 })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [{ ...record, latest_result_id: 102 }] })));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { global: { stubs: routerStubs } }); await flushPromises();
  await wrapper.get(".rerun").trigger("click"); await flushPromises();
  expect(wrapper.emitted("rerunSucceeded")?.[0]).toEqual([{ resultId: 102, taskId: 1 }]);
  expect(fetchMock.mock.calls[0]?.[0]).toContain("/literature-search/history");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/literature-search/1/rerun",
    expect.objectContaining({ body: JSON.stringify({ retmax: 500 }) }),
  );
});

test("only produces a user-facing notice for meaningful result changes", () => {
  expect(formatSearchChangeNotice({ previous_count: 33, current_count: 33, count_delta: 0, added_count: 0, removed_count: 0, added_pmids: [], removed_pmids: [] })).toBeNull();
  expect(formatSearchChangeNotice({ previous_count: 33, current_count: 35, count_delta: 2, added_count: 2, removed_count: 0, added_pmids: ["1", "2"], removed_pmids: [] })).toBe("本次检索发现 2 篇新增文献");
});
