import type { AnnotationRect } from "../api/documentAnnotations";
import type { AnchorFragment, SelectionPage } from "../types/sourceAnchors";

export interface MappedText {
  node: Text;
  page: HTMLElement;
  metadata: SelectionPage;
  item: SelectionPage["items"][number];
}

/** 只绑定 PDF.js 公开 textDivs 输出；逐项核对 A0，拒绝推测 DOM 编号。 */
export function bindTextLayer(page: HTMLElement, divs: readonly HTMLElement[], strings: readonly string[],
  sourceIndexes: readonly number[], metadata: SelectionPage): MappedText[] {
  if (divs.length !== metadata.items.length || strings.length !== divs.length || sourceIndexes.length !== divs.length) {
    throw new Error("TEXT_LAYER_MAPPING_MISMATCH：文本项数量不一致，已禁用精确选区。");
  }
  return divs.flatMap((span, index) => {
    const item = metadata.items[index];
    if (!item || item.item_index !== index || item.source_array_index !== sourceIndexes[index] ||
        strings[index] !== item.text || span.textContent !== item.text) {
      throw new Error("TEXT_LAYER_MAPPING_MISMATCH：浏览器文本与固定原文不一致。");
    }
    span.dataset.pageNumber = String(metadata.page_number);
    span.dataset.textItemIndex = String(item.item_index);
    span.dataset.sourceArrayIndex = String(item.source_array_index);
    span.dataset.anchorRevisionId = String(metadata.anchor_revision_id);
    if (!item.text) return [];
    if (span.childNodes.length !== 1 || span.firstChild?.nodeType !== Node.TEXT_NODE) {
      throw new Error("TEXT_LAYER_MAPPING_MISMATCH：文本节点结构不能精确映射。");
    }
    return [{ node: span.firstChild as Text, page, metadata, item }];
  });
}

function normalizedRect(rect: DOMRect, bounds: DOMRect): AnnotationRect | null {
  if (!bounds.width || !bounds.height || !rect.width || !rect.height) return null;
  const left = Math.max(0, (rect.left - bounds.left) / bounds.width);
  const top = Math.max(0, (rect.top - bounds.top) / bounds.height);
  const right = Math.min(1, ((rect.right ?? rect.left + rect.width) - bounds.left) / bounds.width);
  const bottom = Math.min(1, ((rect.bottom ?? rect.top + rect.height) - bounds.top) / bounds.height);
  return right > left && bottom > top ? { left, top, width: right - left, height: bottom - top } : null;
}

export function rangeRectangles(range: Range, page: HTMLElement): AnnotationRect[] {
  if (typeof range.getClientRects !== "function") return [];
  const bounds = page.getBoundingClientRect();
  return Array.from(range.getClientRects()).map(rect => normalizedRect(rect, bounds)).filter((rect): rect is AnnotationRect => rect !== null);
}

/** DOM Range 本身统一正反拖选端点；读取交集后按 A1 rank 排序，保留每项范围。 */
export function captureMappedRange(range: Range, mappings: readonly MappedText[]): { fragments: AnchorFragment[]; browserQuote: string } {
  const selected = mappings.flatMap(mapping => {
    if (!range.intersectsNode(mapping.node)) return [];
    const start = range.startContainer === mapping.node ? range.startOffset : 0;
    const end = range.endContainer === mapping.node ? range.endOffset : mapping.node.length;
    if (start === end || range.comparePoint(mapping.node, end) < 0 || range.comparePoint(mapping.node, start) > 0) return [];
    if (mapping.item.rank === null || mapping.item.eligibility === "blocked") {
      throw new Error("SELECTION_CROSSES_BLOCKED_REGION：该范围的阅读顺序尚未确认，请缩小选区。");
    }
    const itemRange = document.createRange(); itemRange.setStart(mapping.node, start); itemRange.setEnd(mapping.node, end);
    return [{ mapping, start, end, itemRange, text: mapping.node.data.slice(start, end) }];
  });
  if (!selected.length) throw new Error("SELECTION_ENDPOINT_UNRESOLVED：无法确认选区端点。");
  // 检查未映射文字，不能默默丢掉映射失败页面或区域中的选中文字。
  const compact = (text: string) => text.normalize("NFC").replace(/\s+/g, "");
  if (compact(selected.map(item => item.text).join("")) !== compact(range.toString())) {
    throw new Error("TEXT_LAYER_MAPPING_MISMATCH：选区包含未映射文字。");
  }
  selected.sort((left, right) => left.mapping.item.rank! - right.mapping.item.rank! || left.start - right.start);
  if (selected.length > 256 || selected.map(item => item.text).join("").length > 8000) {
    throw new Error("SELECTION_LIMIT_EXCEEDED：请缩小选区。");
  }
  return { browserQuote: selected.map(item => item.text).join(" "), fragments: selected.map(({ mapping, start, end, itemRange }) => ({
    page_number: mapping.metadata.page_number, start_item_index: mapping.item.item_index, end_item_index: mapping.item.item_index,
    start_offset_utf16: start, end_offset_utf16: end, rectangles: rangeRectangles(itemRange, mapping.page),
  })) };
}

export function locateFragments(fragments: readonly AnchorFragment[], mappings: readonly MappedText[]): { page: number; rect: AnnotationRect }[] | null {
  const results: { page: number; rect: AnnotationRect }[] = [];
  for (const fragment of fragments) {
    const items = mappings.filter(item => item.metadata.page_number === fragment.page_number &&
      item.item.item_index >= fragment.start_item_index && item.item.item_index <= fragment.end_item_index);
    const expectedItemCount = fragment.end_item_index - fragment.start_item_index + 1;
    if (expectedItemCount <= 0 || items.length !== expectedItemCount ||
        items[0]?.item.item_index !== fragment.start_item_index ||
        items.at(-1)?.item.item_index !== fragment.end_item_index) return null;
    for (const mapping of items) {
      const start = mapping.item.item_index === fragment.start_item_index ? fragment.start_offset_utf16 : 0;
      const end = mapping.item.item_index === fragment.end_item_index ? fragment.end_offset_utf16 : mapping.node.length;
      if (start >= end || end > mapping.node.length) return null;
      const range = document.createRange(); range.setStart(mapping.node, start); range.setEnd(mapping.node, end);
      results.push(...rangeRectangles(range, mapping.page).map(rect => ({ page: fragment.page_number, rect })));
    }
  }
  return results.length ? results : null;
}
