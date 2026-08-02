import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import LiteratureSearchView from "./LiteratureSearchView.vue";

afterEach(() => vi.restoreAllMocks());

test("shows raw topic, rule fallback, and editable candidate", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        raw_topic: "胃癌",
        candidate_source: "rule_fallback",
        prompt_version: "search-intent-v1",
        clarification_questions: ["需要限定发表时间范围吗？"],
        candidate: {
          topic: "胃癌", disease: "胃癌", intervention: null, target: null, mechanism: null,
          date_range: null, study_types: [], language: [], exclusions: [], retmax: 50,
        },
      }),
    }),
  );
  const wrapper = mount(LiteratureSearchView);
  await wrapper.get("input[required]").setValue("胃癌");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("原始主题：胃癌");
  expect(wrapper.text()).toContain("规则候选");
  expect(wrapper.text()).toContain("可编辑检索条件");
});
