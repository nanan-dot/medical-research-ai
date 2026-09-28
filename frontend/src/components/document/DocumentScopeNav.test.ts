import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ResourceLibraryItem, ResourceSourceTree } from "../../api/resourceLibrary";
import DocumentScopeNav from "./DocumentScopeNav.vue";

const tree: ResourceSourceTree = {
  groups: [
    {
      source_type: "local",
      node_id: "group:local",
      descendant_count: 4,
      health: "ready",
      children: [{
        node_id: "source:7",
        parent_id: "group:local",
        name: "本地临床资料",
        relative_path: "",
        source_id: 7,
        direct_count: 1,
        descendant_count: 4,
        health: "ready",
        children: [{
          node_id: "tree:7:ild",
          parent_id: "source:7",
          name: "ILD 核心文献",
          relative_path: "ild",
          source_id: 7,
          direct_count: 1,
          descendant_count: 3,
          health: "ready",
          children: [],
        }],
      }],
    },
    { source_type: "obsidian", node_id: "group:obsidian", descendant_count: 0, health: "unavailable", children: [] },
    { source_type: "zotero", node_id: "group:zotero", descendant_count: 0, health: "ready", children: [] },
  ],
};

const recentItems: ResourceLibraryItem[] = [{
  id: 12,
  knowledge_source_id: 7,
  file_path: "ild/study.pdf",
  original_filename: "study.pdf",
  media_type: "application/pdf",
  file_hash: "hash",
  file_size: 12,
  modified_time: "2026-08-30T00:00:00Z",
  scan_state: "pending",
  parse_status: "succeeded",
  index_status: "succeeded",
  error_code: null,
  error_message: null,
  retry_count: 0,
  started_at: null,
  finished_at: null,
  parsed_is_scanned: false,
  source_name: "本地临床资料",
  source_type: "local_folder",
  relative_path: "ild/study.pdf",
  display_name: "study.pdf",
  task_status: null,
  phase: null,
  current_item: null,
  last_opened_at: "2026-08-30T00:00:00Z",
  open_count: 1,
  status: "ai_available",
  match_fields: [],
  snippet: null,
  locator: null,
}];

function mountRail() {
  return mount(DocumentScopeNav, {
    props: { tree, recentItems, selectedNodeId: null, total: 4, loading: false },
    global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
  });
}

describe("DocumentScopeNav", () => {
  afterEach(() => vi.useRealTimers());

  it("keeps the prescribed all/search/recent/tree/manage order without fabricating counts", () => {
    const wrapper = mountRail();
    const text = wrapper.text();
    const headings = wrapper.findAll("h2").map((heading) => heading.text());
    const railSections = wrapper.findAll(".scope-nav > *").map((element) => element.classes()[0]);

    expect(text.indexOf("全部资料")).toBeLessThan(text.indexOf("搜索资料来源或文件夹"));
    expect(text.indexOf("搜索资料来源或文件夹")).toBeLessThan(text.indexOf("最近使用"));
    expect(headings).toEqual(["最近使用", "资料来源"]);
    expect(railSections).toEqual(["all-resources", "source-search", "recent-section", "tree-section", "manage-sources"]);
    expect(text).toContain("不可用");
    expect(text).not.toContain("1280");
  });

  it("filters only the source tree after 150 ms and restores the previous expansion when cleared", async () => {
    vi.useFakeTimers();
    const wrapper = mountRail();
    const input = wrapper.get('input[placeholder="搜索资料来源或文件夹…"]');

    await input.setValue("ILD");
    await vi.advanceTimersByTimeAsync(150);
    expect(wrapper.text()).toContain("ILD 核心文献");
    // 资料树搜索不会干扰“最近使用”区；命中的祖先来源会保留以表达路径。
    expect(wrapper.text()).toContain("study.pdf");
    await input.setValue("");
    await vi.advanceTimersByTimeAsync(150);
    expect(wrapper.text()).toContain("本地临床资料");
  });

  it("supports tree keyboard expansion and opens recent items without changing the selected source", async () => {
    const wrapper = mountRail();
    const source = wrapper.get('[data-node-id="source:7"]');
    await source.trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.find('[data-node-id="tree:7:ild"]').exists()).toBe(true);
    await source.trigger("keydown", { key: "ArrowLeft" });
    expect(wrapper.find('[data-node-id="tree:7:ild"]').exists()).toBe(false);

    await wrapper.get('[aria-label="打开资料 study.pdf"]').trigger("click");
    expect(wrapper.emitted("openRecent")).toEqual([[recentItems[0]]]);
    expect(wrapper.emitted("selectNode")).toBeUndefined();
  });

  it("expands collapsed ancestors for a deep-linked tree node", async () => {
    const wrapper = mount(DocumentScopeNav, {
      props: { tree, recentItems, selectedNodeId: "tree:7:ild", total: 4, loading: false },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    expect(wrapper.get('[data-node-id="source:7"]').attributes("aria-expanded")).toBe("true");
    expect(wrapper.find('[data-node-id="tree:7:ild"]').exists()).toBe(true);
  });
});
