import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import PaperAnalysisView from "./PaperAnalysisView.vue";

afterEach(() => vi.restoreAllMocks());

function mockAnalysisResponse() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 3,
        document_id: 1,
        analysis_status: "succeeded",
        template_version: "general-v1",
        model_version: "test",
        generation: 1,
        structured_result: {
          basic_information: { value: "Current study title\nFirst Author", kind: "fact", source_indices: [0] },
          study_type: { value: "Randomized trial", kind: "fact", source_indices: [0] },
          sample_size: { value: "", kind: "not_found", source_indices: [] },
        },
        sources: [{ citation: "Trial", title: null, page_start: 4, page_end: 5, excerpt: "Source excerpt", score: 0.9 }],
        pending_confirmations: ["sample_size"],
        error_code: null,
        error_message: null,
      }),
    }),
  );
}

test("shows only the implemented paper-analysis entry before an analysis is generated", () => {
  const wrapper = mount(PaperAnalysisView);

  expect(wrapper.text()).toContain("PAPER RESEARCH · SINGLE-PAPER ANALYSIS");
  expect(wrapper.text()).toContain("论文分析");
  expect(wrapper.get('label[for="document-id"]').text()).toContain("已索引文档 ID");
  expect(wrapper.find('[aria-label="论文研究二级导航"]').text()).toBe("论文分析");
  expect(wrapper.text()).not.toContain("创建组会汇报");
  expect(wrapper.text()).not.toContain("证据问答");
  expect(wrapper.text()).not.toContain("笔记与标注");
});

test("renders only grounded analysis context, missing values, and derived evidence status", async () => {
  mockAnalysisResponse();
  const wrapper = mount(PaperAnalysisView);

  await wrapper.get("input").setValue("1");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("Current study title");
  expect(wrapper.text()).toContain("文档 ID 1");
  expect(wrapper.text()).toContain("分析完成");
  expect(wrapper.text()).toContain("原文证据 1 条");
  expect(wrapper.text()).toContain("Randomized trial");
  expect(wrapper.text()).toContain("未提供");
  expect(wrapper.text()).toContain("直接证据");
  expect(wrapper.find('a[href="/api/v1/paper-analysis/3/export"]').exists()).toBe(true);
});

test("opens the evidence rail when a report source locator is selected", async () => {
  mockAnalysisResponse();
  const wrapper = mount(PaperAnalysisView);

  await wrapper.get("input").setValue("1");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  await wrapper.get('button[aria-label="定位到第 4 页来源"]').trigger("click");

  expect(wrapper.find(".grid-rail").classes()).toContain("rail-open");
});
