import { apiRequest } from "./client";
import type { SourceAnchorDescriptor } from "../types/sourceAnchors";

export type AnnotationColor = "yellow" | "green" | "blue" | "pink";
export type AnnotationVersionStatus = "current" | "relocation_required";

export interface AnnotationRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface DocumentAnnotation {
  id: number;
  source_anchor_id?: number | null;
  resolved_source_anchor_id?: number | null;
  document_id: number;
  file_hash: string;
  page_number: number;
  rectangles: readonly AnnotationRect[];
  selected_text: string;
  selected_text_hash: string;
  color: AnnotationColor;
  note: string | null;
  version_status: AnnotationVersionStatus;
  created_at: string;
  updated_at: string;
}

export interface CreateDocumentAnnotation {
  expected_file_hash: string;
  page_number: number;
  rectangles: readonly AnnotationRect[];
  selected_text: string;
  color: AnnotationColor;
  note: string | null;
}

export interface UpdateDocumentAnnotation {
  expected_file_hash: string;
  color?: AnnotationColor;
  note?: string | null;
}

export const documentAnnotationsApi = {
  createAnchored(documentId: number, descriptor: SourceAnchorDescriptor, color: AnnotationColor, note: string | null, key: string): Promise<DocumentAnnotation> {
    return apiRequest(`/documents/${documentId}/annotations`, { method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify({ anchor_descriptor: descriptor, color, note }) });
  },
  list(documentId: number): Promise<DocumentAnnotation[]> {
    return apiRequest<DocumentAnnotation[]>(`/documents/${documentId}/annotations`);
  },
  create(documentId: number, payload: CreateDocumentAnnotation): Promise<DocumentAnnotation> {
    return apiRequest<DocumentAnnotation>(`/documents/${documentId}/annotations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  update(
    documentId: number,
    annotationId: number,
    payload: UpdateDocumentAnnotation,
  ): Promise<DocumentAnnotation> {
    return apiRequest<DocumentAnnotation>(
      `/documents/${documentId}/annotations/${annotationId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
  },
  remove(documentId: number, annotationId: number, expectedFileHash: string): Promise<void> {
    const query = new URLSearchParams({ expected_file_hash: expectedFileHash });
    return apiRequest<void>(`/documents/${documentId}/annotations/${annotationId}?${query}`, {
      method: "DELETE",
    });
  },
};
