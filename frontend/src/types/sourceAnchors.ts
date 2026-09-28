import type { AnnotationRect } from "../api/documentAnnotations";

export interface AnchorVersion {
  expected_file_hash: string;
  expected_anchor_revision_id: number;
  expected_segmentation_revision_id: number;
}
export interface AnchorFragment {
  page_number: number;
  start_item_index: number;
  start_offset_utf16: number;
  end_item_index: number;
  end_offset_utf16: number;
  rectangles: readonly AnnotationRect[];
}
export interface SourceAnchorDescriptor extends AnchorVersion {
  browser_quote: string;
  fragments: readonly AnchorFragment[];
}
export interface SourceAnchor {
  id: number;
  document_id: number;
  anchor_revision_id: number;
  file_hash: string;
  quote: string;
  quote_hash: string;
  resolution_status: "exact" | "unresolved";
  quality_status: "eligible" | "review_required";
  fragments: readonly AnchorFragment[];
  segment_ids: readonly number[];
}
export interface SelectionPage {
  page_number: number;
  rotation: number;
  anchor_revision_id: number;
  segmentation_revision_id: number;
  pdfjs_version: string;
  items: readonly { item_index: number; source_array_index: number; text: string; rank: number | null; eligibility: string }[];
}
