import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentAnnotationEditor from "./DocumentAnnotationEditor.vue";

const selection = {
  pageNumber: 2,
  rectangles: [{ left: 0.1, top: 0.2, width: 0.3, height: 0.05 }],
  selectedText: "研究对象",
};

describe("DocumentAnnotationEditor", () => {
  it("does not save before a text selection exists", async () => {
    const wrapper = mount(DocumentAnnotationEditor, {
      props: { selection: null, saving: false },
    });

    expect(wrapper.get(".save-button").attributes("disabled")).toBeDefined();
    await wrapper.get(".save-button").trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("emits the selected geometry and trimmed note", async () => {
    const wrapper = mount(DocumentAnnotationEditor, {
      props: { selection, saving: false },
    });

    await wrapper.get("textarea").setValue("  需要复核  ");
    await wrapper.get("select").setValue("blue");
    await wrapper.get(".save-button").trigger("click");

    expect(wrapper.emitted("submit")).toEqual([[
      { selection, color: "blue", note: "需要复核" },
    ]]);
  });
});
