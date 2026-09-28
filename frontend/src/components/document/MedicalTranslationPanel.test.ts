import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import MedicalTranslationPanel from "./MedicalTranslationPanel.vue";
import type { PdfTextSelection } from "../../types/documentAnnotations";

const documentRecord = {
  id: 7, knowledge_source_id: 1, file_path: "paper.pdf", original_filename: "paper.pdf", media_type: "application/pdf",
  file_hash: "a".repeat(64), file_size: 512, modified_time: "2026-08-10T00:00:00Z", scan_state: "pending" as const,
  parse_status: "succeeded" as const, index_status: "outdated" as const, error_code: null, error_message: null,
  retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false,
};

function selection(text: string, item = 0): PdfTextSelection {
  return {
    pageNumber: 1,
    rectangles: [{ left: .1, top: .2, width: .3, height: .04 }],
    selectedText: text,
    anchorDescriptor: {
      expected_file_hash: "a".repeat(64), expected_anchor_revision_id: 2, expected_segmentation_revision_id: 3,
      browser_quote: text,
      fragments: [{ page_number: 1, start_item_index: item, start_offset_utf16: 0, end_item_index: item, end_offset_utf16: text.length, rectangles: [] }],
    },
  };
}

function job(id: number, revisionId: number) {
  return { id, task_id: id + 10, document_id: 7, source_anchor_id: id + 20, state: "succeeded", source_language: "en", target_language: "zh-CN", attempt_count: 1, result_revision_id: revisionId, error_code: null, error_message: null, created_at: "2026-09-01T00:00:00Z", finished_at: "2026-09-01T00:00:01Z" };
}

function revision(id: number, text: string, blocked = false) {
  return { id, document_id: 7, source_anchor_id: 27, version: 1, origin: "machine", source_language: "en", target_language: "zh-CN", translated_text: text, alignment: [{ source_start: 0, source_end: 9, target_start: 0, target_end: text.length }], terms: [{ source_term: "XYZ", target_term: null, status: "unresolved", provenance: "phase1-local-rule", version: "v1", authority: null, source_span: [0, 3] }], issues: blocked ? [{ code: "DOSE_MISMATCH", severity: "critical", blocking: true, message: "剂量发生变化", source_span: [5, 9], target_span: [4, 9] }] : [], quality_status: blocked ? "blocked" : "needs_review", provider: "fake", model: "test", created_at: "2026-09-01T00:00:01Z" };
}

afterEach(() => vi.unstubAllGlobals());

describe("MedicalTranslationPanel", () => {
  it("shows aligned result, terminology evidence, blocking issues and correction controls", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      return Promise.resolve(new Response(JSON.stringify(url.includes("translation-revisions") ? revision(31, "剂量为 50 mg", true) : job(1, 31)), { status: url.includes("translation-revisions") ? 200 : 202 }));
    }));
    const wrapper = mount(MedicalTranslationPanel, { props: { document: documentRecord, selection: selection("Dose 5 mg") } });
    await wrapper.get(".primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("剂量为 50 mg");
    expect(wrapper.text()).toContain("1 项阻断");
    expect(wrapper.text()).toContain("1 项待确认");
    await wrapper.get(".text-action").trigger("click");
    expect(wrapper.get("label[for='translation-correction']").text()).toContain("人工修订译文");
  });

  it("does not let a slow old selection overwrite the latest selection", async () => {
    let releaseOld: ((value: Response) => void) | undefined;
    const oldResponse = new Promise<Response>((resolve) => { releaseOld = resolve; });
    let postCount = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST" && url.includes("translation-jobs")) {
        postCount += 1;
        return postCount === 1 ? oldResponse : Promise.resolve(new Response(JSON.stringify(job(2, 42)), { status: 202 }));
      }
      if (url.endsWith("/42")) return Promise.resolve(new Response(JSON.stringify(revision(42, "最新选区译文"))));
      if (url.endsWith("/41")) return Promise.resolve(new Response(JSON.stringify(revision(41, "旧选区译文"))));
      throw new Error(`unexpected ${url}`);
    }));
    const wrapper = mount(MedicalTranslationPanel, { props: { document: documentRecord, selection: selection("old", 0) } });
    await wrapper.get(".primary").trigger("click");
    await wrapper.setProps({ selection: selection("new", 1) });
    await wrapper.get(".primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("最新选区译文");
    releaseOld?.(new Response(JSON.stringify(job(1, 41)), { status: 202 }));
    await flushPromises();
    expect(wrapper.text()).toContain("最新选区译文");
    expect(wrapper.text()).not.toContain("旧选区译文");
  });
});
