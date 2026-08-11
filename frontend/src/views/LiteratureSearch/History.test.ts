import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { LiteratureSearchTask } from "../../api/literatureSearch";
import History from "./History.vue";

const routerStubs = { RouterLink: { template: "<a><slot /></a>" } };

const succeededTask: LiteratureSearchTask = {
  id: 1,
  original_query: "胃癌 EGFR 免疫治疗",
  structured_query: "",
  search_string: '"stomach neoplasms"[Title/Abstract] AND "EGFR"[Title/Abstract] AND immunotherapy',
  database: "pubmed",
  result_count: 1,
  retmax: 20,
  filters: "",
  model_version: "search-intent-v1",
  user_edits: "",
  status: "succeeded",
  error_message: null,
  created_at: "2026-08-05T10:00:00Z",
  searched_at: "2026-08-05T10:01:00Z",
  latest_result_id: 101,
  versions: [
    { version: 1, result_id: 101, searched_at: "2026-08-05T10:01:00Z", result_count: 1, change: null },
  ],
};

afterEach(() => vi.unstubAllGlobals());

test("renders the task list with topic, search string, status and rerun action", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [succeededTask] })),
    ),
  );
  const wrapper = mount(History, { global: { stubs: routerStubs } });
  await flushPromises();

  expect(wrapper.text()).toContain("检索历史");
  expect(wrapper.text()).toContain("胃癌 EGFR 免疫治疗");
  expect(wrapper.text()).toContain("已完成");
  expect(wrapper.text()).toContain("v1");
  expect(wrapper.text()).toContain("重跑");
});

test("rerun posts to the rerun endpoint and shows the version change summary", async () => {
  const updatedTask: LiteratureSearchTask = {
    ...succeededTask,
    result_count: 3,
    latest_result_id: 102,
    versions: [
      { version: 1, result_id: 101, searched_at: "2026-08-05T10:01:00Z", result_count: 1, change: null },
      {
        version: 2,
        result_id: 102,
        searched_at: "2026-08-05T10:05:00Z",
        result_count: 3,
        change: {
          previous_count: 1,
          current_count: 3,
          count_delta: 2,
          added_count: 2,
          removed_count: 0,
          added_pmids: ["39000401", "39000402"],
          removed_pmids: [],
        },
      },
    ],
  };
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [succeededTask] })),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          task: updatedTask,
          change: updatedTask.versions[1].change,
          new_result_id: 102,
        }),
      ),
    );
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { global: { stubs: routerStubs } });
  await flushPromises();

  await wrapper.get(".rerun").trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/v1/literature-search/1/rerun",
    expect.objectContaining({ method: "POST" }),
  );
  expect(wrapper.text()).toContain("新增 2 条");
  expect(wrapper.text()).toContain("减少 0 条");
  expect(wrapper.text()).toContain("39000401");
  expect(wrapper.emitted("rerunSucceeded")?.[0]).toEqual([{ resultId: 102, taskId: 1 }]);
});
