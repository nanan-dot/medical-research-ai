import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentInspector from "./DocumentInspector.vue";

describe("DocumentInspector", () => {
  it("shows the selected document's real source, status, and error context", () => {
    const wrapper = mount(DocumentInspector, {
      props: {
        sourceName: "临床肿瘤资料", scopeName: "临床肿瘤资料", total: 1,
        document: { id: 3, knowledge_source_id: 8, file_path: "trial/protocol.pdf", original_filename: "protocol.pdf", media_type: "application/pdf", file_hash: "hash", file_size: 88, modified_time: "2026-08-01T00:00:00Z", scan_state: "outdated", parse_status: "failed", index_status: "outdated", error_code: "parse_failed", error_message: "解析器返回错误", retry_count: 1, started_at: null, finished_at: null, parsed_is_scanned: null },
      },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("临床肿瘤资料 / trial/protocol.pdf");
    expect(wrapper.text()).toContain("失败");
    expect(wrapper.get(".error-context").text()).toContain("解析器返回错误");
  });

  it("uses a scope-aware empty state before a document is selected", () => {
    const wrapper = mount(DocumentInspector, {
      props: {
        document: null,
        scopeName: "临床试验",
        sourceName: null,
        total: 3,
      },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    expect(wrapper.text()).toContain("资料详情");
    expect(wrapper.text()).toContain("临床试验");
    expect(wrapper.text()).toContain("3 份");
  });
});
