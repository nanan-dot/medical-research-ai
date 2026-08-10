import { apiRequest } from "./client";

export type OcrJobStatus = "queued" | "processing" | "succeeded" | "partial_failed" | "failed" | "cancelled";

export interface OcrPage {
  page_number: number;
  text: string | null;
  confidence: number | null;
  error_code: string | null;
  error_message: string | null;
}

export interface OcrJob {
  id: number;
  document_id: number;
  status: OcrJobStatus;
  engine_name: string | null;
  engine_version: string | null;
  language: string;
  page_count: number | null;
  completed_pages: number;
  failed_pages: number;
  output_sha256: string | null;
  error_code: string | null;
  error_message: string | null;
  cancel_requested: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  pages: OcrPage[];
}

export const documentOcrApi = {
  request(documentId: number): Promise<OcrJob> {
    return apiRequest<OcrJob>(`/documents/${documentId}/ocr`, { method: "POST" });
  },
  getLatest(documentId: number): Promise<OcrJob | null> {
    return apiRequest<OcrJob | null>(`/documents/${documentId}/ocr`);
  },
  cancel(documentId: number): Promise<OcrJob> {
    return apiRequest<OcrJob>(`/documents/${documentId}/ocr/cancel`, { method: "POST" });
  },
};
