import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentScopeNav from "./DocumentScopeNav.vue";

const source = {
  id: 8,
  name: "临床肿瘤资料",
  source_type: "local_folder" as const,
  root_path: "H:\\\\clinical",
  enabled: true,
  sync_status: "completed" as const,
  last_sync_time: null,
  error_message: null,
  stats: { total_files: 12, parsed: 10, indexed: 9, pending: 1, failed: 2 },
};

describe("DocumentScopeNav", () => {
  it("renders the real source count and selected range without failure-hint noise", () => {
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source], selectedSourceId: 8, recentSourceIds: [], total: 12 },
      global: { stubs: { RouterLink: { props: ["to"], template: "<a :href='to'><slot /></a>" } } },
    });
    const items = wrapper.findAll(".scope-item");
    expect(items[1].classes()).toContain("active");
    expect(items[1].text()).toContain("临床肿瘤资料");
    expect(items[1].text()).toContain("12");
    // 不再显示“N 个需处理”红字提示，避免来源树拥挤。
    expect(wrapper.text()).not.toContain("需处理");
    expect(wrapper.text()).not.toContain("异常");
    expect(wrapper.find(".scope-heading a").attributes("href")).toBe("/sources");
  });

  it("uses real folder/vault svg icons, not text glyphs", () => {
    const obsidianSource = { ...source, id: 9, name: "临床笔记库", source_type: "obsidian_vault" as const };
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source, obsidianSource], selectedSourceId: null, recentSourceIds: [], total: 24 },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    // 图标是内联 SVG，不再是 □ / ▣ 文字符号。
    expect(wrapper.findAll(".type-icon svg").length + wrapper.findAll("svg.type-icon").length).toBeGreaterThan(0);
    expect(wrapper.text()).not.toContain("□");
    expect(wrapper.text()).not.toContain("▣");
    expect(wrapper.text()).toContain("Obsidian Vault (1)");
    expect(wrapper.text()).toContain("临床笔记库");
  });

  it("emits the selected source id when a source is clicked", async () => {
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source], selectedSourceId: null, recentSourceIds: [], total: 12 },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    await wrapper.findAll(".scope-item")[1].trigger("click");

    expect(wrapper.emitted("select")).toEqual([[8]]);
  });

  it("separates actual recent selections without inventing entries", () => {
    const obsidianSource = { ...source, id: 9, name: "临床笔记库", source_type: "obsidian_vault" as const };
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source, obsidianSource], selectedSourceId: 8, recentSourceIds: [9, 8, 9], total: 24 },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    expect(wrapper.text()).toContain("最近使用");
    expect(wrapper.findAll(".scope-item--recent")).toHaveLength(2);
  });
});
