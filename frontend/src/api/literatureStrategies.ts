import { apiRequest } from "./client";

export interface StrategyExecution {
  id: number;
  strategy_version_id: number;
  version: number;
  result_id: number | null;
  status: string;
  result_count: number;
  error_message: string | null;
  created_at: string;
  completed_at?: string | null;
  requested_retmax?: number;
  previous_result_id: number | null;
  added_count: number | null;
  removed_count: number | null;
  added_pmids: string[] | null;
  removed_pmids: string[] | null;
  has_changes: boolean | null;
}

export interface StrategyVersion {
  id: number;
  version: number;
  original_query: string;
  search_string: string;
  filters: string;
  model_version: string;
  term_groups: string[];
  mesh_terms: string[];
  start_year: number | null;
  end_year: number | null;
  change_summary: Record<string, unknown>;
  created_at: string;
}

export interface StrategyListItem {
  id: number;
  name: string;
  research_context_id: number | null;
  framework: string;
  is_pinned: boolean;
  is_archived: boolean;
  current_version: number;
  original_query: string;
  keyword_count: number;
  mesh_count: number;
  start_year: number | null;
  end_year: number | null;
  latest_execution: StrategyExecution | null;
}

export interface StrategyDetail {
  id: number;
  name: string;
  research_context_id: number | null;
  framework: string;
  database: string;
  is_pinned: boolean;
  is_archived: boolean;
  current_version: StrategyVersion;
  versions: StrategyVersion[];
  executions: StrategyExecution[];
  updated_at: string;
}

export interface StrategyComparison {
  from_version: number;
  to_version: number;
  changes: Record<string, unknown>;
}

export interface StrategyPage {
  total: number;
  offset: number;
  limit: number;
  items: StrategyListItem[];
}

export interface StrategyListFilters {
  query: string;
  researchContextId: string;
  framework: string;
  timeRange: string;
  sort: string;
  quickFilter: "all" | "changes" | "failed";
  archived: boolean;
}

function buildListQuery(offset: number, limit: number, filters: StrategyListFilters) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
    sort: filters.sort,
  });
  if (filters.query) params.set("q", filters.query);
  if (filters.researchContextId)
    params.set("research_context_id", filters.researchContextId);
  if (filters.framework) params.set("framework", filters.framework);
  if (filters.timeRange) {
    const createdFrom = new Date();
    createdFrom.setDate(createdFrom.getDate() - Number(filters.timeRange));
    params.set("created_from", createdFrom.toISOString());
  }
  if (filters.quickFilter === "changes") params.set("has_changes", "true");
  if (filters.quickFilter === "failed") params.set("execution_status", "failed");
  if (filters.archived) params.set("archived", "true");
  return params.toString();
}

export const literatureStrategiesApi = {
  list: (offset: number, limit: number, filters: StrategyListFilters) =>
    apiRequest<StrategyPage>(
      `/literature-search/history-strategies?${buildListQuery(offset, limit, filters)}`,
    ),
  get: (id: number) =>
    apiRequest<StrategyDetail>(`/literature-search/history-strategies/${id}`),
  patch: (
    id: number,
    payload: { name?: string; is_pinned?: boolean; research_context_id?: number | null },
  ) =>
    apiRequest<StrategyDetail>(`/literature-search/history-strategies/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  clone: (id: number) =>
    apiRequest<StrategyDetail>(`/literature-search/history-strategies/${id}/clone`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }),
  archive: (id: number) =>
    apiRequest<StrategyDetail>(`/literature-search/history-strategies/${id}/archive`, {
      method: "POST",
    }),
  restore: (id: number) =>
    apiRequest<StrategyDetail>(`/literature-search/history-strategies/${id}/restore`, {
      method: "POST",
    }),
  execute: (id: number, version: number, retmax = 20) =>
    apiRequest<StrategyExecution>(
      `/literature-search/history-strategies/${id}/versions/${version}/executions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ retmax }),
      },
    ),
  compareVersions: (id: number, fromVersion: number, toVersion: number) =>
    apiRequest<StrategyComparison>(
      `/literature-search/history-strategies/${id}/versions/${fromVersion}/compare/${toVersion}`,
    ),
  exportAll: () =>
    apiRequest<{ exported_at: string; total: number; strategies: StrategyDetail[] }>(
      "/literature-search/history-strategies/export/all",
    ),
};
