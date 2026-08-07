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
// ---------------------------------------------------------------------------
// R2-WP05 筛选 / 排序 / 分页
// ---------------------------------------------------------------------------

// 排序枚举：relevance（PubMed 返回顺序=天然相关性）/ newest（年份降序）/
// classic（期刊权威性+verified）/ custom（用户自定义序号）。与后端 Literal 对齐。
export type SearchSort = "relevance" | "newest" | "classic" | "custom";
// 已读状态：unread（未读）/ read（已读）。
export type ReadStatus = "unread" | "read";

// 单条结果（CitationItem 的前端镜像，字段名与后端一致）。
export interface CitationItem {
  pmid: string;
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
  publication_types: string[];
}

// 单条结果的用户态（saved / read_status / tags / 自定义排序序号）。
export interface ItemStateRead {
  saved: boolean;
  read_status: ReadStatus;
  tags: string[];
  custom_order_index: number | null;
}

// 单条结果 + 排序理由 + 用户态：排序理由由后端 ranking 生成，只描述真实信号。
export interface RankedCitationItem {
  item: CitationItem;
  sort_reason: string;
  state: ItemStateRead | null;
}

// 结果分页响应：total 为应用筛选后的总条数，items 为当前页带排序理由的条目。
export interface LiteratureSearchResultPage {
  result_id: number;
  query: string;
  total_count: number;
  filtered_total: number;
  page: number;
  page_size: number;
  sort: SearchSort;
  items: RankedCitationItem[];
}

// 白名单筛选/排序/分页参数，与后端 ResultQueryParams 对齐；空值表示不筛选。
export interface ResultQueryParams {
  year: number | null;
  publication_type: string;
  journal: string;
  author: string;
  has_abstract: boolean | null;
  saved: boolean | null;
  read_status: ReadStatus | "";
  tags: string;
  sort: SearchSort;
  page: number;
  page_size: number;
}

// 筛选表单只关心筛选字段（不含分页）；分页由 composable 单独管理。
export type ResultFilterValues = Omit<ResultQueryParams, "page" | "page_size">;

// 用户态写入：四个字段全部可选，只传想更新的字段（与后端 ItemStateUpdate 对齐）。
export interface ItemStateUpdate {
  saved?: boolean;
  read_status?: ReadStatus;
  tags?: string[];
  custom_order_index?: number;
}
export interface LiteratureSearchTaskRerun {
  task: LiteratureSearchTask;
  change: SearchResultChange | null;
  new_result_id: number;
}
export type DuplicateMatchMethod = "pmid" | "doi" | "title_normalized" | "author_year" | "manual";
export type DuplicateConfidence = "clear" | "fuzzy";
export type DuplicateResolutionAction = "keep_record" | "keep_all" | "merge_all" | "undo";
export interface DuplicateGroupMember { result_id: number; record_pmid: string; canonical_result_id: number | null; canonical_record_pmid: string | null; source_search_ids: number[]; }
export interface DuplicateGroup { id: number; trigger_task_id: number; match_method: DuplicateMatchMethod; confidence: DuplicateConfidence; status: string; created_at: string; members: DuplicateGroupMember[]; resolution: { resolved_at: string; resolved_action: DuplicateResolutionAction; resolved_by: string; } | null; }
export interface DuplicateGroupList { items: DuplicateGroup[]; }
export interface DuplicateResolveRequest { action: DuplicateResolutionAction; canonical_result_id?: number; canonical_record_pmid?: string; resolved_by?: string; }
export type FulltextStatus = "metadata_only" | "local_pdf_available" | "open_access_available" | "unavailable";
export interface LibraryItem { id: number; pmid: string; doi: string | null; title: string | null; journal: string | null; year: number | null; document_id: number | null; source_search_id: number; fulltext_status: FulltextStatus; fulltext_status_reason: string; created_at: string; updated_at: string; }
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
  items: ReadingOrderItem[];
}

// 生成阅读顺序的请求：manual_order 为用户已保存的人工顺序（完整 PMID 列表，
// 位置即顺序）；空列表表示"未调整过"，使用算法顺序。
export interface ReadingOrderRequest {
  manual_order: string[];
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
    structured_query: string;
    search_string: string;
    database: string;
    filters: string;
    model_version: string;
    user_edits: string;
    retmax: number;
  }) => apiRequest<LiteratureSearchTask>("/literature-search", { method: "POST", ...json, body: JSON.stringify(request) }),
  listTasks: (offset: number, limit: number) => apiRequest<LiteratureSearchTaskPage>(`/literature-search?offset=${offset}&limit=${limit}`),
  rerunTask: (id: number) => apiRequest<LiteratureSearchTaskRerun>(`/literature-search/${id}/rerun`, { method: "POST" }),
  // 检索结果分页（R2-WP05）：白名单参数拼入 query，page_size 恒 ≤100。
  getResults: (id: number, params: ResultQueryParams) => {
    const query = new URLSearchParams();
    if (params.year !== null) query.set("year", String(params.year));
    if (params.publication_type) query.set("publication_type", params.publication_type);
    if (params.journal) query.set("journal", params.journal);
    if (params.author) query.set("author", params.author);
    if (params.has_abstract !== null) query.set("has_abstract", String(params.has_abstract));
    if (params.saved !== null) query.set("saved", String(params.saved));
    if (params.read_status) query.set("read_status", params.read_status);
    if (params.tags) query.set("tags", params.tags);
    query.set("sort", params.sort);
    query.set("page", String(params.page));
    query.set("page_size", String(params.page_size));
    return apiRequest<LiteratureSearchResultPage>(`/literature-search/${id}/results?${query.toString()}`);
  },
  // 单条结果用户态读写（R2-WP05）：saved / read_status / tags / 自定义排序序号。
  updateItemState: (id: number, pmid: string, request: ItemStateUpdate) =>
    apiRequest<ItemStateRead>(`/literature-search/${id}/items/${pmid}/state`, { method: "PATCH", ...json, body: JSON.stringify(request) }),
  deduplicateTask: (id: number) => apiRequest<DuplicateGroupList>(`/literature-search/${id}/deduplicate`, { method: "POST" }),
  resolveDuplicateGroup: (id: number, request: DuplicateResolveRequest) =>
    apiRequest<DuplicateGroup>(`/duplicate-groups/${id}/resolve`, { method: "POST", ...json, body: JSON.stringify(request) }),
  saveToLibrary: (id: number, pmid: string) => apiRequest<LibraryItem>(`/literature-results/${id}/save`, { method: "POST", ...json, body: JSON.stringify({ pmid }) }),
  // 推荐阅读顺序（R2-WP08）：生成（可带 manual_order）与保存人工顺序（全量替换）。
  generateReadingOrder: (id: number, request: ReadingOrderRequest = { manual_order: [] }) =>
    apiRequest<ReadingOrder>(`/literature-search/${id}/reading-order`, { method: "POST", ...json, body: JSON.stringify(request) }),
  saveReadingOrder: (id: number, manualOrder: string[]) =>
    apiRequest<ReadingOrder>(`/literature-search/${id}/reading-order/order`, { method: "PUT", ...json, body: JSON.stringify({ manual_order: manualOrder }) }),
};
