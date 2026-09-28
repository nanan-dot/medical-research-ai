import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { router as applicationRouter } from "../../router";
import SearchEntryView from "./SearchEntryView.vue";

test("AC-ENTRY-02 keeps the previous workspace on its dedicated route", () => {
  expect(applicationRouter.resolve("/literature-search/workspace").matched).toHaveLength(1);
  expect(applicationRouter.resolve("/literature-search/workspace").matched[0]?.path).toBe("/literature-search/workspace");
});

test("AC-ENTRY-12 restores only the URL-persisted raw topic after refresh", async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/literature-search", component: SearchEntryView },
      { path: "/literature-search/history", component: { template: "<div />" } },
      { path: "/literature-search/workspace", component: { template: "<div />" } },
    ],
  });
  await router.push("/literature-search?raw_topic=%E8%83%83%E7%99%8C");
  await router.isReady();
  const wrapper = mount(SearchEntryView, { global: { plugins: [router] } });

  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("胃癌");
  expect(wrapper.get('input[value="auto"]').element).toBeTruthy();
});

test("AC-ENTRY-13 preserves history and result deep links", () => {
  expect(applicationRouter.resolve("/literature-search/history").matched[0]?.path).toBe("/literature-search/history");
  expect(applicationRouter.resolve("/literature-search/results/201?task=7&from=history").matched[0]?.path).toBe("/literature-search/results/:id");
});

test("AC-ENTRY-15 keeps the mobile entry route resolvable without a second shell", () => {
  expect(applicationRouter.resolve("/literature-search").matched[0]?.path).toBe("/literature-search");
});
