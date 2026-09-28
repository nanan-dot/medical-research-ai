import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentSummaryCards from "./DocumentSummaryCards.vue";

const summary = {
  total: 18,
  processed: 13,
  ai_available: 9,
  processing: 4,
  needs_attention: 2,
  issue_breakdown: { parse_failed: 1, unsupported_format: 0, unavailable_file: 0, index_failed: 1, other: 0 },
  source_types: [],
  snapshot_at: "2026-08-30T00:00:00Z",
};

describe("DocumentSummaryCards", () => {
  it("renders all five API-derived resource statistics and their accounting tooltips", () => {
    const wrapper = mount(DocumentSummaryCards, {
      props: { summary, loading: false, error: false, active: "all" },
    });

    expect(wrapper.findAll("button")).toHaveLength(5);
    expect(wrapper.findAll(".card-note")).toHaveLength(5);
    expect(wrapper.text()).toContain("资料总量");
    expect(wrapper.text()).toContain("已处理");
    expect(wrapper.text()).toContain("AI 可使用");
    expect(wrapper.text()).toContain("处理中");
    expect(wrapper.text()).toContain("异常");
    expect(wrapper.text()).toContain("18");
    expect(wrapper.text()).toContain("全部导入资料");
    expect(wrapper.find('[title*="全库"]').exists()).toBe(true);
  });

  it("does not turn an unavailable summary into a zero", () => {
    const wrapper = mount(DocumentSummaryCards, {
      props: { summary: null, loading: false, error: true, active: "all" },
    });

    expect(wrapper.text()).toContain("暂不可用");
    expect(wrapper.text()).not.toContain("0");
  });
});
