export type KnowledgeSourceType = "local_folder" | "obsidian_vault" | "temporary_import";
export type SyncStatus = "idle" | "scanning" | "completed" | "completed_with_errors" | "unavailable";
export type KnowledgeSourceHealth = "ready" | "syncing" | "needs_attention" | "paused" | "unavailable";
export type KnowledgeSourceSort = "pinned" | "last_sync" | "last_opened" | "name" | "document_count";

export interface KnowledgeSourceStats {
  total_files: number; parsed: number; indexed: number; pending: number; failed: number;
  available?: number; processing?: number; needs_attention?: number; availability_percent?: number | null;
}
export interface KnowledgeSource {
  id: number; name: string; source_type: KnowledgeSourceType; root_path: string; enabled: boolean;
  auto_sync?: boolean; sync_interval_minutes?: number; next_auto_sync_at?: string | null; is_pinned?: boolean;
  sync_status: SyncStatus; health_status?: KnowledgeSourceHealth; last_sync_time: string | null;
  last_opened_at?: string | null; error_message: string | null; stats: KnowledgeSourceStats;
}
export interface KnowledgeBaseSummary {
  source_count: number; local_folder_count: number; obsidian_count: number; total_item_count: number;
  available_item_count: number; processing_item_count: number; needs_attention_count: number; affected_source_count: number;
  availability_percent: number | null;
  issue_breakdown: { parse_failed: number; unsupported_format: number; unavailable_file: number; index_failed: number; other: number };
}
export interface KnowledgeSourcePage { items: KnowledgeSource[]; total: number; offset: number; limit: number; }
export interface KnowledgeSourceQuery { q?: string; sourceType?: "local_folder" | "obsidian_vault"; healthStatus?: KnowledgeSourceHealth; enabled?: boolean; autoSync?: boolean; isPinned?: boolean; sortBy: KnowledgeSourceSort; sortOrder: "asc" | "desc"; offset: number; limit: number; }
export interface CreateKnowledgeSource { name: string; source_type: KnowledgeSourceType; root_path: string; enabled?: boolean; }
export interface SyncAccepted { task_id: number; knowledge_source_id: number; status: string; status_url: string; }
export interface DirectoryBrowseResult { path: string | null; }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/knowledge-sources${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(payload?.error?.message ?? payload?.detail ?? "知识源请求失败");
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}

function pageQuery(query: KnowledgeSourceQuery): string {
  const params = new URLSearchParams({ sort_by: query.sortBy, sort_order: query.sortOrder, offset: String(query.offset), limit: String(query.limit) });
  if (query.q?.trim()) params.set("q", query.q.trim());
  if (query.sourceType) params.set("source_type", query.sourceType);
  if (query.healthStatus) params.set("health_status", query.healthStatus);
  if (query.enabled !== undefined) params.set("enabled", String(query.enabled));
  if (query.autoSync !== undefined) params.set("auto_sync", String(query.autoSync));
  if (query.isPinned !== undefined) params.set("is_pinned", String(query.isPinned));
  return params.toString();
}

export const knowledgeSourcesApi = {
  list: () => request<KnowledgeSource[]>(""), page: (query: KnowledgeSourceQuery) => request<KnowledgeSourcePage>(`/page?${pageQuery(query)}`), summary: () => request<KnowledgeBaseSummary>("/summary"),
  create: (payload: CreateKnowledgeSource) => request<KnowledgeSource>("", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<Pick<KnowledgeSource, "name" | "enabled" | "auto_sync" | "is_pinned">>) => request<KnowledgeSource>(`/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: (id: number) => request<void>(`/${id}`, { method: "DELETE" }), sync: (id: number) => request<SyncAccepted>(`/${id}/sync`, { method: "POST" }),
  openDirectory: (id: number) => request<void>(`/${id}/open-directory`, { method: "POST" }), browseDirectory: () => request<DirectoryBrowseResult>("/browse-directory", { method: "POST" }),
};
