import { onScopeDispose, shallowRef, watch } from "vue";

import { medicalTranslationsApi, type TranslationPrefetchIntent } from "../api/medicalTranslations";
import type { VisibleReadingContext } from "../types/readingContext";
import { createTranslationFollowPolicy } from "../utils/translationFollowPolicy";
import { rankTranslationCandidates, shouldPrefetch } from "../utils/translationPrefetchPolicy";

interface Options {
  documentId: () => number;
  fileHash: () => string;
  context: () => VisibleReadingContext | null;
  followEnabled: () => boolean;
  pinnedSegmentId: () => number | null;
  hasSelection: () => boolean;
  isEditing: () => boolean;
}

/** 将 A4 可视段落转成一次有界意图；旧代际和离开页面的请求均可取消。 */
export function useSegmentTranslationIntent(options: Options) {
  const result = shallowRef<TranslationPrefetchIntent | null>(null);
  const error = shallowRef<string | null>(null);
  const activeSegmentId = shallowRef<number | null>(null);
  const policy = createTranslationFollowPolicy({ dwellMs: 300 });
  let controller: AbortController | null = null;
  let lastKey = "";
  let dwellTimer: ReturnType<typeof setTimeout> | null = null;

  function environmentAllowsPrefetch(): boolean {
    const connection = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }).connection;
    return shouldPrefetch({ followEnabled: options.followEnabled(), isBackground: document.visibilityState !== "visible",
      saveData: Boolean(connection?.saveData), effectiveType: connection?.effectiveType ?? null });
  }

  async function request(context: VisibleReadingContext): Promise<void> {
    if (!options.followEnabled()) return;
    const now = performance.now();
    policy.setGeneration(`${context.documentId}:${context.anchorRevisionId}:${context.segmentationRevisionId}:${options.fileHash()}`);
    const chosen = policy.observe({ segmentId: context.primarySegmentId, now, hasSelection: options.hasSelection(),
      isEditing: options.isEditing(), pinnedSegmentId: options.pinnedSegmentId() });
    activeSegmentId.value = chosen;
    if (chosen === null) {
      if (context.primarySegmentId !== null) {
        if (dwellTimer !== null) clearTimeout(dwellTimer);
        // A4 may publish only once after scrolling stops; schedule one bounded re-sample
        // so the dwell rule can mature without relying on a second scroll event.
        dwellTimer = setTimeout(() => void request(context), 300);
      }
      return;
    }
    if (dwellTimer !== null) { clearTimeout(dwellTimer); dwellTimer = null; }
    const nearby = rankTranslationCandidates([
      { segmentId: chosen, priority: "active", distance: 0 },
      ...(environmentAllowsPrefetch() ? context.visibleSegmentIds.filter(id => id !== chosen)
        .map((segmentId, index) => ({ segmentId, priority: "adjacent" as const, distance: index + 1 })) : []),
    ], 3);
    const requestKey = `${context.documentId}:${context.anchorRevisionId}:${context.segmentationRevisionId}:${nearby.map(item => item.segmentId).join(",")}`;
    if (requestKey === lastKey) return;
    lastKey = requestKey;
    controller?.abort();
    controller = new AbortController();
    error.value = null;
    try {
      const response = await medicalTranslationsApi.requestSegments(context.documentId, {
        expected_file_hash: options.fileHash(), expected_anchor_revision_id: context.anchorRevisionId,
        expected_segmentation_revision_id: context.segmentationRevisionId, segment_ids: nearby.map(item => item.segmentId),
        active_segment_id: chosen, trigger: "follow",
      }, controller.signal);
      if (!controller.signal.aborted && requestKey === lastKey) result.value = response;
    } catch (cause) {
      if (!controller.signal.aborted && requestKey === lastKey) error.value = cause instanceof Error ? cause.message : "段落翻译意图未提交";
    }
  }

  watch(() => options.context(), context => { if (context) void request(context); }, { deep: false, immediate: true });
  onScopeDispose(() => { controller?.abort(); if (dwellTimer !== null) clearTimeout(dwellTimer); });
  return { activeSegmentId, error, result };
}
