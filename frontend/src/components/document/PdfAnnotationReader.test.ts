import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const pdfFixture = vi.hoisted(() => ({
  pageCount: 1,
  rendered: [] as number[],
  holdNext: false,
  failNext: false,
  cancelled: vi.fn(),
  textLayerHold: false,
  textLayerCancelled: vi.fn(),
  mappingHold: false,
  mappingCancelled: vi.fn(),
}));
vi.mock("../../api/readingSegments", () => ({ readPageSegments: async () => [] }));

function intersection(target: HTMLElement, isIntersecting: boolean): IntersectionObserverEntry {
  return { target, isIntersecting, intersectionRatio: isIntersecting ? 1 : 0, time: 0,
    boundingClientRect: target.getBoundingClientRect(), intersectionRect: target.getBoundingClientRect(), rootBounds: null };
}

vi.mock("pdfjs-dist/legacy/build/pdf.mjs", () => {
  class TextLayer {
    container: HTMLElement;
    textDivs: HTMLElement[] = [];
    textContentItemsStr = ["研究对象"];
    private rejectRender: ((cause: Error) => void) | null = null;
    constructor(options: { container: HTMLElement }) { this.container = options.container; }
    async render(): Promise<void> {
      if (pdfFixture.textLayerHold) {
        pdfFixture.textLayerHold = false;
        return new Promise<void>((_resolve, reject) => { this.rejectRender = reject; });
      }
      const span = document.createElement("span");
      span.textContent = "研究对象";
      this.container.append(span);
      this.textDivs.push(span);
    }
    cancel(): void {
      pdfFixture.textLayerCancelled();
      this.rejectRender?.(new Error("RenderingCancelledException"));
    }
  }
  return {
    GlobalWorkerOptions: {},
    version: "6.2.108",
    TextLayer,
    getDocument: () => ({
      destroy: vi.fn(),
      promise: Promise.resolve({
        numPages: pdfFixture.pageCount,
        getPage: async (page: number) => ({
          getViewport: ({ scale }: { scale: number }) => ({ width: 320 * scale, height: 480 * scale, scale, rotation: 0 }),
          render: () => {
            pdfFixture.rendered.push(page);
            if (pdfFixture.failNext) {
              pdfFixture.failNext = false;
              return { promise: Promise.reject(new Error("合成页失败")), cancel: vi.fn() };
            }
            if (pdfFixture.holdNext) {
              pdfFixture.holdNext = false;
              let rejectRender!: (cause: Error) => void;
              return { promise: new Promise<void>((_resolve, reject) => { rejectRender = reject; }),
                cancel: () => { pdfFixture.cancelled(); rejectRender(new Error("RenderingCancelledException")); } };
            }
            return { promise: Promise.resolve(), cancel: vi.fn() };
          },
          getTextContent: async () => ({ items: [{ str: "研究对象" }] }),
        }),
      }),
    }),
  };
});

vi.mock("../../api/sourceAnchors", () => ({ sourceAnchorsApi: {
  version: async () => ({ expected_file_hash: "a".repeat(64), expected_anchor_revision_id: 1, expected_segmentation_revision_id: 2 }),
  page: async (_documentId: number, _pageNumber: number, _version: unknown, signal?: AbortSignal) => {
    if (pdfFixture.mappingHold) {
      return new Promise((_, reject) => signal?.addEventListener("abort", () => {
        pdfFixture.mappingCancelled(); reject(new DOMException("取消", "AbortError"));
      }, { once: true }));
    }
    return { page_number: 1, rotation: 0, anchor_revision_id: 1, segmentation_revision_id: 2,
      pdfjs_version: "6.2.108", items: [{ item_index: 0, source_array_index: 0, text: "研究对象", rank: 0, eligibility: "eligible" }] };
  },
} }));

import PdfAnnotationReader from "./PdfAnnotationReader.vue";

afterEach(() => {
  window.getSelection()?.removeAllRanges();
  delete (window.Range.prototype as { getClientRects?: () => unknown }).getClientRects;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  pdfFixture.pageCount = 1; pdfFixture.rendered = []; pdfFixture.holdNext = false; pdfFixture.failNext = false; pdfFixture.cancelled.mockClear();
  pdfFixture.textLayerHold = false; pdfFixture.textLayerCancelled.mockClear();
  pdfFixture.mappingHold = false; pdfFixture.mappingCancelled.mockClear();
});

describe("PdfAnnotationReader", () => {
  it("cancels an active Canvas task on document change and renders the new generation", async () => {
    pdfFixture.holdNext = true;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: { sourceUrl: "/old.pdf", annotations: [], selectedAnnotationId: null } });
    await flushPromises();
    expect(pdfFixture.rendered).toHaveLength(1);
    await wrapper.setProps({ sourceUrl: "/new.pdf" });
    await flushPromises();
    expect(pdfFixture.cancelled).toHaveBeenCalledOnce();
    expect(wrapper.get(".text-layer").text()).toBe("研究对象");
    expect(wrapper.find(".page-error").exists()).toBe(false);
    wrapper.unmount();
  });
  it("cancels a pending TextItem mapping request when the document changes", async () => {
    pdfFixture.mappingHold = true;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: {
      sourceUrl: "/old.pdf", documentId: 7, fileHash: "a".repeat(64), annotations: [], selectedAnnotationId: null,
    } });
    await flushPromises();
    await wrapper.setProps({ sourceUrl: "/new.pdf" });
    await flushPromises();
    expect(pdfFixture.mappingCancelled).toHaveBeenCalled();
    expect(wrapper.text()).not.toContain("文本映射失败");
    wrapper.unmount();
  });
  it("cancels a pending TextItem mapping request when the reader unmounts", async () => {
    pdfFixture.mappingHold = true;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: {
      sourceUrl: "/document.pdf", documentId: 7, fileHash: "a".repeat(64), annotations: [], selectedAnnotationId: null,
    } });
    await flushPromises();
    wrapper.unmount();
    expect(pdfFixture.mappingCancelled).toHaveBeenCalledOnce();
  });
  it("cancels an active TextLayer task on document change", async () => {
    pdfFixture.textLayerHold = true;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: { sourceUrl: "/old.pdf", annotations: [], selectedAnnotationId: null } });
    await flushPromises();
    await wrapper.setProps({ sourceUrl: "/new.pdf" });
    await flushPromises();
    expect(pdfFixture.textLayerCancelled).toHaveBeenCalledOnce();
    expect(wrapper.get(".text-layer").text()).toBe("研究对象");
    expect(wrapper.find(".page-error").exists()).toBe(false);
    wrapper.unmount();
  });
  it("keeps the document usable when one page fails and retries that page", async () => {
    pdfFixture.failNext = true;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: { sourceUrl: "/document.pdf", annotations: [], selectedAnnotationId: null } });
    await flushPromises();
    expect(wrapper.get(".page-error").text()).toContain("合成页失败");
    await wrapper.get(".page-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".page-error").exists()).toBe(false);
    expect(wrapper.get(".text-layer").text()).toBe("研究对象");
    wrapper.unmount();
  });
  it("renders a bounded window, releases remote pixels and restores a page after returning", async () => {
    pdfFixture.pageCount = 20;
    let observe!: IntersectionObserverCallback;
    vi.stubGlobal("IntersectionObserver", class {
      constructor(callback: IntersectionObserverCallback) { observe = callback; }
      observe() {} disconnect() {}
    });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, { props: { sourceUrl: "/synthetic.pdf", annotations: [], selectedAnnotationId: null }, attachTo: document.body });
    await flushPromises();
    expect(wrapper.findAll(".pdf-page")).toHaveLength(20);
    expect(pdfFixture.rendered).toEqual([1, 2]);
    const first = wrapper.get('[data-page-number="1"]').element as HTMLElement;
    const last = wrapper.get('[data-page-number="20"]').element as HTMLElement;
    const height = first.style.height;
    observe([intersection(first, false), intersection(last, true)], {} as IntersectionObserver);
    await flushPromises();
    expect(first.querySelector("canvas")!.width).toBe(0);
    expect(first.querySelectorAll(".text-layer span")).toHaveLength(0);
    expect(first.style.height).toBe(height);
    expect(last.querySelector("canvas")!.width).toBeGreaterThan(0);
    expect(last.querySelectorAll(".text-layer span")).toHaveLength(1);
    observe([intersection(last, false), intersection(first, true)], {} as IntersectionObserver);
    await flushPromises();
    expect(first.querySelectorAll(".text-layer span")).toHaveLength(1);
    expect(last.querySelector("canvas")!.width).toBe(0);
    wrapper.unmount();
  });
  it("captures a browser text selection and emits a same-page annotation anchor", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    const wrapper = mount(PdfAnnotationReader, {
      props: { sourceUrl: "/api/v1/documents/7/original", documentId: 7, fileHash: "a".repeat(64), annotations: [], selectedAnnotationId: null },
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

    expect(wrapper.emitted("selectionChange")).toContainEqual([expect.objectContaining({
      pageNumber: 1,
      selectedText: "研究对象",
      rectangles: [expect.objectContaining({ left: .1, top: .1 })],
      anchorDescriptor: expect.objectContaining({ expected_anchor_revision_id: 1,
        fragments: [expect.objectContaining({ start_item_index: 0, start_offset_utf16: 0, end_offset_utf16: 4 })] }),
    })]);
    expect(wrapper.text()).toContain("已记录选中文字，可在右侧批注中保存。");
    wrapper.unmount();
  });
});
