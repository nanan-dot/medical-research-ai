import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ReaderRecordsModal from "./ReaderRecordsModal.vue";

const records = [
  { record_id: "annotation:1", record_type: "annotation", source_anchor_id: 17, quote: "原文", text: "一条批注", page_number: 3, section_path: null, relocation_status: "resolved", created_at: "2026-09-03" },
  { record_id: "highlight:1", record_type: "highlight", source_anchor_id: 21, quote: "高亮原文", text: null, page_number: 4, section_path: null, relocation_status: "resolved", created_at: "2026-09-03" },
] as const;

afterEach(() => { document.body.innerHTML = ""; });

describe("ReaderRecordsModal", () => {
  it("shows only the selected category and emits a locatable record", async () => {
    const wrapper = mount(ReaderRecordsModal, { attachTo: document.body, props: { open: true, records, activeType: "annotation" } });
    expect(document.body.textContent).toContain("一条批注");
    expect(document.body.textContent).not.toContain("高亮原文");
    expect(document.body.querySelector(".record-row")?.getAttribute("role")).toBeNull();
    await document.body.querySelector<HTMLButtonElement>(".record-row")!.click();
    expect(wrapper.emitted("locate")?.[0]).toEqual([records[0]]);
  });

  it("closes via Escape and preserves the modal outside the panel flow", async () => {
    const wrapper = mount(ReaderRecordsModal, { attachTo: document.body, props: { open: true, records, activeType: null } });
    expect(document.body.querySelector(".records-overlay")).not.toBeNull();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
