import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { DocumentRecord } from "../../api/documents";
import DocumentDetailsDrawer from "./DocumentDetailsDrawer.vue";

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
  it("exposes a modal dialog and closes through the backdrop", async () => {
    const wrapper = mountDrawer();

    expect(document.querySelector('[role="dialog"]')?.getAttribute("aria-modal")).toBe("true");
    await document.querySelector<HTMLButtonElement>(".backdrop")!.click();

    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });

  it("closes with Escape without invoking document actions", async () => {
    const wrapper = mountDrawer();
    const drawer = document.querySelector<HTMLElement>(".drawer")!;

    await drawer.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(wrapper.emitted("retryParse")).toBeUndefined();
    expect(wrapper.emitted("retryIndex")).toBeUndefined();
    wrapper.unmount();
  });
});
