import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ResourceLibraryFilters } from "../../api/resourceLibrary";
import DocumentFilters from "./DocumentFilters.vue";

const filters: ResourceLibraryFilters = {
  query: "",
  sourceIds: [],
  nodeId: null,
  fileTypes: [],
  statuses: [],
  updatedFrom: null,
  updatedTo: null,
  sortBy: "updated_at",
  sortOrder: "desc",
};

describe("DocumentFilters", () => {
  afterEach(() => vi.useRealTimers());

  it("emits a single server-side filter contract after a debounced unified search", async () => {
    vi.useFakeTimers();
    const wrapper = mount(DocumentFilters, {
      props: {
        filters,
        facets: { sources: [{ value: "7", count: 3 }], source_types: [], file_types: [{ value: "pdf", count: 2 }], statuses: [{ value: "ai_available", count: 2 }] },
        disabled: false,
      },
    });

    await wrapper.get('input[placeholder="搜索资料标题、正文内容、路径或来源…"]').setValue("ILD");
    await vi.advanceTimersByTimeAsync(300);

    expect(wrapper.emitted("change")?.[0]).toEqual([expect.objectContaining({ query: "ILD" })]);
    expect(wrapper.text()).toContain("来源");
    expect(wrapper.text()).toContain("类型");
    expect(wrapper.text()).toContain("状态");
    expect(wrapper.text()).toContain("更新时间");
    expect(wrapper.text()).toContain("筛选");
  });
});
