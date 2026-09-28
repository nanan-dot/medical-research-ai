import { shallowRef } from "vue";
import type { AnnotationRect, DocumentAnnotation } from "../api/documentAnnotations";
import { sourceAnchorsApi } from "../api/sourceAnchors";
import { locateFragments, type MappedText } from "../utils/pdfSelection";

export function useAnchorHighlights() {
  const highlights = shallowRef<Map<number, { annotation: DocumentAnnotation; rect: AnnotationRect }[]>>(new Map());
  const locationStatus = shallowRef("");
  let generation = 0;
  function clear() { generation++; highlights.value = new Map(); locationStatus.value = ""; }
  async function refresh(annotations: readonly DocumentAnnotation[], mappings: readonly MappedText[], fileHash?: string) {
    const current = ++generation;
    const next = new Map<number, { annotation: DocumentAnnotation; rect: AnnotationRect }[]>();
    const statuses = new Set<string>();
    for (const annotation of annotations) {
      if (annotation.version_status !== "current") continue;
      let rects = annotation.rectangles.map(rect => ({ page: annotation.page_number, rect }));
      const activeAnchorId = annotation.resolved_source_anchor_id ?? annotation.source_anchor_id;
      if (activeAnchorId) {
        try {
          const anchor = await sourceAnchorsApi.get(activeAnchorId);
          if (anchor.resolution_status !== "exact" || anchor.file_hash !== fileHash) {
            statuses.add("旧版本锚点不可精确定位，请核对原文件。"); continue;
          }
          const compatible = mappings.filter(item => item.metadata.anchor_revision_id === anchor.anchor_revision_id);
          const exact = locateFragments(anchor.fragments, compatible);
          rects = exact ?? anchor.fragments.flatMap(fragment => fragment.rectangles.map(rect => ({ page: fragment.page_number, rect })));
          statuses.add(exact ? "按 TextItem 字符范围精确定位。" : rects.length ? "使用保存的几何位置后备定位。" : "仅能定位到页，未恢复精确选区。");
        } catch {
          statuses.add("锚点读取失败，仅显示原有几何快照。");
        }
      } else statuses.add("旧批注使用几何位置显示。");
      for (const { page, rect } of rects) {
        const entries = next.get(page) ?? []; entries.push({ annotation, rect }); next.set(page, entries);
      }
    }
    if (current === generation) { highlights.value = next; locationStatus.value = [...statuses].join(" "); }
  }
  return { highlights, locationStatus, refresh, clear };
}
