import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ReadingOrder, ReadingOrderItem } from "../../api/literatureSearch";
import ReadingPlan from "./ReadingPlan.vue";

const item = (pmid: string, category: ReadingOrderItem["category"], priority: number, title: string | null): ReadingOrderItem => ({
  pmid,
  category,
  priority,
  reason: `理由 ${pmid}：综述/指南/原始研究/前沿/高相关的规则解释。`,
  evidence_features: ["verified=true", `position=${priority - 1}`, "publication_type=Review"],
  title,
  year: 2024,
});

const order: ReadingOrder = {
  result_id: 7,
  order_source: "rule",
  generated_at: "2026-08-05T00:00:00+00:00",
  items: [
    item("1", "review", 1, "综述标题"),
    item("2", "guideline", 2, "指南标题"),
    item("3", "original_research", 3, null),
  ],
};

describe("ReadingPlan", () => {
  it("renders category labels, priority, reason and evidence features", () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: false, error: "" },
    });

    expect(wrapper.text()).toContain("推荐阅读顺序");
    expect(wrapper.text()).toContain("高质量综述");
    expect(wrapper.text()).toContain("指南或共识");
    expect(wrapper.text()).toContain("代表性原始研究");
    // priority 1..n 顺序展示。
    expect(wrapper.findAll(".priority").map((node) => node.text())).toEqual(["1", "2", "3"]);
    // reason 与 evidence_features 展示。
    expect(wrapper.text()).toContain("理由 1：综述");
    expect(wrapper.text()).toContain("publication_type=Review");
    expect(wrapper.text()).toContain("排序来源：算法规则");
    // 标题未提供时如实显示，不虚构标题。
    expect(wrapper.text()).toContain("标题未提供");
  });

  it("emits generate and move events", async () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: false, error: "" },
    });

    await wrapper.get(".generate-button").trigger("click");
    expect(wrapper.emitted("generate")).toHaveLength(1);

    // 第一条不能上移；第二条上移会交换位置并提交完整 PMID 顺序。
    const firstActions = wrapper.findAll(".item-actions")[0].findAll("button");
    expect((firstActions[0].element as HTMLButtonElement).disabled).toBe(true);

    const secondActions = wrapper.findAll(".item-actions")[1].findAll("button");
    await secondActions[0].trigger("click");
    expect(wrapper.emitted("save")?.[0]).toEqual([["2", "1", "3"]]);
  });

  it("shows empty state when no order yet", () => {
    const wrapper = mount(ReadingPlan, {
      props: { order: null, loading: false, saving: false, error: "" },
    });
    expect(wrapper.text()).toContain("尚未生成阅读顺序");
  });

  it("shows error and saving states", () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: true, error: "生成失败" },
    });
    expect(wrapper.text()).toContain("生成失败");
    expect(wrapper.text()).toContain("正在保存人工顺序");
  });
});
