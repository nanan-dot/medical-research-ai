import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DocumentRecord } from "../../api/documents";
import DocumentDetailsDrawer from "./DocumentDetailsDrawer.vue";

const { getPreview } = vi.hoisted(() => ({ getPreview: vi.fn() }));

vi.mock("../../api/documentPreviews", () => ({
  documentPreviewsApi: { get: getPreview },
}));

const documentRecord: DocumentRecord = {
  id: 9,
  knowledge_source_id: 2,
  file_path: "trial/protocol.pdf",
  original_filename: "protocol.pdf",
  media_type: "application/pdf",
  file_hash: "hash",
  file_size: 1024,
  modified_time: "2026-08-01T00:00:00Z",
  scan_state: "pending",
  parse_status: "succeeded",
  index_status: "succeeded",
  parsed_is_scanned: false,
  error_code: null,
  error_message: null,
  retry_count: 0,
  started_at: null,
  finished_at: null,
  health_status: "available",
  health_reason: "已建立问答索引",
};

function mountDrawer() {
  return mount(DocumentDetailsDrawer, {
    attachTo: document.body,
    props: {
      document: documentRecord,
      disabled: false,
      sourceName: "临床试验",
      scopeName: "临床试验",
      total: 1,
    },
    global: {
      stubs: {
        RouterLink: { template: "<a><slot /></a>" },
      },
    },
  });
}

describe("DocumentDetailsDrawer", () => {
  beforeEach(() => {
    getPreview.mockResolvedValue({ document_id: 9, kind: "unavailable", content_url: null, blocks: [], tables: [], message: "该文件暂不支持在线预览。" });
  });

  it("exposes a modal dialog and closes through the backdrop", async () => {
    const wrapper = mountDrawer();
    await nextTick();

    expect(document.querySelector('[role="dialog"]')?.getAttribute("aria-modal")).toBe("true");
    expect(document.querySelector('[role="dialog"]')?.getAttribute("aria-labelledby")).toBe("resource-details-title");
    expect(document.activeElement?.id).toBe("resource-details-title");
    await Promise.resolve();
    expect(document.body.textContent).toContain("暂不支持预览");
    await document.querySelector<HTMLButtonElement>(".backdrop")!.click();

    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });

  it("closes with Escape without invoking document actions", async () => {
    const wrapper = mountDrawer();
    await nextTick();
    const drawer = document.querySelector<HTMLElement>(".drawer")!;

    await drawer.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(wrapper.emitted("retryParse")).toBeUndefined();
    expect(wrapper.emitted("retryIndex")).toBeUndefined();
    wrapper.unmount();
  });
});
