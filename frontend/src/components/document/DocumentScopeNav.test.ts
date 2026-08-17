import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentScopeNav from "./DocumentScopeNav.vue";

const source = {
  id: 8,
  name: "临床肿瘤资料",
  source_type: "local_folder" as const,
  root_path: "H:\\clinical",
  enabled: true,
  sync_status: "completed" as const,
  last_sync_time: null,
  error_message: null,
  stats: { total_files: 12, parsed: 10, indexed: 9, pending: 1, failed: 2 },
};

describe("DocumentScopeNav", () => {
  it("renders the real source count, exception state, and selected range", () => {
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source], selectedSourceId: 8, total: 12 },
      global: { stubs: { RouterLink: { props: ["to"], template: "<a :href=\"to\"><slot /></a>" } } },
    });
    const items = wrapper.findAll(".scope-item");
    expect(items[1].classes()).toContain("active");
    expect(items[1].text()).toContain("临床肿瘤资料");
    expect(items[1].text()).toContain("12");
    expect(items[1].text()).toContain("2 个异常");
    expect(wrapper.find(".failure-hint").classes()).toContain("failure-hint");
    expect(wrapper.get(".scope-heading a").attributes("href")).toBe("/sources");
  });

  it("emits the selected source id when a source is clicked", async () => {
    const wrapper = mount(DocumentScopeNav, {
      props: { sources: [source], selectedSourceId: null, total: 12 },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    await wrapper.findAll(".scope-item")[1].trigger("click");

    expect(wrapper.emitted("select")).toEqual([[8]]);
  });
});
