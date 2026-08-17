export type KnowledgeSourceType = "local_folder" | "obsidian_vault" | "temporary_import";
export type SyncStatus = "idle" | "scanning" | "completed" | "completed_with_errors" | "unavailable";

export interface SyncSummary {
  knowledge_source_id: number; sync_status: SyncStatus; last_sync_time: string | null;
  added: number; modified: number; deleted: number; skipped: number; failed: number; error_message: string | null;
}
export interface KnowledgeSourceStats {
  total_files: number;
  parsed: number;
  indexed: number;
  pending: number;
  failed: number;
}
export interface KnowledgeSource {
  id: number; name: string; source_type: KnowledgeSourceType; root_path: string; enabled: boolean;
  sync_status: SyncStatus; last_sync_time: string | null; error_message: string | null;
  stats: KnowledgeSourceStats;
}
export interface CreateKnowledgeSource { name: string; source_type: KnowledgeSourceType; root_path: string; enabled?: boolean; }
export interface ImportKnowledgeSourceDocument {
  file: File;
  knowledgeSourceId?: number;
  newSourceName?: string;
  relativeDirectory?: string;
}
export interface ImportedKnowledgeSourceDocument {
  document_id: number;
  knowledge_source_id: number;
  original_filename: string;
  stored_relative_path: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/knowledge-sources${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(payload?.error?.message ?? payload?.detail ?? "知识源请求失败");
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

async function importDocument(payload: ImportKnowledgeSourceDocument): Promise<ImportedKnowledgeSourceDocument> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (payload.knowledgeSourceId !== undefined) formData.append("knowledge_source_id", String(payload.knowledgeSourceId));
  if (payload.newSourceName) formData.append("new_source_name", payload.newSourceName);
  if (payload.relativeDirectory) formData.append("relative_directory", payload.relativeDirectory);
  const response = await fetch("/api/v1/knowledge-sources/import-document", { method: "POST", body: formData });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(body?.error?.message ?? body?.detail ?? "文档导入失败");
  }
  return await response.json() as ImportedKnowledgeSourceDocument;
}

export interface DirectoryBrowseResult { path: string | null; }

export const knowledgeSourcesApi = {
  list: () => request<KnowledgeSource[]>(""),
  create: (payload: CreateKnowledgeSource) => request<KnowledgeSource>("", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: { enabled: boolean }) => request<KnowledgeSource>(`/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: (id: number) => request<void>(`/${id}`, { method: "DELETE" }),
  sync: (id: number) => request<SyncSummary>(`/${id}/sync`, { method: "POST" }),
  browseDirectory: () => request<DirectoryBrowseResult>("/browse-directory", { method: "POST" }),
  importDocument,
};
