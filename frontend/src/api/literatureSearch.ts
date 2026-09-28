import { apiRequest } from "./client";

export const MAX_SEARCH_RESULTS = 500;

export interface DateRange { start_year: number | null; end_year: number | null; original_expression: string | null; }
export interface SearchIntentCandidate { topic: string; disease: string | null; intervention: string | null; comparison: string | null; outcome: string | null; target: string | null; mechanism: string | null; date_range: DateRange | null; study_types: string[]; language: string[]; exclusions: string[]; retmax: number; }
export interface ParsedQuery { raw_topic: string; candidate: SearchIntentCandidate; clarification_questions: string[]; candidate_source: "model_candidate" | "rule_fallback"; prompt_version: string; }
export interface SearchTermGroup { name: string; core_term: string; terms: string[]; field_tag: string | null; source: string; }
export interface MeshCandidate { descriptor: string; mesh_id: string; source: string; group_name: string; }
export interface ExpandedTerms { term_groups: SearchTermGroup[]; mesh_candidates: MeshCandidate[]; mesh_status_by_group?: Record<string, "verified" | "not_found" | "unavailable">; warnings: string[]; user_edits: Record<string, string[]>; }
export interface BuiltQuery { boolean_query: string; field_tags: Record<string, string>; explanations: string[]; user_edits: Record<string, string[]>; }
// 任务状态机：pending → running → succeeded / failed（R2-WP04）。
export type SearchTaskStatus = "pending" | "running" | "succeeded" | "failed";
export type ScoringRunStatus = "not_started" | "queued" | "collecting_inputs" | "scoring" | "validating" | "active" | "failed";
export interface ScoringStatus {
  active_generation_id: number | null;
  building_generation_id: number | null;
  status: ScoringRunStatus;
  completed: number;
  total: number;
  started_at: string | null;
  updated_at: string | null;
  algorithm_version: string | null;
  signals: Record<string, string>;
  last_error: string | null;
  can_retry: boolean;
}
export interface ScoringRun {
  generation_id: number;
  status: ScoringRunStatus;
  algorithm_version: string;
  operation: "created" | "reused";
}
export interface ScoreExplanation {
  result_id: number;
  pmid: string;
  generation_id: number;
  algorithm_version: string;
  eligibility: { status: string; reasons: string[] };
  components: Record<string, unknown>;
  evidence: Array<{ dimension?: string; matched_terms?: string[]; status?: string; source?: string; reason?: string | null; terms?: string[]; version?: string }>;
  limitations: string[];
}
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
  research_context_id?: number | null;
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
  strategy_fingerprint: string | null;
  versions: LiteratureSearchTaskVersion[];
}
export interface LiteratureSearchTaskPage {
  total: number;
  offset: number;
  limit: number;
  items: LiteratureSearchTask[];
}
export interface LiteratureSearchHistoryEntry {
  id: number;
  original_query: string;
  result_count: number;
  status: SearchTaskStatus;
  error_message: string | null;
  searched_at: string | null;
  latest_result_id: number | null;
  latest_change: SearchResultChange | null;
}
export interface LiteratureSearchHistoryPage {
  total: number;
  offset: number;
  limit: number;
  items: LiteratureSearchHistoryEntry[];
}
// ---------------------------------------------------------------------------
// R2-WP05 筛选 / 排序 / 分页
// ---------------------------------------------------------------------------

// 排序枚举：relevance（PubMed 返回顺序=天然相关性）/ newest（年份降序）/
// classic（期刊权威性+verified）/ custom（用户自定义序号）。与后端 Literal 对齐。
export type SearchSort = "recommended" | "relevance" | "popular" | "newest" | "article_impact" | "classic" | "evidence_fit" | "custom";
// 阅读状态：unread（未读）/ reading（在读）/ read（已读）。
export type ReadStatus = "unread" | "reading" | "read";

// 单条结果（CitationItem 的前端镜像，字段名与后端一致）。
export interface CitationItem {
  pmid: string;
  pmcid?: string | null;
  doi: string | null;
  title: string | null;
  authors: string[];
  journal: string | null;
  year: number | null;
  entry_type: string;
  verified: boolean;
  verified_by: string | null;
  verified_on: string | null;
  has_abstract: boolean;
  abstract: string | null;
  publication_types: string[];
  mesh_terms?: string[];
}

// 单条结果的用户态（saved / read_status / tags / 自定义排序序号）。
export interface ItemStateRead {
  saved: boolean;
  read_status: ReadStatus;
  tags: string[];
  custom_order_index: number | null;
  in_reading_plan: boolean;
  is_key: boolean;
}
export interface ScoreMetric { score: number | null; status: string; reason: string | null; }
export interface ScoreSummary {
  generation_id: number;
  algorithm_version: string;
  score_status: string;
  relevance: ScoreMetric;
  evidence_fit: ScoreMetric;
  article_impact: ScoreMetric;
  popularity: ScoreMetric;
  classic: ScoreMetric;
  recency: ScoreMetric;
  priority: ScoreMetric;
  cited_by_count: number | null;
  citation_source: "openalex" | null;
  citation_observed_at: string | null;
}
export interface JournalMetricSummary {
  status: string;
  match_method: string | null;
  latest: {
    impact_factor?: { value: number | null; year: number | null } | null;
    jcr?: { best_quartile: string | null; year: number | null } | null;
    wos?: { indexes: string[]; year: number | null } | null;
    cas?: { quartile: string | null; year: number | null; category?: string | null; is_top?: boolean | null } | null;
  } | null;
  reason: string | null;
}

// 单条结果 + 排序理由 + 用户态：排序理由由后端 ranking 生成，只描述真实信号。
export interface RankedCitationItem {
  item: CitationItem;
  sort_reason: string;
  state: ItemStateRead | null;
  library_item: LibraryItem | null;
  score_summary?: ScoreSummary | null;
  journal_metric?: JournalMetricSummary | null;
  limitations?: string[];
}

// 结果分页响应：total 为应用筛选后的总条数，items 为当前页带排序理由的条目。
export interface LiteratureSearchResultPage {
  result_id: number;
  query: string;
  total_count: number;
  filtered_total: number;
  reading_plan_total?: number;
  facets?: Record<string, Record<string, number>>;
  sort_capabilities?: Record<string, { available: boolean; reason: string | null }>;
  page: number;
  page_size: number;
  sort: SearchSort;
  requested_sort?: SearchSort;
  effective_sort?: SearchSort;
  active_generation_id?: number | null;
  scoring_status?: "not_started" | "building" | "active" | "failed";
  duplicate_mode?: "all" | "consolidated";
  hidden_duplicate_count?: number;
  items: RankedCitationItem[];
}

// 白名单筛选/排序/分页参数，与后端 ResultQueryParams 对齐；空值表示不筛选。
export interface ResultQueryParams {
  year: number | null;
  year_from?: number | null;
  year_to?: number | null;
  publication_type: string;
  journal: string;
  author: string;
  has_abstract: boolean | null;
  saved: boolean | null;
  read_status: ReadStatus | "";
  tags: string;
  jcr_quartile?: string;
  wos_index?: string;
  cas_quartile?: string;
  impact_factor_min?: number | null;
  cited_by_min?: number | null;
  sort: SearchSort;
  page: number;
  page_size: number;
  duplicate_mode: "all" | "consolidated";
}
function buildResultQuery(params: ResultQueryParams): URLSearchParams {
  const query = new URLSearchParams();
  if (params.year !== null) query.set("year", String(params.year));
  if (params.year_from != null) query.set("year_from", String(params.year_from));
  if (params.year_to != null) query.set("year_to", String(params.year_to));
  if (params.publication_type) query.set("publication_type", params.publication_type);
  if (params.journal) query.set("journal", params.journal);
  if (params.author) query.set("author", params.author);
  if (params.has_abstract !== null) query.set("has_abstract", String(params.has_abstract));
  if (params.saved !== null) query.set("saved", String(params.saved));
  if (params.read_status) query.set("read_status", params.read_status);
  if (params.tags) query.set("tags", params.tags);
  if (params.jcr_quartile) query.set("jcr_quartile", params.jcr_quartile);
  if (params.wos_index) query.set("wos_index", params.wos_index);
  if (params.cas_quartile) query.set("cas_quartile", params.cas_quartile);
  if (params.impact_factor_min != null) query.set("impact_factor_min", String(params.impact_factor_min));
  if (params.cited_by_min != null) query.set("cited_by_min", String(params.cited_by_min));
  query.set("sort", params.sort); query.set("page", String(params.page)); query.set("page_size", String(params.page_size)); query.set("duplicate_mode", params.duplicate_mode);
  return query;
}

// 筛选表单只关心筛选字段（不含分页）；分页由 composable 单独管理。
export type ResultFilterValues = Omit<ResultQueryParams, "page" | "page_size" | "duplicate_mode">;

// 用户态写入：四个字段全部可选，只传想更新的字段（与后端 ItemStateUpdate 对齐）。
export interface ItemStateUpdate {
  saved?: boolean;
  read_status?: ReadStatus;
  tags?: string[];
  custom_order_index?: number;
  in_reading_plan?: boolean;
  is_key?: boolean;
}

export interface BulkItemStateResult {
  updated: string[];
  failed: Array<{ pmid: string; reason: string }>;
}
export interface LiteratureSearchTaskRerun {
  task: LiteratureSearchTask;
  change: SearchResultChange | null;
  new_result_id: number;
}
export interface LiteratureSearchTaskCreateResult extends LiteratureSearchTask {
  operation: "created" | "reused";
  change: SearchResultChange | null;
  new_result_id: number;
}
export type DuplicateMatchMethod = "pmid" | "doi" | "title_normalized" | "author_year" | "manual";
export type DuplicateConfidence = "clear" | "fuzzy";
export type ResultDuplicateResolutionAction = "merge" | "keep_all" | "undo";
export interface DuplicateGroupMember { result_id: number; record_pmid: string; record_key: string | null; position: number | null; pmid: string | null; doi: string | null; title: string | null; authors: string[]; journal: string | null; year: number | null; publication_types: string[]; verified: boolean; has_abstract: boolean; withdrawn: boolean; is_canonical: boolean; visible_in_consolidated_view: boolean; canonical_result_id: number | null; canonical_record_pmid: string | null; source_search_ids: number[]; }
export interface DuplicateGroup { id: number; trigger_task_id: number; result_id: number | null; match_method: DuplicateMatchMethod; confidence: DuplicateConfidence; status: string; created_at: string; match_explanation: string; canonical_record_key: string | null; members: DuplicateGroupMember[]; resolution: { resolved_at: string; resolved_action: ResultDuplicateResolutionAction; resolved_by: string; } | null; }
export interface DuplicateGroupPage { total: number; offset: number; limit: number; items: DuplicateGroup[]; }
export interface ResultDuplicateResolutionRequest { action: ResultDuplicateResolutionAction; canonical_record_key?: string; resolved_by?: string; }
export interface ResultDuplicateResolution { group: DuplicateGroup; summary: DeduplicationSummary; }
export interface DeduplicationSummary { result_id: number; scanned_count: number; source_visible_count: number; consolidated_visible_count: number; hidden_record_count: number; clear_group_count: number; pending_group_count: number; resolved_merge_group_count: number; resolved_keep_all_group_count: number; has_scan: boolean; generated_at: string | null; }
export type FulltextStatus = "metadata_only" | "local_pdf_available" | "open_access_available" | "unavailable";
export interface LibraryItem { id: number; pmid: string; pmcid: string | null; doi: string | null; title: string | null; journal: string | null; year: number | null; document_id: number | null; source_search_id: number; fulltext_status: FulltextStatus; fulltext_status_reason: string; created_at: string; updated_at: string; }
// ---------------------------------------------------------------------------
// R2-WP08 推荐阅读顺序
// ---------------------------------------------------------------------------

// 证据金字塔层级：数值越小越先读，顺序固定为 综述 → 指南/共识 → 原始研究 → 前沿 → 高相关。
export type ReadingCategory = "review" | "guideline" | "original_research" | "frontier" | "highly_relevant";
// 排序来源：rule（算法顺序）/ manual（用户人工顺序优先）。
export type ReadingOrderSource = "rule" | "manual";

// 单条阅读顺序条目：category 由规则分类器依据真实字段得出；priority 为 1..n；
// reason 为可解释文本；evidence_features 为触发分类的真实特征列表。
export interface ReadingOrderItem {
  pmid: string;
  category: ReadingCategory;
  priority: number;
  reason: string;
  evidence_features: string[];
  title: string | null;
  year: number | null;
}

// 一次阅读顺序生成的结果：order_source 供前端明确展示排序来源。
export interface ReadingOrder {
  result_id: number;
  order_source: ReadingOrderSource;
  generated_at: string;
  duplicate_mode?: "all" | "consolidated";
  items: ReadingOrderItem[];
}

// 生成阅读顺序的请求：manual_order 为用户已保存的人工顺序（完整 PMID 列表，
// 位置即顺序）；空列表表示"未调整过"，使用算法顺序。
export interface ReadingOrderRequest {
  manual_order: string[];
  duplicate_mode?: "all" | "consolidated";
}
const json = { headers: { "Content-Type": "application/json" } };
export const literatureSearchApi = {
  parseQuery: (rawTopic: string) => apiRequest<ParsedQuery>("/literature-search/parse-query", { method: "POST", ...json, body: JSON.stringify({ raw_topic: rawTopic }) }),
  expandTerms: (candidate: SearchIntentCandidate, userEdits: Record<string, string[]>) => apiRequest<ExpandedTerms>("/literature-search/expand-terms", { method: "POST", ...json, body: JSON.stringify({ candidate, user_edits: userEdits }) }),
  buildQuery: (termGroups: SearchTermGroup[], userEdits: Record<string, string[]>) => apiRequest<BuiltQuery>("/literature-search/build-query", { method: "POST", ...json, body: JSON.stringify({ term_groups: termGroups, user_edits: userEdits }) }),
  // 检索任务与历史（R2-WP04）
  // 创建并立即执行检索任务：search_string 必须是 build-query 输出的布尔检索式
  //（用户可编辑），其余字段为输入快照，供重跑复现完整检索过程。
  createTask: (request: {
    original_query: string;
    research_context_id?: number;
    structured_query: string;
    search_string: string;
    database: string;
    filters: string;
    model_version: string;
    user_edits: string;
    retmax: number;
  }) => apiRequest<LiteratureSearchTaskCreateResult>("/literature-search", { method: "POST", ...json, body: JSON.stringify(request) }),
  listTasks: (offset: number, limit: number) => apiRequest<LiteratureSearchTaskPage>(`/literature-search?offset=${offset}&limit=${limit}`),
  getTask: (id: number) => apiRequest<LiteratureSearchTask>(`/literature-search/${id}`),
  bindTaskResearchContext: (id: number, researchContextId: number) =>
    apiRequest<LiteratureSearchTask>(`/literature-search/${id}/research-context`, {
      method: "PATCH",
      ...json,
      body: JSON.stringify({ research_context_id: researchContextId }),
    }),
  // 评分状态只读本地 generation；页面加载不会触发 PubMed 或开放数据请求。
  getScoringStatus: (id: number, signal?: AbortSignal) => apiRequest<ScoringStatus>(`/literature-search/${id}/scoring/status`, { signal }),
  createResearchIntent: (research_context_id: number, dimensions: Record<string, string>) =>
    apiRequest<{ id: number }>("/literature-search/research-intents", { method: "POST", ...json, body: JSON.stringify({ research_context_id, dimensions, confirmation_status: "user_confirmed" }) }),
  createScoringRun: (resultId: number, intent_snapshot_id: number, force_refresh = false) =>
    apiRequest<ScoringRun>(`/literature-search/${resultId}/scoring/runs`, { method: "POST", ...json, body: JSON.stringify({ intent_snapshot_id, include_external_metrics: true, include_pico: true, force_refresh }) }),
  cancelScoringRun: (resultId: number) =>
    apiRequest<ScoringRun>(`/literature-search/${resultId}/scoring/cancel`, { method: "POST" }),
  getScoreExplanation: (id: number, pmid: string, signal?: AbortSignal) => apiRequest<ScoreExplanation>(`/literature-search/${id}/items/${encodeURIComponent(pmid)}/score-explanation`, { signal }),
  listHistory: (offset: number, limit: number) => apiRequest<LiteratureSearchHistoryPage>(`/literature-search/history?offset=${offset}&limit=${limit}`),
  rerunTask: (id: number, retmax?: number) => apiRequest<LiteratureSearchTaskRerun>(
    `/literature-search/${id}/rerun`,
    retmax === undefined
      ? { method: "POST" }
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ retmax }) },
  ),
  // 检索结果分页（R2-WP05）：白名单参数拼入 query，page_size 恒 ≤100。
  getResults: (id: number, params: ResultQueryParams, signal?: AbortSignal) => {
    const query = buildResultQuery(params);
    return apiRequest<LiteratureSearchResultPage>(`/literature-search/${id}/results?${query.toString()}`, { signal });
  },
  exportResults: async (id: number, params: ResultQueryParams, format: "csv" | "ris" | "bibtex"): Promise<Blob> => {
    const query = buildResultQuery(params);
    query.set("format", format);
    const response = await fetch(`/api/v1/literature-search/${id}/results/export?${query.toString()}`);
    if (!response.ok) throw new Error("导出失败，请稍后重试");
    return response.blob();
  },
  // 单条结果用户态读写（R2-WP05）：saved / read_status / tags / 自定义排序序号。
  updateItemState: (id: number, pmid: string, request: ItemStateUpdate) =>
    apiRequest<ItemStateRead>(`/literature-search/${id}/items/${pmid}/state`, { method: "PATCH", ...json, body: JSON.stringify(request) }),
  updateItemStatesBulk: (id: number, pmids: string[], state: ItemStateUpdate) =>
    apiRequest<BulkItemStateResult>(`/literature-search/${id}/items/state/bulk`, { method: "PATCH", ...json, body: JSON.stringify({ pmids, state }) }),
  getDeduplicationSummary: (id: number) => apiRequest<DeduplicationSummary>(`/literature-search/results/${id}/deduplication`),
  runResultDeduplication: (id: number) => apiRequest<DeduplicationSummary>(`/literature-search/results/${id}/deduplication`, { method: "PUT" }),
  listResultDuplicateGroups: (id: number, status = "pending_resolution", offset = 0, limit = 20) => apiRequest<DuplicateGroupPage>(`/literature-search/results/${id}/duplicate-groups?status=${status}&offset=${offset}&limit=${limit}`),
  resolveResultDuplicateGroup: (resultId: number, groupId: number, request: ResultDuplicateResolutionRequest) => apiRequest<ResultDuplicateResolution>(`/literature-search/results/${resultId}/duplicate-groups/${groupId}/resolution`, { method: "POST", ...json, body: JSON.stringify(request) }),
  saveToLibrary: (id: number, pmid: string) => apiRequest<LibraryItem>(`/literature-results/${id}/save`, { method: "POST", ...json, body: JSON.stringify({ pmid }) }),
  // 推荐阅读顺序（R2-WP08）：生成（可带 manual_order）与保存人工顺序（全量替换）。
  generateReadingOrder: (id: number, request: ReadingOrderRequest = { manual_order: [] }) =>
    apiRequest<ReadingOrder>(`/literature-search/${id}/reading-order`, { method: "POST", ...json, body: JSON.stringify(request) }),
  saveReadingOrder: (id: number, manualOrder: string[], duplicateMode: "all" | "consolidated" = "all") =>
    apiRequest<ReadingOrder>(`/literature-search/${id}/reading-order/order`, { method: "PUT", ...json, body: JSON.stringify({ manual_order: manualOrder, duplicate_mode: duplicateMode }) }),
};
