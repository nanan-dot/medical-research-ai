import { flushPromises, mount } from "@vue/test-utils";
import { expect, test } from "vitest";
import App from "../App.vue";
import { router } from "./index";

test("routes through the workbench and preserves URL state", async () => {
  await router.push("/");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  expect(wrapper.text()).toContain("跳到主要内容");
  expect(wrapper.text()).toContain("你的医学科研工作空间");
  await router.push("/feedback");
  await flushPromises();
  expect(wrapper.text()).toContain("匿名试用反馈");
  expect(router.currentRoute.value.fullPath).toBe("/feedback");
});
