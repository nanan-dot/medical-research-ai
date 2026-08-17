import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("pdfjs-dist/legacy/build/pdf.mjs", () => {
  class TextLayer {
    container: HTMLElement;
    constructor(options: { container: HTMLElement }) { this.container = options.container; }
    async render(): Promise<void> {
      const span = document.createElement("span");
      span.textContent = "研究对象";
      this.container.append(span);
    }
  }
  return {
    GlobalWorkerOptions: {},
    TextLayer,
    getDocument: () => ({
      destroy: vi.fn(),
      promise: Promise.resolve({
        numPages: 1,
        getPage: async () => ({
          getViewport: () => ({ width: 400, height: 600, scale: 1.25 }),
          render: () => ({ promise: Promise.resolve() }),
          getTextContent: async () => ({}),
        }),
      }),
    }),
  };
});

import PdfAnnotationReader from "./PdfAnnotationReader.vue";

afterEach(() => {
  window.getSelection()?.removeAllRanges();
  delete (window.Range.prototype as { getClientRects?: () => unknown }).getClientRects;
  vi.restoreAllMocks();
});

describe("PdfAnnotationReader", () => {
  it("captures a browser text selection and emits a same-page annotation anchor", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, {
      props: { sourceUrl: "/api/v1/documents/7/original", annotations: [], selectedAnnotationId: null },
      attachTo: document.body,
    });
    await flushPromises();

    const page = wrapper.get("[data-page-number='1']").element;
    vi.spyOn(page, "getBoundingClientRect").mockReturnValue({ left: 0, top: 0, width: 400, height: 600 } as DOMRect);
    const textNode = wrapper.get(".text-layer span").element.firstChild!;
    const range = document.createRange();
    range.selectNode(textNode);
    Object.defineProperty(window.Range.prototype, "getClientRects", { configurable: true, value: () => [{ left: 40, top: 60, width: 120, height: 20 }] });
    const browserSelection = window.getSelection()!;
    browserSelection.removeAllRanges();
    browserSelection.addRange(range);
    expect(browserSelection.toString()).toBe("研究对象");
    document.dispatchEvent(new Event("selectionchange"));
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.emitted("selectionChange")).toContainEqual([{
      pageNumber: 1,
      selectedText: "研究对象",
      rectangles: [{ left: .1, top: .1, width: .3, height: 20 / 600 }],
    }]);
    expect(wrapper.text()).toContain("已记录选中文字，可在右侧批注中保存。");
    wrapper.unmount();
  });
});
