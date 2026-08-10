import { apiRequest } from "./client";
import type { DocumentRecord } from "./documents";

export interface DocumentAssetRecord {
  id: number;
  asset_kind: string;
  original_filename: string;
  stored_relative_path: string;
  media_type: string;
  byte_size: number;
  sha256: string;
  processing_status: string;
  created_at: string;
}

export interface DocumentUploadResult {
  document: DocumentRecord;
  asset: DocumentAssetRecord;
  auto_parse_started: boolean;
  parse_trigger_url: string;
}

export const documentUploadsApi = {
  upload(file: File): Promise<DocumentUploadResult> {
    const formData = new FormData();
    formData.append("file", file, file.name);
    return apiRequest<DocumentUploadResult>("/document-uploads", {
      method: "POST",
      body: formData,
    });
  },
};
