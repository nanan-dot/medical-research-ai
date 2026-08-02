import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import PaperAnalysisView from "./PaperAnalysisView.vue";

afterEach(() => vi.restoreAllMocks());

test("renders grounded values, missing markers and export", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 3, document_id: 1, analysis_status: "succeeded", template_version: "general-v1", model_version: "test", generation: 1, structured_result: { sample_size: { value: "120 participants", kind: "fact", source_indices: [0] }, population: { value: "未找到", kind: "not_found", source_indices: [] } }, sources: [{ citation: "Trial", title: null, page_start: 4, page_end: 5 }], pending_confirmations: ["population"], error_code: null, error_message: null }) }));
  const wrapper = mount(PaperAnalysisView);
  await wrapper.get("input").setValue("1"); await wrapper.get("form").trigger("submit"); await flushPromises();
  expect(wrapper.text()).toContain("120 participants");
  expect(wrapper.text()).toContain("未找到");
  expect(wrapper.text()).toContain("Trial · 第 4 页");
  expect(wrapper.get("a").attributes("href")).toBe("/api/v1/paper-analysis/3/export");
});
