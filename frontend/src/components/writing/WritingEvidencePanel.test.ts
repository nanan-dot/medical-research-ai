import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WritingEvidencePanel from "./WritingEvidencePanel.vue";

describe("WritingEvidencePanel", () => {
  it("reports unavailable when the active context has no documents", () => {
    const wrapper = mount(WritingEvidencePanel, {
      props: {
        references: [],
        contextDocumentIds: [],
        selectedSegmentId: "paragraph-1",
        isBusy: false,
      },
    });

    expect(wrapper.text()).toContain("UNAVAILABLE");
  });

  it("emits a real context document id when binding evidence", async () => {
    const wrapper = mount(WritingEvidencePanel, {
      props: {
        references: [],
        contextDocumentIds: [42],
        selectedSegmentId: "paragraph-1",
        isBusy: false,
      },
    });

    await wrapper.get(".document-button").trigger("click");
    expect(wrapper.emitted("bindDocument")).toEqual([[42]]);
  });
});
