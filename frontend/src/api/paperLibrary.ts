import { apiRequest } from "./client";

export type PaperView = "all" | "recent" | "reading" | "analyzing" | "unclassified";
export type PaperSort = "recent_activity" | "added_at" | "year" | "title";
export type ReadingStatus = "unread" | "reading" | "read";
export type AnalysisStatus = "not_started" | "pending" | "analyzing" | "completed" | "failed" | "cancelled";
export type ResearchRole = "core_evidence" | "background_support" | "method_reference" | "supplementary_reading" | "to_evaluate";
export type PreferredWorkAction = "reading" | "analysis";

export interface WorkEntry { action: string; enabled: boolean; reason: string | null; }
export interface PaperRelation { research_context_id: number; research_name: string; role: ResearchRole | null; note: string | null; version: number; }
export interface PaperActivity { id: number; kind: string; detail: string | null; created_at: string; }
export interface PaperItem {
  id: number; pmid: string | null; doi: string | null; title: string | null; authors: string | null; journal: string | null; year: number | null;
  paper_type: string | null; journal_quartile: string | null; journal_quartile_source: string | null; journal_quartile_year: number | null;
  metadata_status: string; metadata_source: string | null; metadata_retryable: boolean; metadata_error_code: string | null;
  document_id: number | null; fulltext_status: string; reading_status: ReadingStatus; reading_progress_percent: number; current_section: string | null;
  analysis_status: AnalysisStatus; analysis_progress: { completed: number; total: number } | null; primary_relation: PaperRelation | null;
  recent_activity: PaperActivity | null; additional_relation_count: number; tags: readonly string[]; can_read: boolean; can_analyze: boolean;
  capability_reason: string | null; preferred_work_action: PreferredWorkAction; last_work_at: string | null; reading_entry: WorkEntry; analysis_entry: WorkEntry;
}
export interface PaperOverview extends PaperItem { relations: readonly PaperRelation[]; activities: readonly PaperActivity[]; }
export interface PaperPage { items: readonly PaperItem[]; total: number; offset: number; limit: number; }
export interface PaperSummary { all: number; recent: number; reading: number; analyzing: number; unclassified: number; }
export interface FacetValue { value: string; count: number; label: string | null; }
export interface PaperFacets { reading_status: readonly FacetValue[]; analysis_status: readonly FacetValue[]; paper_types: readonly FacetValue[]; research_roles: readonly FacetValue[]; research_contexts: readonly FacetValue[]; tags: readonly FacetValue[]; }
export interface PaperFilters {
  view: PaperView; query: string; readingStatus: readonly ReadingStatus[]; analysisStatus: readonly AnalysisStatus[]; paperTypes: readonly string[];
  researchRoles: readonly ResearchRole[]; researchIds: readonly number[]; tags: readonly string[]; sort: PaperSort;
}
export interface PaperAddRequest { doi?: string; pmid?: string; document_id?: number; }
export interface PaperAddResult { item: PaperItem; outcome: "created" | "already_exists" | "linked"; }
export interface ResearchRelationUpdate { role: ResearchRole | null; note: string | null; expected_version: number | null; }

export const DEFAULT_PAPER_FILTERS: PaperFilters = {
  view: "all", query: "", readingStatus: [], analysisStatus: [], paperTypes: [], researchRoles: [], researchIds: [], tags: [], sort: "recent_activity",
};

function appendFilters(params: URLSearchParams, filters: Readonly<PaperFilters>): void {
  if (filters.query.trim()) params.set("query", filters.query.trim());
  filters.readingStatus.forEach((value) => params.append("reading_status", value));
  filters.analysisStatus.forEach((value) => params.append("analysis_status", value));
  filters.paperTypes.forEach((value) => params.append("paper_type", value));
  filters.researchRoles.forEach((value) => params.append("research_role", value));
  filters.researchIds.forEach((value) => params.append("research_id", String(value)));
  filters.tags.forEach((value) => params.append("tag", value));
}

function itemsPath(filters: Readonly<PaperFilters>, offset: number, limit: number): string {
  const params = new URLSearchParams({ view: filters.view, offset: String(Math.max(0, offset)), limit: String(limit), sort: filters.sort });
  appendFilters(params, filters);
  return `/paper-library/items?${params.toString()}`;
}

function facetsPath(filters: Readonly<PaperFilters>): string {
  const params = new URLSearchParams({ view: filters.view });
  appendFilters(params, filters);
  return `/paper-library/facets?${params.toString()}`;
}

const jsonHeaders = { "Content-Type": "application/json" } as const;

export const paperLibraryApi = {
  summary: (signal?: AbortSignal) => apiRequest<PaperSummary>("/paper-library/summary", { signal }),
  facets: (filters: Readonly<PaperFilters>, signal?: AbortSignal) => apiRequest<PaperFacets>(facetsPath(filters), { signal }),
  items: (filters: Readonly<PaperFilters>, offset: number, limit: number, signal?: AbortSignal) => apiRequest<PaperPage>(itemsPath(filters, offset, limit), { signal }),
  add: (payload: PaperAddRequest) => apiRequest<PaperAddResult>("/paper-library/items", { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) }),
  overview: (id: number, signal?: AbortSignal) => apiRequest<PaperOverview>(`/paper-library/items/${id}/overview`, { signal }),
  refreshMetadata: (id: number) => apiRequest<PaperItem>(`/paper-library/items/${id}/metadata/refresh`, { method: "POST" }),
  updateReadingState: (id: number, payload: { status: ReadingStatus; progress_percent: number; current_section: string | null }) => apiRequest<{ reading_status: ReadingStatus; reading_progress_percent: number; current_section: string | null }>(`/paper-library/items/${id}/reading-state`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify(payload) }),
  updateTags: (id: number, tags: readonly string[]) => apiRequest<string[]>(`/paper-library/items/${id}/tags`, { method: "PUT", headers: jsonHeaders, body: JSON.stringify({ tags }) }),
  activities: (id: number, signal?: AbortSignal) => apiRequest<PaperActivity[]>(`/paper-library/items/${id}/activities`, { signal }),
  upsertRelation: (id: number, researchId: number, payload: ResearchRelationUpdate) => apiRequest<PaperRelation>(`/paper-library/items/${id}/research-relations/${researchId}`, { method: "PUT", headers: jsonHeaders, body: JSON.stringify(payload) }),
  deleteRelation: (id: number, researchId: number, expectedVersion: number) => apiRequest<void>(`/paper-library/items/${id}/research-relations/${researchId}?expected_version=${expectedVersion}`, { method: "DELETE" }),
};
