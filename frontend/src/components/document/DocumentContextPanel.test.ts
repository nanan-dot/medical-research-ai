import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentContextPanel from "./DocumentContextPanel.vue";

const documentRecord = {
  id: 7, knowledge_source_id: 1, file_path: "paper.pdf", original_filename: "paper.pdf", media_type: "application/pdf",
  file_hash: "a".repeat(64), file_size: 512, modified_time: "2026-08-10T00:00:00Z", scan_state: "pending" as const,
  parse_status: "failed" as const, index_status: "outdated" as const, error_code: null, error_message: null,
  retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false,
};

function mountPanel() {
  return mount(DocumentContextPanel, {
    props: { document: documentRecord, summary: null, actionLoading: false, selection: null, annotations: [], annotationLoading: false, annotationSaving: false, annotationError: null, selectedAnnotationId: null },
  });
}

describe("DocumentContextPanel", () => {
  it("defaults to the information tab with accessible tab semantics and state actions", async () => {
    const wrapper = mountPanel();
    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs).toHaveLength(2);
    expect(tabs[0].attributes("aria-selected")).toBe("true");
    expect(wrapper.get('[role="tabpanel"]').attributes("id")).toBe("document-information-panel");
    await wrapper.get(".actions button").trigger("click");
    expect(wrapper.emitted("retryParse")).toHaveLength(1);
  });

  it("switches to the annotation tab by click and keyboard", async () => {
    const wrapper = mountPanel();
    const tabs = wrapper.findAll('[role="tab"]');
    await tabs[0].trigger("keydown", { key: "ArrowRight" });
    expect(tabs[1].attributes("aria-selected")).toBe("true");
    expect(wrapper.get('[role="tabpanel"]').attributes("id")).toBe("document-annotations-panel");
    expect(wrapper.text()).toContain("请先在 PDF 文本层选中一段文字。");
  });
});
