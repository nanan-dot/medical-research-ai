import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import ContinueResearchPanel from "./ContinueResearchPanel.vue";

afterEach(() => vi.unstubAllGlobals());

test("uses the aggregated research-record endpoint and does not show a boolean query", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    total: 1, offset: 0, limit: 10, items: [{
      id: 8, original_query: "直肠癌新辅助免疫治疗", result_count: 33,
      status: "succeeded", error_message: null, searched_at: "2026-08-13T06:47:08Z",
      latest_result_id: 13, latest_change: null,
    }],
  })));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(ContinueResearchPanel, { global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } } });
  await flushPromises();
  expect(wrapper.text()).toContain("直肠癌新辅助免疫治疗");
  expect(wrapper.text()).toContain("共 33 篇结果");
  expect(wrapper.text()).not.toContain("Title/Abstract");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/literature-search/history?offset=0&limit=10", undefined);
});
