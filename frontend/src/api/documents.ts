export type ParseStatus = "pending" | "parsing" | "succeeded" | "failed";
export type IndexStatus = "pending" | "indexing" | "succeeded" | "failed" | "outdated";

export interface DocumentRecord {
  id: number;
  knowledge_source_id: number;
  file_path: string;
  file_hash: string;
  file_size: number;
  modified_time: string;
  scan_state: "pending" | "outdated";
  parse_status: ParseStatus;
  index_status: IndexStatus;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface DocumentPage {
  items: DocumentRecord[];
  total: number;
  offset: number;
  limit: number;
}

export interface DocumentFilters {
  parseStatus: ParseStatus | "";
  indexStatus: IndexStatus | "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/documents${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; error?: { message?: string } }
      | null;
    throw new Error(payload?.error?.message ?? payload?.detail ?? "文档请求失败");
  }
  return (await response.json()) as T;
}

export const documentsApi = {
  list(filters: DocumentFilters, offset: number, limit: number) {
    const query = new URLSearchParams({ offset: String(offset), limit: String(limit) });
    if (filters.parseStatus) query.set("parse_status", filters.parseStatus);
    if (filters.indexStatus) query.set("index_status", filters.indexStatus);
    return request<DocumentPage>(`?${query.toString()}`);
  },
  retryParse: (id: number) => request<DocumentRecord>(`/${id}/retry-parse`, { method: "POST" }),
  retryIndex: (id: number) => request<DocumentRecord>(`/${id}/retry-index`, { method: "POST" }),
  deleteIndex: (id: number) => request<DocumentRecord>(`/${id}/index`, { method: "DELETE" }),
};
