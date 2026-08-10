import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentOcrPanel from "./DocumentOcrPanel.vue";

afterEach(() => vi.unstubAllGlobals());

describe("DocumentOcrPanel", () => {
  it("shows the real engine-unavailable task failure returned by the API", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("null"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({
          id: 5,
          document_id: 7,
          status: "failed",
          engine_name: "tesseract",
          engine_version: null,
          language: "eng",
          page_count: null,
          completed_pages: 0,
          failed_pages: 0,
          output_sha256: null,
          error_code: "ocr_engine_unavailable",
          error_message: "未在 PATH 中找到 tesseract",
          cancel_requested: false,
          created_at: "2026-08-10T00:00:00Z",
          started_at: null,
          finished_at: "2026-08-10T00:00:00Z",
          pages: [],
        }), { status: 202 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(DocumentOcrPanel, {
      props: { documentId: 7, isScanned: true },
    });
    await flushPromises();

    await wrapper.get(".actions button").trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/documents/7/ocr",
      expect.objectContaining({ method: "POST" }),
    );
    expect(wrapper.text()).toContain("未在 PATH 中找到 tesseract");
  });

  it("does not expose an OCR trigger for a text-layer PDF", async () => {
    const wrapper = mount(DocumentOcrPanel, {
      props: { documentId: 8, isScanned: false },
    });

    expect(wrapper.find(".ocr-panel").exists()).toBe(false);
  });
});
