import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DuplicateReview from "./DuplicateReview.vue";

describe("DuplicateReview", () => {
  it("shows provided matching evidence and emits manual actions", async () => {
    const wrapper = mount(DuplicateReview, {
      props: { loading: false, groups: [{ id: 1, trigger_task_id: 1, match_method: "title_normalized", confidence: "fuzzy", status: "pending_resolution", created_at: "2026-08-05", resolution: null, members: [{ result_id: 2, record_pmid: "10", canonical_result_id: null, canonical_record_pmid: null, source_search_ids: [1, 2] }] }] },
    });
    expect(wrapper.text()).toContain("标题标准化候选");
    expect(wrapper.text()).toContain("来源任务 1、2");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("run")).toHaveLength(1);
    await wrapper.get(".group-actions button").trigger("click");
    expect(wrapper.emitted("resolve")?.[0]).toEqual([1, "merge_all"]);
  });
});
