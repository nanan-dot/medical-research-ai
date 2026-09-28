import { afterEach, describe, expect, it } from "vitest";
import { bindTextLayer, captureMappedRange, locateFragments } from "./pdfSelection";
import type { SelectionPage } from "../types/sourceAnchors";

function mappedPage(pageNumber = 1) {
  const page = document.createElement("div");
  const span = document.createElement("span");
  span.textContent = "A😀 α ≤ 5";
  page.append(span);
  const metadata: SelectionPage = { page_number: pageNumber, rotation: 0,
    anchor_revision_id: 1, segmentation_revision_id: 2, pdfjs_version: "6.2.108",
    items: [{ item_index: 0, source_array_index: 0, text: span.textContent, rank: pageNumber - 1, eligibility: "eligible" }] };
  return { page, span, metadata };
}

afterEach(() => {
  delete (window.Range.prototype as { getClientRects?: () => unknown }).getClientRects;
});

describe("A2 explicit PDF.js TextLayer mapping", () => {
  it("rejects a text mismatch instead of numbering arbitrary DOM spans", () => {
    const { page, span, metadata } = mappedPage();
    expect(() => bindTextLayer(page, [span], ["different"], [0], metadata)).toThrow("TEXT_LAYER_MAPPING_MISMATCH");
  });

  it("captures a UTF-16 range including emoji and a container boundary", () => {
    const { page, span, metadata } = mappedPage();
    const mapped = bindTextLayer(page, [span], [span.textContent!], [0], metadata);
    const range = document.createRange();
    range.setStart(span.firstChild!, 1);
    range.setEnd(page, 1);
    const result = captureMappedRange(range, mapped);
    expect(result.fragments[0]?.start_offset_utf16).toBe(1);
    expect(result.fragments[0]?.end_offset_utf16).toBe(9);
    expect(result.browserQuote).toBe("😀 α ≤ 5");
  });

  it("does not include the following visual line when the range ends at its boundary", () => {
    const page = document.createElement("div");
    const first = document.createElement("span");
    const second = document.createElement("span");
    first.textContent = "first line";
    second.textContent = "second line";
    page.append(first, second);
    const metadata: SelectionPage = {
      page_number: 1,
      rotation: 0,
      anchor_revision_id: 1,
      segmentation_revision_id: 2,
      pdfjs_version: "6.2.108",
      items: [
        { item_index: 0, source_array_index: 0, text: "first line", rank: 0, eligibility: "eligible" },
        { item_index: 1, source_array_index: 1, text: "second line", rank: 1, eligibility: "eligible" },
      ],
    };
    const mappings = bindTextLayer(page, [first, second], ["first line", "second line"], [0, 1], metadata);
    const range = document.createRange();
    range.selectNode(first.firstChild!);

    const result = captureMappedRange(range, mappings);

    expect(result.browserQuote).toBe("first line");
    expect(result.fragments).toHaveLength(1);
    expect(result.fragments[0]?.end_item_index).toBe(0);
  });

  it("preserves separate page fragments for a cross-page selection", () => {
    const first = mappedPage(1), second = mappedPage(2);
    const host = document.createElement("div"); host.append(first.page, second.page);
    const mappings = [first, second].flatMap(item => bindTextLayer(item.page, [item.span], [item.span.textContent!], [0], item.metadata));
    const range = document.createRange(); range.selectNodeContents(host);
    expect(captureMappedRange(range, mappings).fragments.map(item => item.page_number)).toEqual([1, 2]);
  });

  it("does not claim an exact replay when a multi-item fragment is only partially mapped", () => {
    const first = mappedPage();
    const mapped = bindTextLayer(first.page, [first.span], [first.span.textContent!], [0], first.metadata);
    Object.defineProperty(window.Range.prototype, "getClientRects", {
      configurable: true,
      value: () => [{ left: 0, top: 0, right: 20, bottom: 10, width: 20, height: 10 }],
    });
    Object.defineProperty(first.page, "getBoundingClientRect", {
      configurable: true,
      value: () => ({ left: 0, top: 0, right: 100, bottom: 100, width: 100, height: 100 }),
    });
    const fragment = {
      page_number: 1,
      start_item_index: 0,
      start_offset_utf16: 0,
      end_item_index: 1,
      end_offset_utf16: 1,
      rectangles: [],
    };

    expect(locateFragments([fragment], mapped)).toBeNull();
  });
});
