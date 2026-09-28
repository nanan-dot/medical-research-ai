import type { DocumentFileType, DocumentRecord } from "./documents";

export type ResourceLibraryStatus =
  | "ai_available"
  | "processing"
  | "needs_processing"
  | "outdated"
  | "needs_attention"
  | "metadata_only";
export type ResourceSourceType = "local_folder" | "obsidian_vault" | "zotero_library" | "temporary_import";
export type ResourceSortBy = "updated_at" | "name" | "file_size" | "source_name" | "status" | "last_opened";
export type ResourceSortOrder = "asc" | "desc";

export interface ResourceLibrarySummary {
  total: number;
  processed: number;
  ai_available: number;
  processing: number;
  needs_attention: number;
  issue_breakdown: Record<string, number>;
  source_types: ReadonlyArray<{ source_type: ResourceSourceType; count: number }>;
  snapshot_at: string;
}

export interface ResourceFacetValue {
  value: string;
  count: number;
}

export interface ResourceLibraryFacets {
  sources: readonly ResourceFacetValue[];
  source_types: readonly ResourceFacetValue[];
  file_types: readonly ResourceFacetValue[];
  statuses: readonly ResourceFacetValue[];
}

export interface ResourceLibraryItem extends DocumentRecord {
  source_name: string;
  source_type: ResourceSourceType;
  relative_path: string;
  display_name: string;
  task_status: string | null;
  phase: string | null;
  current_item: string | null;
  last_opened_at: string | null;
  open_count: number;
  status: ResourceLibraryStatus;
  match_fields: readonly string[];
  snippet: string | null;
  locator: string | null;
}

export interface ResourceLibraryPage {
  items: ResourceLibraryItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface ResourceTreeNode {
  node_id: string;
  parent_id: string | null;
  name: string;
  relative_path: string;
  source_id: number | null;
  direct_count: number;
  descendant_count: number;
  health: "ready" | "unavailable" | "degraded" | string;
  children: ResourceTreeNode[];
}

export interface ResourceTreeGroup {
  source_type: "local" | "obsidian" | "zotero" | string;
  node_id: string;
  descendant_count: number;
  health: "ready" | "unavailable" | "degraded" | string;
  children: ResourceTreeNode[];
}

export interface ResourceSourceTree {
  groups: ResourceTreeGroup[];
}

export interface ResourceStorageSummary {
  managed_bytes: number;
  external_source_bytes: number;
  total_known_bytes: number;
  quota_bytes: number | null;
  usage_percent: number | null;
  status: "not_configured" | "within_quota" | "exceeded" | string;
  measured_at: string;
}

export interface ResourceImportItem {
  original_filename: string;
  status: string;
  document_id: number | null;
  task_id: number | null;
  error_code: string | null;
  message: string | null;
}

export interface ResourceLibraryFilters {
  query: string;
  sourceIds: number[];
  nodeId: string | null;
  fileTypes: DocumentFileType[];
  statuses: ResourceLibraryStatus[];
  updatedFrom: string | null;
  updatedTo: string | null;
  sortBy: ResourceSortBy;
  sortOrder: ResourceSortOrder;
}

export const DEFAULT_RESOURCE_LIBRARY_FILTERS: ResourceLibraryFilters = {
  query: "",
  sourceIds: [],
  nodeId: null,
  fileTypes: [],
  statuses: [],
  updatedFrom: null,
  updatedTo: null,
  sortBy: "updated_at",
  sortOrder: "desc",
};

const API_PREFIX = "/api/v1/library";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(payload?.error?.message ?? payload?.detail ?? "资料库请求失败");
  }
  return (await response.json()) as T;
}

function appendFilters(query: URLSearchParams, filters: Readonly<ResourceLibraryFilters>): void {
  if (filters.query.trim()) query.set("q", filters.query.trim());
  filters.sourceIds.forEach((value) => query.append("source_id", String(value)));
  filters.fileTypes.forEach((value) => query.append("file_type", value));
  filters.statuses.forEach((value) => query.append("health_status", value));
  if (filters.updatedFrom) query.set("updated_from", filters.updatedFrom);
  if (filters.updatedTo) query.set("updated_to", filters.updatedTo);
  if (filters.nodeId) query.set("tree_node_id", filters.nodeId);
}

function itemsQuery(filters: Readonly<ResourceLibraryFilters>, offset: number, limit: number): URLSearchParams {
  const query = new URLSearchParams({
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    offset: String(Math.max(0, offset)),
    limit: String(Math.min(Math.max(1, limit), 100)),
  });
  appendFilters(query, filters);
  return query;
}

export const resourceLibraryApi = {
  summary: (signal?: AbortSignal) => request<ResourceLibrarySummary>("/summary", { signal }),
  items: (filters: Readonly<ResourceLibraryFilters>, offset: number, limit: number, signal?: AbortSignal) => request<ResourceLibraryPage>(`/items?${itemsQuery(filters, offset, limit).toString()}`, { signal }),
  facets: (filters: Readonly<ResourceLibraryFilters>, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    appendFilters(query, filters);
    return request<ResourceLibraryFacets>(`/facets${query.size ? `?${query.toString()}` : ""}`, { signal });
  },
  sourceTree: (signal?: AbortSignal) => request<ResourceSourceTree>("/source-tree", { signal }),
  recent: (limit = 5, signal?: AbortSignal) => request<ResourceLibraryPage>(`/recent?offset=0&limit=${Math.min(Math.max(1, limit), 100)}`, { signal }),
  storage: (signal?: AbortSignal) => request<ResourceStorageSummary>("/storage", { signal }),
  item: (id: number, signal?: AbortSignal) => request<ResourceLibraryItem>(`/items/${id}`, { signal }),
  markOpened: (id: number, idempotencyKey: string) => request<{ document_id: number; open_count: number; last_opened_at: string; last_opened_by: string | null }>(`/items/${id}/opened`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idempotency_key: idempotencyKey }) }),
  repair: (id: number) => request<{ task_id: number }>(`/items/${id}/repair`, { method: "POST" }),
  reprocess: (id: number) => request<{ task_id: number }>(`/items/${id}/reprocess`, { method: "POST" }),
  imports: async (files: File[]) => {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    return request<{ items: ResourceImportItem[] }>("/imports", { method: "POST", body });
  },
};
