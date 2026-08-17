import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentWorkspaceSummary from "./DocumentWorkspaceSummary.vue";

describe("DocumentWorkspaceSummary", () => {
  it("removes duplicate context and keeps global processing metrics unavailable", () => {
    const wrapper = mount(DocumentWorkspaceSummary, {
      props: {
        sourceName: null,
        stats: null,
        total: 12,
      },
      global: {
        stubs: {
          RouterLink: { template: "<a><slot /></a>" },
        },
      },
    });

    expect(wrapper.text()).toContain("文件总数");
    expect(wrapper.text()).toContain("已解析");
    expect(wrapper.text()).toContain("已索引");
    expect(wrapper.text()).toContain("待处理");
    expect(wrapper.text()).toContain("异常");
    expect(wrapper.findAll(".metric-value--unavailable")).toHaveLength(4);
    expect(wrapper.text()).not.toContain("文档库 / 全部知识库");
    expect(wrapper.text()).not.toContain("管理资料");
    expect(wrapper.text()).not.toContain("处理统计仅在选定知识源后显示");
  });

  it("renders selected source statistics from the real source stats object", () => {
    const wrapper = mount(DocumentWorkspaceSummary, {
      props: {
        sourceName: "临床肿瘤资料",
        stats: { total_files: 12, parsed: 10, indexed: 9, pending: 1, failed: 2 },
        total: 12,
      },
    });

    expect(wrapper.text()).toContain("临床肿瘤资料");
    expect(wrapper.findAll(".metric-value--unavailable")).toHaveLength(0);
    expect(wrapper.text()).toContain("10");
    expect(wrapper.text()).toContain("9");
    expect(wrapper.text()).toContain("1");
    expect(wrapper.text()).toContain("2");
  });
});
