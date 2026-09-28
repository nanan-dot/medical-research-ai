import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StrategyTermsPanel from "./StrategyTermsPanel.vue";

describe("StrategyTermsPanel", () => {
  it("adds a user term and exposes lock, delete and remap actions", async () => {
    const wrapper = mount(StrategyTermsPanel, {
      props: {
        terms: [{ id: 4, concept_group: "disease", text: "interstitial lung disease", source: "research_question", field_tag: null, relation_type: null, is_locked: false, warning: null }],
        loading: false,
        error: null,
      },
    });

    const inputs = wrapper.findAll("input");
    await inputs[0].setValue("pulmonary fibrosis");
    await inputs[1].setValue("disease");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("add")).toEqual([[{ text: "pulmonary fibrosis", conceptGroup: "disease" }]]);
    await wrapper.get(".term-actions button").trigger("click");
    expect(wrapper.emitted("lock")).toEqual([[4, true]]);
    await wrapper.get(".panel-header button").trigger("click");
    expect(wrapper.emitted("remap")).toHaveLength(1);
  });
});
