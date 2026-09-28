import { apiRequest } from "./client";

export type ReaderCapability = "available" | "unavailable" | "reserved" | "not_ready";
export type ReaderTab = "translation" | "copilot";

export interface ReaderBootstrap {
  paper: { paper_item_id: number; document_id: number; title: string | null; journal: string | null; year: number | null; paper_type: string | null; is_favorite: boolean; favorite_version?: number };
  document: { file_hash: string; page_count: number; content_url: string };
  revision_fence: { anchor_revision_id: number | null; segmentation_revision_id: number | null };
  resume: { session_id: number | null; page: number; viewport_offset_ratio: number };
  progress: { qualified_pages: number; total_pages: number; percent: number };
  outline: readonly { id: number; title: string; level: number; first_page: number; last_page: number }[];
  record_counts: { highlights: number; annotations: number; questions: number; bookmarks: number };
  preference: { view_mode: "original" | "bilingual" | "translated"; zoom_percent: number; left_panel_mode: string; left_collapsed: boolean; right_panel_tab: ReaderTab; focus_mode: boolean; version: number };
  capabilities: { outline: ReaderCapability; chapter_bundle: ReaderCapability; copilot: ReaderCapability; translation: ReaderCapability };
}

export interface ReaderSession { id: number; file_hash: string; page: number; viewport_offset_ratio: number; status: string; version: number }
export interface ReaderRecordSummary { highlights: number; annotations: number; questions: number; bookmarks: number }
export interface ReaderRecordSummaryResponse { counts: { highlight: number; annotation: number; question: number; bookmark: number }; total: number; counting_policy_version: string }
export interface ReaderRecord { record_id: string | number; record_type: "highlight" | "annotation" | "question" | "bookmark"; source_anchor_id: number | null; quote: string | null; text?: string | null; page_number: number | null; section_path: string | null; relocation_status: string; created_at: string }
export interface ReaderMessage { id: number; role: "user" | "assistant"; content: string; answer_status?: "answered" | "insufficient_evidence" | "failed"; citations: readonly { id: number; source_anchor_id?: number | null; evidence_text: string | null; page: number | null; section: string | null }[] }
export interface ReaderConversation { id: number; messages: readonly ReaderMessage[] }

const json = { "Content-Type": "application/json" } as const;
const key = () => crypto.randomUUID();

export const paperReaderApi = {
  bootstrap: (itemId: number, signal?: AbortSignal) => apiRequest<ReaderBootstrap>(`/paper-reader/items/${itemId}/bootstrap`, { signal }),
  createSession: (itemId: number, deviceId: string) => apiRequest<ReaderSession>(`/paper-reader/items/${itemId}/sessions`, { method: "POST", headers: { ...json, "Idempotency-Key": key() }, body: JSON.stringify({ device_id: deviceId }) }),
  updatePosition: (sessionId: number, payload: { page: number; viewport_offset_ratio: number; source_anchor_id?: number | null; expected_version: number; expected_file_hash: string }) => apiRequest<ReaderSession>(`/paper-reader/sessions/${sessionId}/position`, { method: "PATCH", headers: json, body: JSON.stringify(payload) }),
  closeSession: (sessionId: number) => apiRequest<ReaderSession>(`/paper-reader/sessions/${sessionId}/close`, { method: "POST" }),
  favorite: (itemId: number, isFavorite: boolean, expectedVersion: number) => apiRequest<{ is_favorite: boolean; version: number }>(`/paper-reader/items/${itemId}/favorite?${new URLSearchParams({ is_favorite: String(isFavorite), expected_version: String(expectedVersion) })}`, { method: "PUT" }),
  preference: (itemId: number, documentId: number, payload: { view_mode?: string; focus_mode?: boolean; left_collapsed?: boolean; right_panel_tab?: ReaderTab; expected_version: number }) => apiRequest<{ version: number }>(`/paper-reader/items/${itemId}/preferences?document_id=${documentId}`, { method: "PATCH", headers: json, body: JSON.stringify(payload) }),
  recordSummary: async (documentId: number): Promise<ReaderRecordSummary> => {
    const response = await apiRequest<ReaderRecordSummaryResponse | ReaderRecordSummary>(`/paper-reader/documents/${documentId}/records/summary`);
    return "counts" in response
      ? { highlights: response.counts.highlight, annotations: response.counts.annotation, questions: response.counts.question, bookmarks: response.counts.bookmark }
      : response;
  },
  records: (documentId: number, type?: string) => apiRequest<{ items: ReaderRecord[] }>(`/paper-reader/documents/${documentId}/records${type ? `?record_type=${encodeURIComponent(type)}` : ""}`),
  chapterBundle: (documentId: number, sectionId: number, anchorRevisionId: number, segmentationRevisionId: number) => apiRequest<{ title: string; segments: readonly { text: string }[] }>(`/paper-reader/documents/${documentId}/chapter-bundle?${new URLSearchParams({ section_id: String(sectionId), expected_anchor_revision_id: String(anchorRevisionId), expected_segmentation_revision_id: String(segmentationRevisionId) })}`),
  studyWorkspace: (itemId: number, researchContextId: number) => apiRequest<{ workspace_id: number; destination: string }>(`/paper-reader/items/${itemId}/study-workspace?research_context_id=${researchContextId}`, { method: "POST", headers: { "Idempotency-Key": key() } }),
  latestConversation: (documentId: number) => apiRequest<ReaderConversation>(`/conversations/latest?document_id=${documentId}`),
  createConversation: (documentId: number) => apiRequest<ReaderConversation>("/conversations", { method: "POST", headers: json, body: JSON.stringify({ document_ids: [documentId] }) }),
  ask: (conversationId: number, question: string, context: Partial<{ document_id: number; source_anchor_id: number | null; active_segment_id: string | null; section_id: number | null; expected_anchor_revision_id: number | null; expected_segmentation_revision_id: number | null }> = {}) => apiRequest<ReaderMessage>(`/conversations/${conversationId}/messages`, { method: "POST", headers: json, body: JSON.stringify({ question, ...context }) }),
};
