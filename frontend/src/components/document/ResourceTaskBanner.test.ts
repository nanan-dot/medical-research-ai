import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ResourceTaskBanner from "./ResourceTaskBanner.vue";

describe("ResourceTaskBanner", () => {
  it("shows only persisted tasks and does not invent a percentage", () => {
    const wrapper = mount(ResourceTaskBanner, {
      props: { tasks: [{ id: 7, displayName: "ILD 临床试验资料", taskStatus: "running", phase: "建立索引", progress: null }], total: 1 },
    });

    expect(wrapper.text()).toContain("正在处理 ILD 临床试验资料");
    expect(wrapper.text()).toContain("建立索引");
    expect(wrapper.text()).not.toMatch(/\d+%/);
  });
});
