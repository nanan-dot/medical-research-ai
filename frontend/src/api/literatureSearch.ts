import { apiRequest } from "./client";

export interface DateRange { start_year: number | null; end_year: number | null; original_expression: string | null; }
export interface SearchIntentCandidate { topic: string; disease: string | null; intervention: string | null; target: string | null; mechanism: string | null; date_range: DateRange | null; study_types: string[]; language: string[]; exclusions: string[]; retmax: number; }
export interface ParsedQuery { raw_topic: string; candidate: SearchIntentCandidate; clarification_questions: string[]; candidate_source: "model_candidate" | "rule_fallback"; prompt_version: string; }
export const literatureSearchApi = { parseQuery: (rawTopic: string) => apiRequest<ParsedQuery>("/literature-search/parse-query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw_topic: rawTopic }) }) };
