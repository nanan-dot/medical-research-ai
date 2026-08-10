import { apiRequest } from "./client";
import type { LibraryItem } from "./literatureSearch";

export type OpenFulltextAcquisitionStatus =
  | "succeeded"
  | "identity_mismatch"
  | "license_unverified"
  | "pdf_unavailable"
  | "network_error"
  | "rate_limited"
  | "content_invalid"
  | "storage_failed";

export interface OpenFulltextAcquisition {
  id: number;
  library_item_id: number;
  document_id: number | null;
  pmcid: string;
  status: OpenFulltextAcquisitionStatus;
  source_url: string | null;
  license: string | null;
  file_format: string | null;
  file_sha256: string | null;
  error_code: string | null;
  error_message: string | null;
  attempted_at: string;
  retrieved_at: string | null;
}

export interface OpenFulltextResult {
  item: LibraryItem;
  acquisition: OpenFulltextAcquisition;
}

export function acquireOfficialPmcFulltext(
  libraryItemId: number,
  pmcid: string,
): Promise<OpenFulltextResult> {
  return apiRequest<OpenFulltextResult>(
    `/library-items/${libraryItemId}/fulltext-retrievals`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pmcid }),
    },
  );
}
