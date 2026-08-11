import { apiRequest } from "./client";

export interface DocumentNavigationRequest { query: string; knowledge_source_id?: number; indexed_only: boolean; limit?: number; }
export interface NavigationResult { document_id: number; title: string; filename: string; knowledge_source_id: number; knowledge_source_name: string; relative_path: string; match_reason: string; location: { page_number: number | null; section: string | null }; excerpt: string; retrieval_score: number | null; condition_status: NavigationCondition[]; }
export interface NavigationCondition { label: string; status: "verified" | "unverified" | "not_requested"; reason: string; }
export interface DocumentNavigationResponse { query: string; knowledge_source_id: number | null; indexed_only: boolean; searchable_document_count: number; strategy: "hybrid" | "bm25"; fallback_reason: string | null; conditions: NavigationCondition[]; results: NavigationResult[]; }

export const documentNavigationApi = {
  search: (payload: DocumentNavigationRequest, signal?: AbortSignal) => apiRequest<DocumentNavigationResponse>("/document-navigation/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal }),
};
