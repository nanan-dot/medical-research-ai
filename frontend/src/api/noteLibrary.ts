import { apiRequest } from "./client";

export const LOCAL_ACTOR_SCOPE = "local";
export type NoteView = "all" | "recent" | "favorite" | "unlinked_research" | "archived";
export interface NoteSourceSummary { source_type: string; source_id: number | null; title: string; status: string; }
export interface NoteContextSummary { id: number; name: string; }
export interface NoteListItem { id: number; current_revision: number; metadata_version: number; title: string; excerpt: string; is_favorite: boolean; is_archived: boolean; tags: string[]; research_context_ids: number[]; source_count: number; source_summaries: NoteSourceSummary[]; research_context_summaries: NoteContextSummary[]; content_updated_at: string; }
export interface NoteSource extends NoteSourceSummary { document_id: number | null; anchor_id: number | null; granularity: string; quote: string | null; url: string | null; capabilities: string[]; }
export interface NoteDraftSource { source_type: "document" | "paper" | "anchor"; source_id: number | null; source_version?: string | null; document_id: number | null; anchor_id: number | null; quote: string | null; title: string; url: string | null; }
export interface NoteRead extends Omit<NoteListItem, "excerpt" | "source_count" | "source_summaries" | "research_context_summaries"> { body: string; sources: NoteSource[]; capabilities: string[]; created_at: string; }
export interface NotePage { items: NoteListItem[]; total: number; all_total: number; page: number; page_size: number; query_fingerprint: string; as_of: string; }
export interface NoteFacets { tags: { id: string; name: string; count: number }[]; research_contexts: { id: number; name: string; count: number }[]; quick_counts: Record<NoteView, number>; }
export interface Draft { note_id: number; base_revision: number; draft_version: number; title: string; body: string; sources: NoteDraftSource[]; save_state: string; updated_at: string; }
export interface Revision { revision_no: number; title: string; body: string; origin: string; created_at: string; sources: NoteSource[]; }
export interface RevisionHistory { items: Revision[]; total: number; page: number; page_size: number; }
export interface NoteFilters { view: NoteView; query: string; tags: string[]; researchContextIds: number[]; page: number; pageSize: 20 | 50 | 100; }
export const DEFAULT_NOTE_FILTERS: NoteFilters = { view: "all", query: "", tags: [], researchContextIds: [], page: 1, pageSize: 20 };

function paramsFor(filters: NoteFilters): URLSearchParams {
  const params = new URLSearchParams({ actor_scope: LOCAL_ACTOR_SCOPE, view: filters.view, page: String(filters.page), page_size: String(filters.pageSize) });
  if (filters.query.trim()) params.set("query", filters.query.trim());
  filters.tags.forEach((tag) => params.append("tags", tag));
  filters.researchContextIds.forEach((id) => params.append("research_context_ids", String(id)));
  return params;
}
const json = (value: unknown): RequestInit => ({ headers: { "content-type": "application/json" }, body: JSON.stringify(value) });
export const noteLibraryApi = {
  list(filters: NoteFilters, signal?: AbortSignal) { return apiRequest<NotePage>(`/note-library/notes?${paramsFor(filters)}`, { signal }); },
  facets(filters: Pick<NoteFilters, "query" | "tags" | "researchContextIds">, signal?: AbortSignal) { const params = paramsFor({ ...DEFAULT_NOTE_FILTERS, ...filters }); params.delete("view"); params.delete("page"); params.delete("page_size"); return apiRequest<NoteFacets>(`/note-library/facets?${params}`, { signal }); },
  get(noteId: number, signal?: AbortSignal) { return apiRequest<NoteRead>(`/note-library/notes/${noteId}?actor_scope=${LOCAL_ACTOR_SCOPE}`, { signal }); },
  create(title = "", body = "") { return apiRequest<NoteRead>("/note-library/notes", { method: "POST", ...json({ actor_scope: LOCAL_ACTOR_SCOPE, title, body, sources: [] }) }); },
  getDraft(noteId: number) { return apiRequest<Draft>(`/note-library/notes/${noteId}/draft?actor_scope=${LOCAL_ACTOR_SCOPE}`); },
  saveDraft(noteId: number, input: { expectedDraftVersion: number; title: string; body: string; sources: NoteDraftSource[] }) { return apiRequest<Draft>(`/note-library/notes/${noteId}/draft`, { method: "PUT", ...json({ actor_scope: LOCAL_ACTOR_SCOPE, expected_draft_version: input.expectedDraftVersion, title: input.title, body: input.body, sources: input.sources }) }); },
  commit(noteId: number, input: { expectedBaseRevision: number; expectedDraftVersion: number; idempotencyKey: string }) { return apiRequest<Revision>(`/note-library/notes/${noteId}/revisions`, { method: "POST", ...json({ actor_scope: LOCAL_ACTOR_SCOPE, expected_base_revision: input.expectedBaseRevision, expected_draft_version: input.expectedDraftVersion, idempotency_key: input.idempotencyKey }) }); },
  metadata(noteId: number, expectedMetadataVersion: number, patch: { is_favorite?: boolean; tags?: string[]; research_context_ids?: number[] }) { return apiRequest<NoteRead>(`/note-library/notes/${noteId}/metadata`, { method: "PATCH", ...json({ actor_scope: LOCAL_ACTOR_SCOPE, expected_metadata_version: expectedMetadataVersion, ...patch }) }); },
  archive(noteId: number, archived: boolean) { return apiRequest<NoteRead>(`/note-library/notes/${noteId}/${archived ? "archive" : "unarchive"}`, { method: "POST", ...json({ actor_scope: LOCAL_ACTOR_SCOPE }) }); },
  history(noteId: number, page = 1) { return apiRequest<RevisionHistory>(`/note-library/notes/${noteId}/revisions?actor_scope=${LOCAL_ACTOR_SCOPE}&page=${page}&page_size=20`); },
  revision(noteId: number, revisionNo: number) { return apiRequest<Revision>(`/note-library/notes/${noteId}/revisions/${revisionNo}?actor_scope=${LOCAL_ACTOR_SCOPE}`); },
  restore(noteId: number, revisionNo: number, expectedBaseRevision: number, idempotencyKey: string) { return apiRequest<Revision>(`/note-library/notes/${noteId}/restore`, { method: "POST", ...json({ actor_scope: LOCAL_ACTOR_SCOPE, revision_no: revisionNo, expected_base_revision: expectedBaseRevision, idempotency_key: idempotencyKey }) }); },
};
