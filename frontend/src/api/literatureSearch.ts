import { apiRequest } from "./client";

export interface DateRange { start_year: number | null; end_year: number | null; original_expression: string | null; }
export interface SearchIntentCandidate { topic: string; disease: string | null; intervention: string | null; target: string | null; mechanism: string | null; date_range: DateRange | null; study_types: string[]; language: string[]; exclusions: string[]; retmax: number; }
export interface ParsedQuery { raw_topic: string; candidate: SearchIntentCandidate; clarification_questions: string[]; candidate_source: "model_candidate" | "rule_fallback"; prompt_version: string; }
export interface SearchTermGroup { name: string; core_term: string; terms: string[]; field_tag: string | null; source: string; }
export interface MeshCandidate { descriptor: string; mesh_id: string; source: string; group_name: string; }
export interface ExpandedTerms { term_groups: SearchTermGroup[]; mesh_candidates: MeshCandidate[]; warnings: string[]; user_edits: Record<string, string[]>; }
export interface BuiltQuery { boolean_query: string; field_tags: Record<string, string>; explanations: string[]; user_edits: Record<string, string[]>; }
const json = { headers: { "Content-Type": "application/json" } };
export const literatureSearchApi = {
  parseQuery: (rawTopic: string) => apiRequest<ParsedQuery>("/literature-search/parse-query", { method: "POST", ...json, body: JSON.stringify({ raw_topic: rawTopic }) }),
  expandTerms: (candidate: SearchIntentCandidate, userEdits: Record<string, string[]>) => apiRequest<ExpandedTerms>("/literature-search/expand-terms", { method: "POST", ...json, body: JSON.stringify({ candidate, user_edits: userEdits }) }),
  buildQuery: (termGroups: SearchTermGroup[], userEdits: Record<string, string[]>) => apiRequest<BuiltQuery>("/literature-search/build-query", { method: "POST", ...json, body: JSON.stringify({ term_groups: termGroups, user_edits: userEdits }) }),
};
