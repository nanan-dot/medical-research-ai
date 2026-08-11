import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";
import Breadcrumbs from "./Breadcrumbs.vue";

describe("Breadcrumbs", () => {
  it("links only the confirmed document-library ancestors", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/documents", component: { template: "<div />" } }, {
        path: "/documents/:id",
        component: { template: "<div />" },
        meta: { breadcrumb: ["\u6587\u6863\u4e0e\u77e5\u8bc6", "\u6587\u6863\u5e93", "\u6587\u6863\u8be6\u60c5"] } as never,
      }],
    });
    await router.push("/documents/42");
    await router.isReady();

    const wrapper = mount(Breadcrumbs, { global: { plugins: [router] } });

    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual(["/documents", "/documents"]);
    expect(wrapper.get("strong").text()).toBe("\u6587\u6863\u8be6\u60c5");
  });
});