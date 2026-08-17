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
    item("1", "review", 1, "综述标题A"),
    item("1b", "review", 2, "综述标题B"),
    item("2", "guideline", 3, "指南标题"),
    item("3", "original_research", 4, null),
  ],
};

describe("ReadingPlan", () => {
  it("shows chapter index and renders the active chapter sequence", async () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: false, error: "" },
    });

    expect(wrapper.find(".plan-title").exists()).toBe(false);
    expect(wrapper.get(".plan-toolbar .generate-button").text()).toBe("重新生成");
    // 顶部横向章节索引包含所有非空分类的 groupLabel。
    expect(wrapper.text()).toContain("先建立证据全貌");
    expect(wrapper.text()).toContain("再看临床决策依据");
    expect(wrapper.text()).toContain("核验一手研究");
    // 默认显示第一个分类（review），badge 为「高质量综述」。
    expect(wrapper.get(".chapter-header").text()).toContain("高质量综述");
    // 当前章节只渲染当前分类的 priority 序列。
    expect(wrapper.findAll(".priority").map((node) => node.text())).toEqual(["1", "2"]);
    expect(wrapper.get(".reason-disclosure summary").text()).toContain("查看推荐依据");
    expect(wrapper.text()).toContain("文献类型：Review");
    expect(wrapper.text()).toContain("排序来源：算法规则");
    // 标题未提供时如实显示，不虚构标题（切到原始研究分类）。
    const indexButtons = wrapper.findAll(".plan-index-item");
    await indexButtons[2].trigger("click");
    expect(wrapper.get(".chapter-header").text()).toContain("代表性原始研究");
    expect(wrapper.text()).toContain("标题未提供");
  });

  it("emits generate and move events", async () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: false, error: "" },
    });

    await wrapper.get(".generate-button").trigger("click");
    expect(wrapper.emitted("generate")).toHaveLength(1);

    // review 分类内：第一条上移禁用，第二条上移启用并提交完整 PMID 顺序。
    const firstActions = wrapper.findAll(".item-actions")[0].findAll("button");
    expect((firstActions[0].element as HTMLButtonElement).disabled).toBe(true);

    const secondActions = wrapper.findAll(".item-actions")[1].findAll("button");
    await secondActions[0].trigger("click");
    expect(wrapper.emitted("save")?.[0]).toEqual([["1b", "1", "2", "3"]]);
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

  it("keeps restored-order metadata out of the compact plan toolbar", () => {
    const wrapper = mount(ReadingPlan, {
      props: { order, loading: false, saving: false, error: "", restoreNotice: "已恢复您保存的人工阅读顺序" },
    });
    expect(wrapper.find(".restore-notice").exists()).toBe(false);
    expect(wrapper.get(".generate-button").text()).toBe("重新生成");
  });
});
