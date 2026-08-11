import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import SearchReadinessPanel from "./SearchReadinessPanel.vue";

test("allows search when a real query is ready even if PICO remains incomplete", () => {
  const wrapper = mount(SearchReadinessPanel, {
    props: {
      topicFilled: true,
      sourceSelected: true,
      draftReady: true,
      taskLoading: false,
      taskError: null,
      hasCandidate: true,
    },
  });

  const button = wrapper.get(".primary-action").element as HTMLButtonElement;
  expect(button.disabled).toBe(false);
});
