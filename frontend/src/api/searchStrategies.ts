import { apiRequest } from "./client";
import type { LiteratureSearchTaskCreateResult } from "./literatureSearch";
import type {
  SearchStrategyDraft,
  SearchStrategyTerm,
  SearchStrategyVersion,
  StrategyCount,
  StrategyValidation,
  StrategyVersionComparison,
} from "../types/searchStrategy";

const jsonHeaders = { headers: { "Content-Type": "application/json" } };

export const searchStrategiesApi = {
  create: (request: {
    research_question: string;
    intent_mode: string;
    intent: object;
    limits: object;
    query_text: string;
    terms: Array<{
      text: string;
      concept_group: string;
      source: SearchStrategyTerm["source"];
      field_tag?: string | null;
      relation_type?: string | null;
      is_locked?: boolean;
    }>;
    mesh_terms: Array<{
      descriptor: string;
      mesh_id: string | null;
      concept_group: string;
      source: "nlm_mesh";
      verification_status: "verified" | "not_found" | "unavailable" | "stale";
      is_locked?: boolean;
    }>;
  }) =>
    apiRequest<SearchStrategyDraft>("/literature-search/strategies", { method: "POST", ...jsonHeaders, body: JSON.stringify(request) }),
  get: (strategyId: number) => apiRequest<SearchStrategyDraft>(`/literature-search/strategies/${strategyId}`),
  getLatestComplete: () => apiRequest<SearchStrategyDraft>("/literature-search/strategies/latest-complete"),
  patch: (strategyId: number, request: { revision: number; research_question?: string; intent_mode?: string; intent?: Record<string, unknown>; limits?: Record<string, unknown>; query_text?: string; query_source?: "generated" | "user_edited" }) =>
    apiRequest<SearchStrategyDraft>(`/literature-search/strategies/${strategyId}`, { method: "PATCH", ...jsonHeaders, body: JSON.stringify(request) }),
  execute: (strategyId: number) =>
    apiRequest<LiteratureSearchTaskCreateResult>(`/literature-search/strategies/${strategyId}/execute`, { method: "POST" }),
  refreshMesh: (strategyId: number) =>
    apiRequest<SearchStrategyDraft>(`/literature-search/strategies/${strategyId}/mesh/refresh`, { method: "POST" }),
  validate: (strategyId: number) =>
    apiRequest<StrategyValidation>(`/literature-search/strategies/${strategyId}/validate`, { method: "POST" }),
  count: (strategyId: number, fingerprint: string) =>
    apiRequest<StrategyCount>(`/literature-search/strategies/${strategyId}/count?fingerprint=${encodeURIComponent(fingerprint)}`, { method: "POST" }),
  addTerm: (strategyId: number, request: { text: string; concept_group: string; source: SearchStrategyTerm["source"]; field_tag?: string | null; relation_type?: string | null; is_locked?: boolean }) =>
    apiRequest<SearchStrategyTerm>(`/literature-search/strategies/${strategyId}/terms`, { method: "POST", ...jsonHeaders, body: JSON.stringify(request) }),
  patchTerm: (strategyId: number, termId: number, request: { text?: string; is_locked?: boolean }) =>
    apiRequest<SearchStrategyTerm>(`/literature-search/strategies/${strategyId}/terms/${termId}`, { method: "PATCH", ...jsonHeaders, body: JSON.stringify(request) }),
  deleteTerm: (strategyId: number, termId: number) =>
    apiRequest<void>(`/literature-search/strategies/${strategyId}/terms/${termId}`, { method: "DELETE" }),
  remapTerms: (strategyId: number) =>
    apiRequest<Pick<SearchStrategyDraft, "revision" | "fingerprint" | "terms">>(`/literature-search/strategies/${strategyId}/terms/remap`, { method: "POST" }),
  createVersion: (strategyId: number) =>
    apiRequest<SearchStrategyVersion>(`/literature-search/strategies/${strategyId}/versions`, { method: "POST" }),
  listVersions: (strategyId: number) =>
    apiRequest<SearchStrategyVersion[]>(`/literature-search/strategies/${strategyId}/versions`),
  compareVersions: (strategyId: number, fromVersion: number, toVersion: number) =>
    apiRequest<StrategyVersionComparison>(`/literature-search/strategies/${strategyId}/compare?from_version=${fromVersion}&to_version=${toVersion}`),
};
