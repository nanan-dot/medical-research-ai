import { shallowRef } from "vue";
import type { Ref } from "vue";
import { readPageSegments } from "../api/readingSegments";
import type { AnchorVersion } from "../types/sourceAnchors";
import type { ReadingSegment, VisibleReadingContext } from "../types/readingContext";
import type { MappedText } from "../utils/pdfSelection";
import { chooseActiveSegment, type SegmentVisibility } from "../utils/activeReadingSegment";

interface Options {
  root: Readonly<Ref<HTMLElement | null>>;
  mappings: () => readonly MappedText[];
  publish: (context: VisibleReadingContext | null) => void;
}

/** 只有版本一致的 A1 段落可参与阅读上下文；迟到请求和离屏节点不参与评分。 */
export function useVisibleSegments(options: Options) {
  const context = shallowRef<VisibleReadingContext | null>(null);
  const error = shallowRef("");
  const pages = new Map<number, readonly ReadingSegment[]>();
  const requests = new Map<number, AbortController>();
  let identity: { documentId: number; version: AnchorVersion } | null = null;
  let generation = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;

  function clear(): void {
    generation++; clearTimeout(timer); pages.clear(); identity = null;
    requests.forEach(controller => controller.abort()); requests.clear();
    error.value = ""; context.value = null; options.publish(null);
  }

  async function loadPage(documentId: number, version: AnchorVersion, page: number): Promise<void> {
    const current = generation;
    requests.get(page)?.abort();
    const controller = new AbortController(); requests.set(page, controller);
    let expired = false;
    const timeout = setTimeout(() => { expired = true; controller.abort(); }, 15_000);
    identity = { documentId, version };
    try {
      const segments = await readPageSegments(documentId, page, version, controller.signal);
      if (current !== generation || controller.signal.aborted) return;
      pages.set(page, segments); sample("scroll");
    } catch (cause) {
      if (current === generation && (!controller.signal.aborted || expired)) error.value = expired ? "可视段落读取超时，请重试。" : cause instanceof Error ? cause.message : "可视段落读取失败";
    } finally {
      clearTimeout(timeout);
      if (requests.get(page) === controller) requests.delete(page);
    }
  }

  function sample(reason: VisibleReadingContext["reason"]): void {
    if (!identity || !options.root.value) return;
    const viewport = options.root.value.getBoundingClientRect();
    if (!viewport.height) return;
    const segments = new Map<number, ReadingSegment>();
    pages.forEach(items => items.forEach(item => segments.set(item.id, item)));
    const visiblePages = new Set<number>();
    const candidates: SegmentVisibility[] = [];
    const selectedSegments = new Set<number>();
    const browserSelection = window.getSelection();
    const selectedRange = browserSelection?.rangeCount && !browserSelection.isCollapsed ? browserSelection.getRangeAt(0) : null;
    for (const segment of segments.values()) {
      let total = 0; let visible = 0; let distance = Infinity;
      for (const mapping of options.mappings()) {
        if (!segment.fragments.some(fragment => fragment.page_number === mapping.metadata.page_number &&
          fragment.start_item_index <= mapping.item.item_index && fragment.end_item_index >= mapping.item.item_index)) continue;
        if (reason === "selection" && selectedRange?.intersectsNode(mapping.node)) selectedSegments.add(segment.id);
        if (reason === "keyboard" && mapping.node.parentElement?.contains(document.activeElement)) selectedSegments.add(segment.id);
        const rect = mapping.node.parentElement!.getBoundingClientRect();
        const area = rect.width * rect.height; total += area;
        const intersection = Math.max(0, Math.min(rect.bottom, viewport.bottom) - Math.max(rect.top, viewport.top)) *
          Math.max(0, Math.min(rect.right, viewport.right) - Math.max(rect.left, viewport.left));
        visible += intersection;
        if (intersection > 0) {
          visiblePages.add(mapping.metadata.page_number);
          distance = Math.min(distance, Math.abs((rect.top + rect.bottom) / 2 - (viewport.top + viewport.height * .35)) / viewport.height);
        }
      }
      if (visible > 0 && total > 0) candidates.push({ id: segment.id, readingOrder: segment.reading_order,
        visibleRatio: visible / total, focusDistance: distance, isHeading: segment.segment_type === "heading" });
    }
    candidates.sort((left, right) => left.readingOrder - right.readingOrder);
    context.value = { documentId: identity.documentId, anchorRevisionId: identity.version.expected_anchor_revision_id,
      segmentationRevisionId: identity.version.expected_segmentation_revision_id,
      primarySegmentId: candidates.find(item => selectedSegments.has(item.id))?.id ?? chooseActiveSegment(candidates, context.value?.primarySegmentId ?? null),
      visibleSegmentIds: candidates.map(item => item.id), pageNumbers: [...visiblePages].sort((a, b) => a - b), reason };
    options.publish(context.value);
  }

  function schedule(reason: VisibleReadingContext["reason"] = "scroll"): void {
    clearTimeout(timer);
    timer = setTimeout(() => sample(reason), 120);
  }
  function release(page: number): void { pages.delete(page); requests.get(page)?.abort(); requests.delete(page); }
  return { context, error, clear, loadPage, release, schedule };
}
