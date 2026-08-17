import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { DocumentRecord } from "../../api/documents";
import DocumentTable from "./DocumentTable.vue";

const documents: DocumentRecord[] = [
  {
    id: 1,
    knowledge_source_id: 2,
    file_path: "trials/protocol.docx",
    original_filename: "protocol.docx",
    file_size: 128,
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_hash: "hash-1",
    modified_time: "2026-08-13T08:00:00Z",
    scan_state: "pending",
    parse_status: "succeeded",
    index_status: "outdated",
    parsed_is_scanned: false,
    error_code: null,
    error_message: null,
    retry_count: 0,
    started_at: null,
    finished_at: null,
  },
  {
    id: 2,
    knowledge_source_id: 2,
    file_path: "trials/failed.pdf",
    original_filename: "failed.pdf",
    file_size: 128,
    media_type: "application/pdf",
    file_hash: "hash-2",
    modified_time: "2026-08-13T08:00:00Z",
    scan_state: "pending",
    parse_status: "failed",
    index_status: "pending",
    parsed_is_scanned: false,
    error_code: "parse_failed",
    error_message: "解析服务暂不可用",
    retry_count: 0,
    started_at: null,
    finished_at: null,
  },
];

describe("DocumentTable", () => {
  it("uses actual file extensions and exposes real processing states", () => {
    const wrapper = mount(DocumentTable, {
      props: {
        documents,
        disabled: false,
        selectedDocumentId: null,
        selectedIds: [],
        sourceNames: { 2: "临床试验" },
      },
      global: {
        stubs: { RouterLink: { template: "<a><slot /></a>" } },
      },
    });

    expect(wrapper.text()).toContain("DOCX");
    expect(wrapper.text()).toContain("索引过期");
    expect(wrapper.text()).toContain("解析失败");
    expect(wrapper.text()).toContain("等待索引");
    expect(wrapper.text()).toContain("临床试验 / trials/protocol.docx");
  });
});
