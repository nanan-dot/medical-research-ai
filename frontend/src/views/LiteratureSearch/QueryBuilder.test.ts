import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import QueryBuilder from "./QueryBuilder.vue";

const candidate = {
  topic: "胃癌",
  disease: "胃癌",
  intervention: null,
  target: null,
  mechanism: null,
  date_range: { start_year: 2024, end_year: 2026, original_expression: "近三年" },
  study_types: [],
  language: [],
  exclusions: [],
  retmax: 50,
};

test("keeps an explicit user edit in the emitted candidate", async () => {
  const wrapper = mount(QueryBuilder, { props: { candidate } });
  await wrapper.get('input[type="number"]').setValue("100");
  await wrapper.get('input[type="number"]').trigger("change");

  const updates = wrapper.emitted("updateCandidate");
  expect(updates?.at(-1)?.[0]).toEqual(expect.objectContaining({ retmax: 100 }));
  expect(wrapper.text()).toContain("不是最终检索式");
});
