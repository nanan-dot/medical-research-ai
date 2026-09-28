import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";
import { routeMeta } from "../../router/route-meta";
import Breadcrumbs from "./Breadcrumbs.vue";

describe("Breadcrumbs", () => {
  it("links only the confirmed resource-library ancestors", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/documents", component: { template: "<div />" } }, {
        path: "/documents/:id",
        component: { template: "<div />" },
        meta: { breadcrumb: ["\u7814\u7a76\u8d44\u6e90", "\u8d44\u6599\u5e93", "\u8d44\u6599\u8be6\u60c5"] } as never,
      }],
    });
    await router.push("/documents/42");
    await router.isReady();

    const wrapper = mount(Breadcrumbs, { global: { plugins: [router] } });

    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual(["/documents", "/documents"]);
    expect(wrapper.get("strong").text()).toBe("\u8d44\u6599\u8be6\u60c5");
  });

  it("renders history-origin results with accessible workspace and history links", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: "/literature-search", component: { template: "<div />" } },
      { path: "/literature-search/history", component: { template: "<div />" } },
      { path: "/literature-search/results/:id", component: { template: "<div />" }, meta: routeMeta("/literature-search/results") },
    ] });
    await router.push("/literature-search/results/101?task=7&from=history");
    await router.isReady();

    const wrapper = mount(Breadcrumbs, { global: { plugins: [router] } });

    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual(["/literature-search", "/literature-search/history"]);
    expect(wrapper.get("strong").text()).toBe("搜索结果");
    expect(wrapper.get("strong").attributes("aria-current")).toBe("page");
    expect(wrapper.findAll("a").every((link) => link.element.tabIndex >= 0)).toBe(true);
  });

  it.each(["", "?from=other", "?from=history&from=other"])("safely degrades results breadcrumbs for invalid origin %s", async (query) => {
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: "/literature-search", component: { template: "<div />" } },
      { path: "/literature-search/results/:id", component: { template: "<div />" }, meta: routeMeta("/literature-search/results") },
    ] });
    await router.push(`/literature-search/results/101${query}`);
    await router.isReady();

    const wrapper = mount(Breadcrumbs, { global: { plugins: [router] } });

    expect(wrapper.text()).toContain("结果展示");
    expect(wrapper.text()).not.toContain("历史记录");
    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual(["/literature-search"]);
  });
});
