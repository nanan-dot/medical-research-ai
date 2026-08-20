export type ParseStatus = "pending" | "parsing" | "succeeded" | "failed";
export type IndexStatus = "pending" | "indexing" | "succeeded" | "failed" | "outdated";
export type DocumentHealthStatus = "available" | "processing" | "needs_attention";
export type DocumentMode = "document" | "content";
export type DocumentFileType = "pdf" | "pptx" | "docx" | "markdown" | "txt" | "other";
export type DocumentSortBy = "updated_at" | "name" | "file_size";
export type SortOrder = "asc" | "desc";

export interface DocumentRecord {
  id: number;
  knowledge_source_id: number;
  file_path: string;
  original_filename: string | null;
  media_type: string | null;
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
  paperqa_index_key?: string | null;
  parsed_is_scanned: boolean | null;
  file_type?: DocumentFileType;
  extension?: string | null;
  preview_capability?: boolean;
  health_status?: DocumentHealthStatus;
  health_reason?: string | null;
  available_actions?: readonly string[];
  progress?: number | null;
  task_id?: number | null;
}

export interface DocumentPage {
  items: DocumentRecord[];
  total: number;
  offset: number;
  limit: number;
}

export interface ContentSearchResult {
  document_id: number;
  document_name: string;
  knowledge_source_id: number;
  source_name: string;
  locator_type: "page" | "slide" | "section" | "paragraph" | "unknown";
  locator: string | null;
  snippet: string;
}

export interface ContentSearchPage {
  items: ContentSearchResult[];
  total: number;
  offset: number;
  limit: number;
}

export interface DocumentStatistics {
  total: number;
  available: number;
  processing: number;
  needs_attention: number;
}

export interface BatchIndexResult {
  succeeded: number;
  failed: number;
  results: Array<{ document_id: number; index_status: IndexStatus; error_message: string | null }>;
}

export interface ContentSummary {
  document_id: number;
  title: string | null;
  page_count: number;
  page_numbers: number[];
  section_headings: string[];
  yaml_metadata: Record<string, unknown>;
  is_scanned: boolean;
  character_count: number;
}

export interface DocumentFilters {
  mode: DocumentMode;
  knowledgeSourceId: number | null;
  query: string;
  fileType: DocumentFileType | "";
  healthStatus: DocumentHealthStatus | "";
  sortBy: DocumentSortBy;
  sortOrder: SortOrder;
  /** 兼容既有任务与论文工作区；文档库新 UI 使用 healthStatus。 */
  parseStatus?: ParseStatus | "";
  indexStatus?: IndexStatus | "";
  researchReady?: boolean;
  needsAttention?: boolean;
  previewableOnly?: boolean;
}

export const DEFAULT_DOCUMENT_FILTERS: DocumentFilters = {
  mode: "document",
  knowledgeSourceId: null,
  query: "",
  fileType: "",
  healthStatus: "",
  sortBy: "updated_at",
  sortOrder: "desc",
};

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

function listQuery(filters: Readonly<Partial<DocumentFilters>>, offset: number, limit: number): URLSearchParams {
  const query = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
    mode: filters.mode ?? "document",
    sort_by: filters.sortBy ?? "updated_at",
    sort_order: filters.sortOrder ?? "desc",
  });
  if (filters.knowledgeSourceId != null) query.set("knowledge_source_id", String(filters.knowledgeSourceId));
  if (filters.query?.trim()) query.set("query", filters.query.trim());
  if (filters.fileType) query.set("file_type", filters.fileType);
  if (filters.healthStatus) query.set("health_status", filters.healthStatus);
  if (filters.parseStatus) query.set("parse_status", filters.parseStatus);
  if (filters.indexStatus) query.set("index_status", filters.indexStatus);
  if (filters.researchReady) query.set("health_status", "available");
  if (filters.needsAttention) query.set("health_status", "needs_attention");
  return query;
}

export const documentsApi = {
  list: (filters: Readonly<Partial<DocumentFilters>>, offset: number, limit: number) =>
    request<DocumentPage>(`?${listQuery({ ...filters, mode: "document" }, offset, limit).toString()}`),
  searchContent: (filters: Readonly<Partial<DocumentFilters>>, offset: number, limit: number) =>
    request<ContentSearchPage>(`?${listQuery({ ...filters, mode: "content" }, offset, limit).toString()}`),
  retryParse: (id: number) => request<DocumentRecord>(`/${id}/retry-parse`, { method: "POST" }),
  retryIndex: (id: number) => request<DocumentRecord>(`/${id}/retry-index`, { method: "POST" }),
  deleteIndex: (id: number) => request<DocumentRecord>(`/${id}/index`, { method: "DELETE" }),
  get: (id: number) => request<DocumentRecord>(`/${id}`),
  contentSummary: (id: number) => request<ContentSummary>(`/${id}/content-summary`),
  parse: (id: number) => request<ContentSummary>(`/${id}/parse`, { method: "POST" }),
  batchIndex: (documentIds: number[]) => request<BatchIndexResult>("/batch-index", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_ids: documentIds }) }),
  statistics: () => request<DocumentStatistics>("/statistics"),
  repair: (id: number) => request<{ document_id: number; action: string; task_id: number | null; status: string; health_status: DocumentHealthStatus }>(`/${id}/repair`, { method: "POST" }),
};
