import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentPreviewPanel from "./DocumentPreviewPanel.vue";

describe("DocumentPreviewPanel", () => {
  it("loads a PDF only from the controlled preview URL", () => {
    const wrapper = mount(DocumentPreviewPanel, {
      props: {
        loading: false,
        errorMessage: null,
        document: null,
        preview: {
          document_id: 9,
          kind: "pdf",
          content_url: "/api/v1/documents/9/original",
          blocks: [],
          tables: [],
          message: null,
        },
      },
    });

    const iframe = wrapper.get("iframe");
    expect(iframe.attributes("src")).toBe("/api/v1/documents/9/original");
    expect(iframe.attributes("sandbox")).toBeDefined();
  });

  it("renders DOCX text as escaped interpolation rather than HTML", () => {
    const wrapper = mount(DocumentPreviewPanel, {
      props: {
        loading: false,
        errorMessage: null,
        document: null,
        preview: {
          document_id: 10,
          kind: "docx",
          content_url: null,
          blocks: [{ kind: "paragraph", text: "<img src=x onerror=alert(1)>", level: null }],
          tables: [],
          message: null,
        },
      },
    });

    expect(wrapper.html()).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(wrapper.find("img").exists()).toBe(false);
  });
});
