import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PdfPageShell from "./PdfPageShell.vue";

describe("PdfPageShell", () => {
  it("renders the frozen exact selection independently from browser native highlighting", () => {
    const wrapper = mount(PdfPageShell, {
      props: {
        pageNumber: 1,
        width: 800,
        height: 1000,
        annotations: [],
        selectedAnnotationId: null,
        selectionRectangles: [
          { left: 0.1, top: 0.2, width: 0.5, height: 0.02 },
        ],
      },
    });

    expect(wrapper.findAll(".selection-highlight")).toHaveLength(1);
    expect(wrapper.find(".selection-highlight").attributes("style")).toContain(
      "top: 20%",
    );
  });
});
