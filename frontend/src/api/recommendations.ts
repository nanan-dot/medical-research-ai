import { apiRequest } from "./client";
import type { CitationItem } from "./literatureSearch";

export type RecommendationRunStatus = "queued" | "running" | "active" | "failed" | "cancelled" | "superseded";
export type RecommendationMode = "balanced" | "latest" | "key_evidence";
export type RecommendationDecisionStatus = "pending" | "accepted" | "dismissed";
export type DismissReason = "duplicate" | "off_topic" | "unsuitable_study_type" | "other";
export type RecommendationOverlap = "novel" | "covered";
export type RecommendationSort = "priority" | "created";

export interface RunError { code: string; message: string; provider: string | null }
export interface RecommendationRun {
  run_id: number; status: RecommendationRunStatus; operation: "created" | "reused"; active_run_id: number | null;
  mode: RecommendationMode; candidate_count: number; expected_count: number; completed_count: number; covered_count: number;
  algorithm_version: string; feature_schema_version: string; intent_snapshot_id: number | null; exploration_query: string | null; narration_status: "pending" | "running" | "completed" | "completed_with_fallback" | "skipped" | "not_requested" | "fallback_timeout" | "fallback_unavailable" | "fallback_rejected"; source_result_id: number;
  source_score_generation_id: number | null; last_error: RunError | null; warnings: string[]; pubmed_query: string | null;
  pubmed_total_count: number | null; collected_at: string | null; created_at: string; activated_at: string | null;
}
export interface RecommendationStatus { building: RecommendationRun | null; active: RecommendationRun | null; can_retry: boolean }
export interface MatchEvidence { dimension: string; status: string; matched_terms: string[]; source: string; field: string; reason: string; version: string; excerpt?: string | null }
export interface Limitation { code: string; message: string }
export interface RecommendationReason { headline: string; narrative: string; relevance: string | null; limitation: string | null; display_source: "base" | "polished"; matches: MatchEvidence[]; incremental_value: string | null; evidence_sources: string[]; limitations: Limitation[] }
export interface Decision { decision: RecommendationDecisionStatus; dismiss_reason: DismissReason | null }
export interface RecommendationItem {
  pmid: string; citation: CitationItem; priority_score: number | null; relevance_score: number | null;
  incremental_value_score: number | null; evidence_fit_score: number | null; recency_score: number | null;
  overlap_status: string; overlap_evidence: Array<{ collection: string; match: string }>;
  open_signal: { source: "openalex"; status: string; cited_by_count: number | null; counts_by_year: Record<number, number>; score: number | null };
  reason: RecommendationReason; rank: number; decision: Decision; narration_status: string;
}
export interface RecommendationPage {
  research_context_id: number; research_name: string; source_result_id: number; intent_snapshot_id: number | null; exploration_query: string | null; run_id: number;
  mode: RecommendationMode; algorithm_version: string; total: number; novel_count: number; covered_count: number;
  page: number; page_size: number; items: RecommendationItem[];
}

const json = { headers: { "Content-Type": "application/json" } };
const base = (resultId: number) => `/literature-search/${resultId}/recommendations`;
export const recommendationApi = {
  createRun: (resultId: number, request: { intent_snapshot_id: number | null; exploration_query?: string | null; mode: RecommendationMode; candidate_count: number; retry_failed?: boolean; force_refresh?: boolean }) => apiRequest<RecommendationRun>(`${base(resultId)}/runs`, { method: "POST", ...json, body: JSON.stringify(request) }),
  getStatus: (resultId: number, signal?: AbortSignal) => apiRequest<RecommendationStatus>(`${base(resultId)}/status`, { signal }),
  cancel: (resultId: number) => apiRequest<RecommendationRun>(`${base(resultId)}/cancel`, { method: "POST" }),
  getActive: (resultId: number, options: { page?: number; page_size?: number; sort?: RecommendationSort; overlap?: RecommendationOverlap }, signal?: AbortSignal) => { const query = new URLSearchParams({ page: String(options.page ?? 1), page_size: String(options.page_size ?? 20), sort: options.sort ?? "priority", overlap: options.overlap ?? "novel" }); return apiRequest<RecommendationPage>(`${base(resultId)}/active?${query}`, { signal }); },
  listRuns: (resultId: number, signal?: AbortSignal) => apiRequest<RecommendationRun[]>(`${base(resultId)}/runs`, { signal }),
  getRun: (resultId: number, runId: number, signal?: AbortSignal) => apiRequest<RecommendationRun>(`${base(resultId)}/runs/${runId}`, { signal }),
  getExplanation: (resultId: number, runId: number, pmid: string, signal?: AbortSignal) => apiRequest<RecommendationItem>(`${base(resultId)}/runs/${runId}/items/${encodeURIComponent(pmid)}/explanation`, { signal }),
  accept: (resultId: number, runId: number, pmid: string) => apiRequest<Decision>(`${base(resultId)}/runs/${runId}/items/${encodeURIComponent(pmid)}/accept`, { method: "POST" }),
  dismiss: (resultId: number, runId: number, pmid: string, reason: DismissReason) => apiRequest<Decision>(`${base(resultId)}/runs/${runId}/items/${encodeURIComponent(pmid)}/dismiss`, { method: "POST", ...json, body: JSON.stringify({ reason }) }),
};
