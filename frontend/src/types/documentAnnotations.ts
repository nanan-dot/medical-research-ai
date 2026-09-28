import type { AnnotationRect } from "../api/documentAnnotations";
import type { SourceAnchorDescriptor } from "./sourceAnchors";

export interface PdfTextSelection {
  pageNumber: number;
  rectangles: readonly AnnotationRect[];
  selectedText: string;
  anchorDescriptor?: SourceAnchorDescriptor;
}
