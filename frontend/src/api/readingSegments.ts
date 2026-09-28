import { apiRequest } from "./client";
import type { AnchorVersion } from "../types/sourceAnchors";
import type { ReadingSegment } from "../types/readingContext";

interface SegmentPage {
  anchor_revision_id: number;
  segmentation_revision_id: number;
  items: ReadingSegment[];
  total: number;
}

export interface TranslationReadingSegment extends ReadingSegment {
  text: string;
}

/** 分页保持相同版本；只保存段落身份与范围，不缓存正文副本。 */
export async function readPageSegments(documentId: number, page: number, version: AnchorVersion, signal?: AbortSignal): Promise<ReadingSegment[]> {
  const segments: ReadingSegment[] = [];
  let offset = 0;
  while (true) {
    const query = new URLSearchParams({ page: String(page), offset: String(offset), limit: "200",
      expected_anchor_revision_id: String(version.expected_anchor_revision_id),
      expected_segmentation_revision_id: String(version.expected_segmentation_revision_id) });
    const response = await apiRequest<SegmentPage>(`/documents/${documentId}/source-segments?${query}`, { signal });
    if (response.anchor_revision_id !== version.expected_anchor_revision_id || response.segmentation_revision_id !== version.expected_segmentation_revision_id) {
      throw new Error("可视段落版本不一致，请重新加载原文。");
    }
    segments.push(...response.items.map(({ id, reading_order, segment_type, translation_eligibility, fragments }) => ({
      id, reading_order, segment_type, translation_eligibility, fragments,
    })));
    offset += response.items.length;
    if (offset >= response.total) return segments;
    if (!response.items.length) throw new Error("可视段落分页不完整。");
  }
}

/** Load the current page's immutable A1 source text for bilingual rendering. */
export async function readPageTranslationSegments(
  documentId: number,
  page: number,
  version: AnchorVersion,
  signal?: AbortSignal,
): Promise<TranslationReadingSegment[]> {
  const query = new URLSearchParams({
    page: String(page),
    offset: "0",
    limit: "200",
    expected_anchor_revision_id: String(version.expected_anchor_revision_id),
    expected_segmentation_revision_id: String(version.expected_segmentation_revision_id),
  });
  const response = await apiRequest<SegmentPage & { items: TranslationReadingSegment[] }>(
    `/documents/${documentId}/source-segments?${query}`,
    { signal },
  );
  if (
    response.anchor_revision_id !== version.expected_anchor_revision_id
    || response.segmentation_revision_id !== version.expected_segmentation_revision_id
  ) {
    throw new Error("双语阅读版本不一致，请重新加载论文。");
  }
  return response.items;
}
