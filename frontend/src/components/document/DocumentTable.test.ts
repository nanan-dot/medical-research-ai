import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ResourceLibraryItem } from "../../api/resourceLibrary";
import DocumentTable from "./DocumentTable.vue";

function item(status: ResourceLibraryItem["status"], overrides: Partial<ResourceLibraryItem> = {}): ResourceLibraryItem {
  return {
    id: 1,
    knowledge_source_id: 2,
    file_path: "trials/protocol.docx",
    original_filename: "protocol.docx",
    file_type: "docx",
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_hash: "hash-1",
    file_size: 128,
    modified_time: "2026-08-13T08:00:00Z",
    scan_state: "pending",
    parse_status: "succeeded",
    index_status: "succeeded",
    parsed_is_scanned: false,
    error_code: null,
    error_message: null,
    retry_count: 0,
    started_at: null,
    finished_at: null,
    source_name: "临床试验",
    source_type: "local_folder",
    relative_path: "trials/protocol.docx",
    display_name: "protocol.docx",
    task_status: null,
    phase: null,
    current_item: null,
    last_opened_at: null,
    open_count: 0,
    status,
    match_fields: [],
    snippet: null,
    locator: null,
    ...overrides,
  };
}

describe("DocumentTable", () => {
  it("uses the resource status mapping instead of parsing a backend error message", () => {
    const wrapper = mount(DocumentTable, {
      props: {
        documents: [item("ai_available"), item("needs_attention", { id: 2, error_code: "parse_failed", error_message: "stack trace" }), item("outdated", { id: 3 })],
        disabled: false,
        selectedIds: [],
        selectedDocumentId: null,
      },
    });

    expect(wrapper.text()).toContain("AI 可使用");
    expect(wrapper.text()).toContain("解析和索引完成");
    expect(wrapper.text()).toContain("解析失败");
    expect(wrapper.text()).toContain("内容已更新");
    expect(wrapper.text()).not.toContain("stack trace");
  });

  it("uses semantic table selection for only the current page", async () => {
    const wrapper = mount(DocumentTable, {
      props: { documents: [item("ai_available"), item("processing", { id: 2 })], disabled: false, selectedIds: [], selectedDocumentId: null },
    });

    expect(wrapper.find("table").exists()).toBe(true);
    expect(wrapper.find('input[aria-label="选择当前页全部资料"]').exists()).toBe(true);
    await wrapper.get('input[aria-label="选择当前页全部资料"]').setValue(true);
    expect(wrapper.emitted("toggleSelect")).toEqual([[1, true], [2, true]]);
  });

  it("never invents a processing percentage when the API omits it", () => {
    const wrapper = mount(DocumentTable, {
      props: { documents: [item("processing", { phase: "建立索引", progress: null })], disabled: false, selectedIds: [], selectedDocumentId: null },
    });

    expect(wrapper.text()).toContain("处理中");
    expect(wrapper.text()).not.toMatch(/\d+%/);
  });

  it("closes an action menu with Escape and returns focus to its trigger", async () => {
    const wrapper = mount(DocumentTable, {
      attachTo: document.body,
      props: { documents: [item("ai_available")], disabled: false, selectedIds: [], selectedDocumentId: null },
    });
    const trigger = wrapper.get('button[aria-label="更多操作 protocol.docx"]');

    await trigger.trigger("click");
    await trigger.trigger("keydown", { key: "Escape" });

    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
    wrapper.unmount();
  });
});
