import { flushPromises, mount } from "@vue/test-utils";
import { expect, test } from "vitest";
import App from "../App.vue";
import { router } from "./index";

test("routes through the workbench and preserves URL state", async () => {
  await router.push("/");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  expect(wrapper.text()).toContain("跳到主要内容");
  expect(wrapper.text()).toContain("研究起点");
  // 顶部栏上下文跟随当前一级工作空间：工作台页显示"工作台"（动态 label）。
  expect(wrapper.text()).toContain("工作台");
  await router.push("/feedback");
  await flushPromises();
  expect(wrapper.text()).toContain("匿名试用反馈");
  expect(router.currentRoute.value.fullPath).toBe("/feedback");
});
