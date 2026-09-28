import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import BilingualTranslationView from "./BilingualTranslationView.vue";

const revision = {
  source_anchor_id: 9,
  translated_text: "剂量为 5 mg。",
  alignment: [{ source_start: 0, source_end: 9, target_start: 0, target_end: 10 }],
};

describe("BilingualTranslationView", () => {
  it("keeps a separate aligned source/translation view and emits a precise-anchor locate action", async () => {
    const wrapper = mount(BilingualTranslationView, { props: { sourceQuote: "Dose 5 mg", revision, mode: "bilingual" } });
    expect(wrapper.text()).toContain("Dose 5 mg");
    expect(wrapper.text()).toContain("剂量为 5 mg");
    await wrapper.get(".source-cell").trigger("click");
    expect(wrapper.emitted("locate")).toHaveLength(1);
  });

  it("disables precise locating when the provider has no usable alignment", () => {
    const wrapper = mount(BilingualTranslationView, { props: { sourceQuote: "Dose 5 mg", revision: { ...revision, alignment: [] }, mode: "bilingual" } });
    expect(wrapper.get(".source-cell").attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("缺少精确句级对齐");
  });
});
