import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";
import ResearchStartPanel from "./ResearchStartPanel.vue";
import { literatureSearchApi } from "../../api/literatureSearch";

vi.mock("../../api/literatureSearch", () => ({
  literatureSearchApi: {
    parseQuery: vi.fn().mockResolvedValue({}),
  },
}));

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/", component: { template: "<div>home</div>" } },
      { path: "/literature-search", component: { template: "<div>search</div>" } },
    ],
  });
}

describe("ResearchStartPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls the real parse-query backend when a query is submitted", async () => {
    const router = makeRouter();
    const wrapper = mount(ResearchStartPanel, { global: { plugins: [router] } });
    await wrapper.find("input").setValue("晚期实体瘤一线治疗方案选择");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(literatureSearchApi.parseQuery).toHaveBeenCalledWith("晚期实体瘤一线治疗方案选择");
  });

  it("does not call the backend for an empty query", async () => {
    const router = makeRouter();
    const wrapper = mount(ResearchStartPanel, { global: { plugins: [router] } });
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(literatureSearchApi.parseQuery).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请先输入");
  });
});
