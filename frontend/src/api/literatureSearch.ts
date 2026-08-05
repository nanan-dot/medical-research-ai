import { apiRequest } from "./client";

export interface DateRange { start_year: number | null; end_year: number | null; original_expression: string | null; }
export interface SearchIntentCandidate { topic: string; disease: string | null; intervention: string | null; target: string | null; mechanism: string | null; date_range: DateRange | null; study_types: string[]; language: string[]; exclusions: string[]; retmax: number; }
export interface ParsedQuery { raw_topic: string; candidate: SearchIntentCandidate; clarification_questions: string[]; candidate_source: "model_candidate" | "rule_fallback"; prompt_version: string; }
export interface SearchTermGroup { name: string; core_term: string; terms: string[]; field_tag: string | null; source: string; }
export interface MeshCandidate { descriptor: string; mesh_id: string; source: string; group_name: string; }
export interface ExpandedTerms { term_groups: SearchTermGroup[]; mesh_candidates: MeshCandidate[]; warnings: string[]; user_edits: Record<string, string[]>; }
export interface BuiltQuery { boolean_query: string; field_tags: Record<string, string>; explanations: string[]; user_edits: Record<string, string[]>; }
// 任务状态机：pending → running → succeeded / failed（R2-WP04）。
export type SearchTaskStatus = "pending" | "running" | "succeeded" | "failed";
export interface SearchResultChange {
  previous_count: number;
  current_count: number;
  count_delta: number;
  added_count: number;
  removed_count: number;
  added_pmids: string[];
  removed_pmids: string[];
}
export interface LiteratureSearchTaskVersion {
  version: number;
  result_id: number;
  searched_at: string;
  result_count: number;
  change: SearchResultChange | null;
}
export interface LiteratureSearchTask {
  id: number;
  original_query: string;
  structured_query: string;
  search_string: string;
  database: string;
  result_count: number;
  retmax: number;
  filters: string;
  model_version: string;
  user_edits: string;
  status: SearchTaskStatus;
  error_message: string | null;
  created_at: string;
  searched_at: string | null;
  latest_result_id: number | null;
  versions: LiteratureSearchTaskVersion[];
}
export interface LiteratureSearchTaskPage {
  total: number;
  offset: number;
  limit: number;
  items: LiteratureSearchTask[];
}
export interface LiteratureSearchTaskRerun {
  task: LiteratureSearchTask;
  change: SearchResultChange | null;
  new_result_id: number;
}
const json = { headers: { "Content-Type": "application/json" } };
export const literatureSearchApi = {
  parseQuery: (rawTopic: string) => apiRequest<ParsedQuery>("/literature-search/parse-query", { method: "POST", ...json, body: JSON.stringify({ raw_topic: rawTopic }) }),
  expandTerms: (candidate: SearchIntentCandidate, userEdits: Record<string, string[]>) => apiRequest<ExpandedTerms>("/literature-search/expand-terms", { method: "POST", ...json, body: JSON.stringify({ candidate, user_edits: userEdits }) }),
  buildQuery: (termGroups: SearchTermGroup[], userEdits: Record<string, string[]>) => apiRequest<BuiltQuery>("/literature-search/build-query", { method: "POST", ...json, body: JSON.stringify({ term_groups: termGroups, user_edits: userEdits }) }),
  // 检索任务与历史（R2-WP04）
  listTasks: (offset: number, limit: number) => apiRequest<LiteratureSearchTaskPage>(`/literature-search?offset=${offset}&limit=${limit}`),
  rerunTask: (id: number) => apiRequest<LiteratureSearchTaskRerun>(`/literature-search/${id}/rerun`, { method: "POST" }),
};
