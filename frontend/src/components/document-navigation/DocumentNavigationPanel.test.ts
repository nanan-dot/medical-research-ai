import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentNavigationPanel from "./DocumentNavigationPanel.vue";

const source = {
  id: 4,
  name: "肿瘤免疫治疗资料",
  source_type: "local_folder" as const,
  root_path: "H:\\research",
  enabled: true,
  sync_status: "completed" as const,
  last_sync_time: null,
  error_message: null,
  stats: { total_files: 2, parsed: 2, indexed: 2, pending: 0, failed: 0 },
};

describe("DocumentNavigationPanel", () => {
  it("uses the current source as the default AI navigation scope", async () => {
    const wrapper = mount(DocumentNavigationPanel, { props: { sources: [source], defaultSourceId: 4, loading: false } });
    await wrapper.get("#navigation-query").setValue("耐药机制");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("search")?.[0]).toEqual(["耐药机制", 4, true]);
  });

  it("uses global scope when no source is selected", async () => {
    const wrapper = mount(DocumentNavigationPanel, { props: { sources: [source], defaultSourceId: null, loading: false } });
    await wrapper.get("#navigation-query").setValue("耐药机制");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("search")?.[0]).toEqual(["耐药机制", null, true]);
  });
});
