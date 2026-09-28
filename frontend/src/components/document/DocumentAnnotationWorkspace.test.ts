import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentAnnotationWorkspace from "./DocumentAnnotationWorkspace.vue";

const documentRecord = {
  id: 7,
  knowledge_source_id: 1,
  file_path: "paper.pdf",
  original_filename: "paper.pdf",
  media_type: "application/pdf",
  file_hash: "a".repeat(64),
  file_size: 512,
  modified_time: "2026-08-10T00:00:00Z",
  scan_state: "pending" as const,
  parse_status: "succeeded" as const,
  index_status: "outdated" as const,
  error_code: null,
  error_message: null,
  retry_count: 0,
  started_at: null,
  finished_at: null,
  parsed_is_scanned: true,
};

afterEach(() => vi.unstubAllGlobals());

describe("DocumentAnnotationWorkspace", () => {
  it("saves a real selected text anchor and reloads returned annotations", async () => {
    const annotation = {
      id: 3,
      document_id: 7,
      file_hash: "a".repeat(64),
      page_number: 1,
      rectangles: [{ left: 0.1, top: 0.2, width: 0.3, height: 0.04 }],
      selected_text: "研究对象",
      selected_text_hash: "b".repeat(64),
      color: "yellow",
      note: null,
      version_status: "current",
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("reading-notes")) return Promise.resolve(new Response(JSON.stringify([])));
      if (init?.method === "POST") return Promise.resolve(new Response(JSON.stringify(annotation), { status: 201 }));
      return Promise.resolve(new Response(JSON.stringify([annotation])));
    });
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(DocumentAnnotationWorkspace, {
      props: { document: documentRecord, sourceUrl: "/api/v1/documents/7/original", summary: null, actionLoading: false },
      global: {
        stubs: {
          PdfAnnotationReader: {
            emits: ["selectionChange"],
            template: "<button class='select-text' @click=\"$emit('selectionChange', { pageNumber: 1, rectangles: [{ left: .1, top: .2, width: .3, height: .04 }], selectedText: '研究对象' })\">选择文本</button>",
          },
        },
      },
    });
    await flushPromises();

    await wrapper.get('[role="tab"][aria-controls="document-annotations-panel"]').trigger("click");
    await wrapper.get(".select-text").trigger("click");
    await wrapper.get(".save-button").trigger("click");
    await flushPromises();

    const annotationCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/annotations") && (init as RequestInit | undefined)?.method === "POST");
    expect(annotationCall).toBeDefined();
    const requestBody = JSON.parse(String((annotationCall?.[1] as RequestInit).body));
    expect(requestBody).toMatchObject({
      expected_file_hash: "a".repeat(64),
      page_number: 1,
      selected_text: "研究对象",
    });
    expect(wrapper.text()).toContain("研究对象");
  });

  it("keeps the captured PDF selection after switching to the annotation tab", async () => {
    const wrapper = mount(DocumentAnnotationWorkspace, {
      props: { document: documentRecord, sourceUrl: "/api/v1/documents/7/original", summary: null, actionLoading: false },
      global: { stubs: { PdfAnnotationReader: { emits: ["selectionChange"], template: "<button class='select-text' @click=\"$emit('selectionChange', { pageNumber: 1, rectangles: [{ left: .1, top: .2, width: .3, height: .04 }], selectedText: '研究对象' })\">选择文本</button>" } } },
    });
    await flushPromises();
    await wrapper.get(".select-text").trigger("click");
    await wrapper.get('[role="tab"][aria-controls="document-annotations-panel"]').trigger("click");
    expect(wrapper.text()).toContain("第 1 页：研究对象");
    expect(wrapper.get(".save-button").attributes("disabled")).toBeUndefined();
  });
});
