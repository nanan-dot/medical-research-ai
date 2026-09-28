export interface ReadingSegment {
  id: number;
  reading_order: number;
  segment_type: string;
  translation_eligibility: string;
  fragments: readonly { page_number: number; start_item_index: number; end_item_index: number }[];
}

export interface VisibleReadingContext {
  documentId: number;
  anchorRevisionId: number;
  segmentationRevisionId: number;
  primarySegmentId: number | null;
  visibleSegmentIds: readonly number[];
  pageNumbers: readonly number[];
  reason: "scroll" | "selection" | "navigation" | "keyboard";
}
