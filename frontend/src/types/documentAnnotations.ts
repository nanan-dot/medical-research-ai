import type { AnnotationRect } from "../api/documentAnnotations";

export interface PdfTextSelection {
  pageNumber: number;
  rectangles: readonly AnnotationRect[];
  selectedText: string;
}
