import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ReaderLeftRail from "./ReaderLeftRail.vue";
import type { ReaderBootstrap } from "../../api/paperReader";

const bootstrap = (outline: ReaderBootstrap["capabilities"]["outline"]): ReaderBootstrap => ({
  paper: { paper_item_id: 1, document_id: 2, title: "Study", journal: "NEJM", year: 2024, paper_type: "RCT", is_favorite: false },
  document: { file_hash: "a", page_count: 38, content_url: "/paper.pdf" },
  revision_fence: { anchor_revision_id: 1, segmentation_revision_id: 2 },
  resume: { session_id: 1, page: 12, viewport_offset_ratio: 0 },
  progress: { qualified_pages: 26, total_pages: 38, percent: 68 },
  outline: outline === "available" ? [{ id: 4, title: "研究结果", level: 1, first_page: 12, last_page: 15 }] : [],
  record_counts: { highlights: 12, annotations: 8, questions: 4, bookmarks: 8 },
  preference: { view_mode: "original", zoom_percent: 100, left_panel_mode: "outline", left_collapsed: false, right_panel_tab: "copilot", focus_mode: false, version: 1 },
  capabilities: { outline, chapter_bundle: "not_ready", copilot: "available", translation: "unavailable" },
});

describe("ReaderLeftRail", () => {
  it("keeps progress compact and reports ready outline state", () => {
    const wrapper = mount(ReaderLeftRail, { props: { bootstrap: bootstrap("available"), collapsed: false } });
    expect(wrapper.find(".progress-section").text()).toContain("26 / 38 页");
    expect(wrapper.find(".outline-item").text()).toContain("研究结果");
  });

  it("uses a compact processing fallback while outline is pending", () => {
    const wrapper = mount(ReaderLeftRail, { props: { bootstrap: bootstrap("not_ready"), collapsed: false } });
    expect(wrapper.text()).toContain("论文结构处理中");
    expect(wrapper.find(".outline-empty").exists()).toBe(false);
  });

  it("emits the first page when a ready chapter is selected", async () => {
    const wrapper = mount(ReaderLeftRail, { props: { bootstrap: bootstrap("available"), collapsed: false } });
    await wrapper.get(".outline-item").trigger("click");
    expect(wrapper.emitted("page")).toEqual([[12]]);
  });
});
