import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import AppSidebar from "./AppSidebar.vue";

async function mountSidebar(initialPath = "/sources") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/sources", component: { template: "<div />" } },
      { path: "/papers", component: { template: "<div />" } },
      { path: "/paper-research/:paperItemId?", component: { template: "<div />" } },
      { path: "/notes", component: { template: "<div />" } },
      { path: "/documents", component: { template: "<div />" } },
      { path: "/literature-search", component: { template: "<div />" } },
      {
        path: "/literature-search/workspace",
        component: { template: "<div />" },
      },
      {
        path: "/literature-search/history",
        component: { template: "<div />" },
      },
      {
        path: "/literature-search/results",
        component: { template: "<div />" },
      },
      {
        path: "/literature-search/results/:id",
        component: { template: "<div />" },
      },
      { path: "/recommendations", component: { template: "<div />" } },
      { path: "/comparisons", component: { template: "<div />" } },
      { path: "/research-directions", component: { template: "<div />" } },
      { path: "/writing", component: { template: "<div />" } },
      { path: "/tasks", component: { template: "<div />" } },
      { path: "/models", component: { template: "<div />" } },
      { path: "/", component: { template: "<div />" } },
    ],
  });
  await router.push(initialPath);
  await router.isReady();
  return mount(AppSidebar, {
    props: { collapsed: false },
    global: { plugins: [router] },
  });
}

describe("AppSidebar", () => {
  it("preserves every real first-level destination", async () => {
    const wrapper = await mountSidebar("/");
    expect(wrapper.findAll(".nav > .nav-link .nav-label, .nav-group-heading .nav-label").map((item) => item.text())).toEqual([
      "工作台",
      "文献检索",
      "研究资源",
      "论文研究",
      "多论文证据",
      "研究设计",
      "写作与汇报",
    ]);
  });

  it("restores all literature-search secondary destinations", async () => {
    const wrapper = await mountSidebar("/literature-search");
    expect(wrapper.get("button[aria-controls='literature-subnav']").attributes("aria-expanded")).toBe("true");
    const links = wrapper.findAll("#literature-subnav a");
    expect(links.map((link) => link.attributes("href"))).toEqual([
      "/literature-search",
      "/literature-search/results",
      "/recommendations",
      "/literature-search/history",
    ]);
    expect(links.map((link) => link.text())).toEqual(["检索中心", "检索结果", "文献推荐", "检索历史"]);
  });

  it("keeps every real research-resource secondary destination", async () => {
    const wrapper = await mountSidebar("/papers");
    const resourceLinks = wrapper.findAll("#resource-subnav a");
    expect(resourceLinks.map((link) => link.attributes("href"))).toEqual([
      "/sources",
      "/papers",
      "/notes",
      "/documents",
    ]);
    expect(
      wrapper.get("a[href='/papers']").attributes("aria-current"),
    ).toBe("page");
  });

  it("keeps every destination keyboard-accessible when collapsed", async () => {
    const wrapper = await mountSidebar("/literature-search");

    await wrapper.setProps({ collapsed: true });
    expect(wrapper.find("#literature-subnav").exists()).toBe(false);
    const literatureLink = wrapper.get("a[href='/literature-search']");
    expect(literatureLink.attributes("aria-label")).toBe("文献检索");
    expect(literatureLink.attributes("data-tooltip")).toBe("文献检索");
    expect(wrapper.get(".collapse-btn").attributes("aria-label")).toBe(
      "展开导航",
    );

    await wrapper.setProps({ collapsed: false });
    expect(literatureLink.attributes("aria-label")).toBeUndefined();
  });
});
