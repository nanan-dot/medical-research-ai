import { apiRequest } from "./client";

export type DocumentPreviewKind = "pdf" | "docx" | "unavailable";

export interface DocumentPreviewBlock {
  kind: "heading" | "paragraph" | "list_item";
  text: string;
  level: number | null;
}

export interface DocumentPreviewTable {
  rows: readonly (readonly string[])[];
}

export interface DocumentPreview {
  document_id: number;
  kind: DocumentPreviewKind;
  content_url: string | null;
  blocks: readonly DocumentPreviewBlock[];
  tables: readonly DocumentPreviewTable[];
  message: string | null;
}

export const documentPreviewsApi = {
  get(documentId: number): Promise<DocumentPreview> {
    return apiRequest<DocumentPreview>(`/documents/${documentId}/preview`);
  },
};
