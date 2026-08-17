"""Literature search API structures."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.library_item.schema import LibraryItemRead
from app.modules.literature_search.query_model import MAX_RETMX, SearchIntentCandidate


class LiteratureSearchCreate(BaseModel):
    pass


class LiteratureSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ----------------------------------------------------------------------
# R2-WP04：检索任务（literature search task）
# ----------------------------------------------------------------------

# 任务状态机：pending → running → succeeded / failed。
SearchTaskStatus = Literal["pending", "running", "succeeded", "failed"]
# 数据库枚举：当前仅支持 PubMed，扩展前必须先扩展枚举与执行逻辑。
SearchDatabase = Literal["pubmed"]


class LiteratureSearchTaskCreate(BaseModel):
    """创建检索任务的请求。

    original_query 为用户原始主题；search_string 是发往 PubMed 的布尔检索式，
    必须来自 build-query 的输出（经用户编辑）。structured_query / filters /
    user_edits 为可选的输入快照，用于重跑时复现完整检索过程。
    """

    original_query: str = Field(min_length=1, max_length=1000)
    structured_query: str = Field(default="", max_length=20000)
    search_string: str = Field(min_length=1, max_length=2000)
    database: SearchDatabase = "pubmed"
    filters: str = Field(default="", max_length=5000)
    model_version: str = Field(min_length=1, max_length=200)
    user_edits: str = Field(default="", max_length=20000)
    retmax: int = Field(default=20, ge=1, le=MAX_RETMX)


class LiteratureSearchTaskVersion(BaseModel):
    """任务的一个结果版本（引用结果，不复制 items_json）。

    change 为重跑后相对上一版本的变化摘要；首个版本 change 为 None。
    """

    version: int
    result_id: int
    searched_at: datetime
    result_count: int
    change: "SearchResultChange | None" = None


class SearchResultChange(BaseModel):
    """新旧版本对比摘要：结果数量与条目集合的变化。"""

    previous_count: int
    current_count: int
    count_delta: int
    added_count: int
    removed_count: int
    added_pmids: list[str] = Field(default_factory=list)
    removed_pmids: list[str] = Field(default_factory=list)


class LiteratureSearchTaskRead(BaseModel):
    """检索任务详情（含全部版本，不含正文摘录）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    original_query: str
    structured_query: str
    search_string: str
    database: str
    result_count: int
    retmax: int
    filters: str
    model_version: str
    user_edits: str
    status: SearchTaskStatus
    error_message: str | None = None
    created_at: datetime
    searched_at: datetime | None = None
    latest_result_id: int | None = None
    # 策略指纹（稳定序列化后的 SHA-256）：供历史页按真实策略分组，
    # 与 createTask 的 operation=reused 判定口径一致，避免前端自行拼快照产生偏差。
    strategy_fingerprint: str | None = None
    versions: list[LiteratureSearchTaskVersion] = Field(default_factory=list)


class LiteratureSearchTaskList(BaseModel):
    """检索历史列表页（分页；不携带条目明细，避免响应过大）。"""

    total: int
    offset: int
    limit: int
    items: list[LiteratureSearchTaskRead]


class LiteratureSearchHistoryEntry(BaseModel):
    """One user-facing research record, aggregated from equivalent task snapshots."""

    id: int
    original_query: str
    result_count: int
    status: SearchTaskStatus
    error_message: str | None = None
    searched_at: datetime | None = None
    latest_result_id: int | None = None
    latest_change: "SearchResultChange | None" = None


class LiteratureSearchHistoryList(BaseModel):
    """Paginated research-record history; raw task audit rows stay internal."""

    total: int
    offset: int
    limit: int
    items: list[LiteratureSearchHistoryEntry]


class LiteratureSearchTaskRerun(BaseModel):
    """重跑任务后返回的更新后任务详情。"""

    task: LiteratureSearchTaskRead
    change: "SearchResultChange | None" = None
    new_result_id: int


class LiteratureSearchTaskRerunRequest(BaseModel):
    """Optional execution limit for a new rerun snapshot."""

    retmax: int | None = Field(default=None, ge=1, le=MAX_RETMX)


class LiteratureSearchTaskCreateResult(LiteratureSearchTaskRead):
    """创建或复用策略后的真实执行结果。"""

    operation: Literal["created", "reused"]
    change: "SearchResultChange | None" = None
    new_result_id: int


class SearchStrategyExport(BaseModel):
    """PRISMA-compliant 检索策略导出（数据库、检索日期、查询串、结果数）。"""

    original_query: str
    database: str
    search_string: str
    searched_at: datetime
    result_count: int
    filters: str
    model_version: str
    status: SearchTaskStatus


# 前向引用在 Pydantic 2 中需通过 model_rebuild 解析。
LiteratureSearchTaskVersion.model_rebuild()
LiteratureSearchTaskRerun.model_rebuild()
LiteratureSearchTaskCreateResult.model_rebuild()


class ParseQueryRequest(BaseModel):
    raw_topic: str = Field(min_length=1, max_length=1000)


class ParseQueryResponse(BaseModel):
    raw_topic: str
    candidate: SearchIntentCandidate
    clarification_questions: list[str]
    candidate_source: str
    prompt_version: str


class SearchTermGroup(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    core_term: str = Field(min_length=1, max_length=200)
    terms: list[str] = Field(default_factory=list, max_length=20)
    field_tag: str | None = Field(default="Title/Abstract", max_length=80)
    source: str = Field(default="user_supplied", max_length=80)


class MeshCandidate(BaseModel):
    descriptor: str = Field(min_length=1, max_length=300)
    mesh_id: str = Field(min_length=1, max_length=80)
    source: str = Field(default="NLM MeSH", max_length=80)
    group_name: str = Field(min_length=1, max_length=80)


class ExpandTermsRequest(BaseModel):
    candidate: SearchIntentCandidate
    user_edits: dict[str, list[str]] = Field(default_factory=dict)


class ExpandTermsResponse(BaseModel):
    term_groups: list[SearchTermGroup]
    mesh_candidates: list[MeshCandidate]
    warnings: list[str] = Field(default_factory=list)
    user_edits: dict[str, list[str]] = Field(default_factory=dict)


class BuildQueryRequest(BaseModel):
    term_groups: list[SearchTermGroup] = Field(min_length=1, max_length=10)
    user_edits: dict[str, list[str]] = Field(default_factory=dict)


class BooleanQueryResult(BaseModel):
    boolean_query: str
    field_tags: dict[str, str]
    explanations: list[str]


class BuildQueryResponse(BooleanQueryResult):
    user_edits: dict[str, list[str]]


class SearchExecuteRequest(BaseModel):
    """执行 PubMed 检索的请求。

    boolean_query 来自 build-query 输出，是用户可编辑的检索式；此处只做长度与
    空白校验，不重新解析语义，避免在传输层二次改写用户的检索意图。
    """

    boolean_query: str = Field(min_length=1, max_length=2000)
    retmax: int = Field(default=20, ge=1, le=MAX_RETMX)


class CitationItem(BaseModel):
    """单条文献检索结果（含引用反幻觉验证标记）。

    verified 只反映数据来源：true 表示字段来自 PubMed 真实 API 响应；
    false 表示本次检索未能验证（如 PMID 存在但摘要缺失），绝不来自记忆补全。

    has_abstract / publication_types 自 R2-WP05 起由 PubMedExecutor 依据
    EFetch 真实摘要与文献类型字段如实打标；旧快照缺这两个字段时默认为
    False / 空列表，不会谎称"有摘要"或伪造文献类型。
    """

    model_config = ConfigDict(frozen=True)

    pmid: str = Field(min_length=1, max_length=20)
    doi: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=1000)
    authors: list[str] = Field(default_factory=list)
    journal: str | None = Field(default=None, max_length=500)
    year: int | None = Field(default=None)
    entry_type: str = Field(default="article", max_length=32)
    verified: bool = False
    verified_by: str | None = Field(default=None, max_length=40)
    verified_on: str | None = Field(default=None, max_length=40)
    has_abstract: bool = False
    publication_types: list[str] = Field(default_factory=list)
    abstract: str | None = None
    withdrawn: bool = False


class LiteratureSearchResultRead(BaseModel):
    """检索执行结果（不含正文摘录，避免暴露超长内容）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    total_count: int
    created_at: datetime
    items: list[CitationItem]


# ----------------------------------------------------------------------
# R2-WP05：筛选、排序与分页
# ----------------------------------------------------------------------

# 排序枚举：relevance（PubMed 返回顺序=天然相关性）/ newest（年份降序）/
# classic（期刊权威性+verified）/ custom（用户自定义序号升序）。
SearchSort = Literal["relevance", "newest", "classic", "custom"]

# 已读状态枚举：unread（未读）/ read（已读）。
ReadStatus = Literal["unread", "read"]


class ResultQueryParams(BaseModel):
    """GET /literature-search/{id}/results 的筛选/排序/分页参数。

    白名单设计：FastAPI 只接受本模型声明的字段，未知 query 参数被 FastAPI
    忽略（不会静默改判）。year 为单个整数（精确年份）；journal / author /
    tags 为子串包含匹配；publication_type 与 publication_types 条目做不区分
    大小写的包含匹配。筛选在服务端对 items_json 快照做内存过滤，不改写快照。
    """

    year: int | None = Field(default=None, ge=1900, le=2100)
    publication_type: str | None = Field(default=None, max_length=100)
    journal: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=500)
    has_abstract: bool | None = None
    saved: bool | None = None
    read_status: ReadStatus | None = None
    tags: str | None = Field(default=None, max_length=500)
    sort: SearchSort = "relevance"
    duplicate_mode: Literal["all", "consolidated"] = "all"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RankedCitationItem(BaseModel):
    """带排序理由与用户态的单条结果，在前端结果卡片上直接展示可解释性。

    sort_reason 由 ranking 模块生成，只描述本次检索内采用的排序信号
    （如 "top journal + recent year" / "verified by pubmed" / "year unknown"），
    绝不包含虚构的被引次数或影响因子。state 由 service 在装配分页响应时并入，
    ranking 纯函数本身不感知用户态。
    """

    item: CitationItem
    sort_reason: str
    state: "ItemStateRead | None" = None
    library_item: LibraryItemRead | None = None


class LiteratureSearchResultPage(BaseModel):
    """结果分页响应：items 为当前页带排序理由的条目，另返回过滤后总数。

    total 是应用筛选后的总条数（用于前端分页条），而非 ESearch 原始命中数。
    page_size 恒小于等于 100，页码越界时 items 为空列表而非 500。
    """

    result_id: int
    query: str
    total_count: int
    filtered_total: int
    page: int
    page_size: int
    sort: SearchSort
    duplicate_mode: Literal["all", "consolidated"] = "all"
    hidden_duplicate_count: int = 0
    items: list[RankedCitationItem]


class ItemStateUpdate(BaseModel):
    """单条结果用户态写入（saved / read_status / tags / 自定义排序序号）。

    四个字段全部可选：调用方只传想更新的字段。saved 为整体布尔标记；
    read_status 只能是 unread/read；tags 整体替换（去重、去空、限长）。
    custom_order_index 为用户拖拽顺序后的序号（custom 排序使用），写入后
    该条记录在 custom 排序中按序号升序排位。
    """

    saved: bool | None = None
    read_status: ReadStatus | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    custom_order_index: int | None = Field(default=None, ge=0, le=100000)


class ItemStateRead(BaseModel):
    """单条结果用户态读取响应（GET 时并入分页响应每个条目）。

    tags 为当前标签列表（已按规范去重、限长）；custom_order_index 为
    用户自定义排序序号（未设置时为 None）。
    """

    saved: bool
    read_status: ReadStatus
    tags: list[str]
    custom_order_index: int | None = None


# ----------------------------------------------------------------------
# R2-WP06：可撤销文献去重
# ----------------------------------------------------------------------

DuplicateMatchMethod = Literal[
    "pmid", "doi", "title_normalized", "author_year", "manual"
]
DuplicateConfidence = Literal["clear", "fuzzy"]
DuplicateGroupStatus = Literal[
    "pending_resolution", "auto_merged", "resolved_keep_all", "resolved_merged"
]
DuplicateResolutionAction = Literal["keep_record", "keep_all", "merge_all", "undo"]


class DuplicateGroupMemberRead(BaseModel):
    result_id: int
    record_pmid: str
    record_key: str | None = None
    position: int | None = None
    pmid: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    publication_types: list[str] = Field(default_factory=list)
    verified: bool = False
    has_abstract: bool = False
    withdrawn: bool = False
    is_canonical: bool = False
    visible_in_consolidated_view: bool = True
    canonical_result_id: int | None
    canonical_record_pmid: str | None
    source_search_ids: list[int]


class DuplicateResolutionRead(BaseModel):
    resolved_at: datetime
    resolved_action: DuplicateResolutionAction
    resolved_by: str


class DuplicateGroupRead(BaseModel):
    id: int
    trigger_task_id: int
    result_id: int | None = None
    match_method: DuplicateMatchMethod
    confidence: DuplicateConfidence
    status: DuplicateGroupStatus
    created_at: datetime
    match_explanation: str
    canonical_record_key: str | None = None
    members: list[DuplicateGroupMemberRead]
    resolution: DuplicateResolutionRead | None


class DuplicateGroupList(BaseModel):
    items: list[DuplicateGroupRead]


class DeduplicationSummary(BaseModel):
    """当前不可变结果快照的去重工作视图摘要。"""

    result_id: int
    scanned_count: int
    source_visible_count: int
    consolidated_visible_count: int
    hidden_record_count: int
    clear_group_count: int
    pending_group_count: int
    resolved_merge_group_count: int
    resolved_keep_all_group_count: int
    has_scan: bool
    generated_at: datetime | None = None


class DuplicateGroupPage(BaseModel):
    """结果范围内的重复组分页响应。"""

    total: int
    offset: int
    limit: int
    items: list[DuplicateGroupRead]

class DuplicateResolveRequest(BaseModel):
    """人工决策；keep_record 需要明确选择保留的 result_id 与 PMID。"""

    action: Literal["keep_record", "keep_all", "merge_all", "undo"]
    canonical_result_id: int | None = Field(default=None, ge=1)
    canonical_record_pmid: str | None = Field(default=None, min_length=1, max_length=20)
    resolved_by: str = Field(default="local_user", min_length=1, max_length=100)


class ResultDuplicateResolutionRequest(BaseModel):
    action: Literal["merge", "keep_all", "undo"]
    canonical_record_key: str | None = Field(default=None, min_length=1)
    resolved_by: str = Field(default="local_user", min_length=1, max_length=100)


class ResultDuplicateResolutionRead(BaseModel):
    group: DuplicateGroupRead
    summary: DeduplicationSummary


# ----------------------------------------------------------------------
# R2-WP08：推荐阅读顺序
# ----------------------------------------------------------------------

# 证据金字塔层级（review-paper 融合）：数值越小越先读。
# 顺序固定为 综述 → 指南/共识 → 原始研究 → 前沿 → 高相关。
ReadingCategory = Literal[
    "review", "guideline", "original_research", "frontier", "highly_relevant"
]


class ReadingOrderRequest(BaseModel):
    """生成阅读顺序的请求。

    manual_order 为用户已保存的人工顺序（完整 PMID 列表）；调用方在 POST
    生成时携带它，服务端优先应用（重新生成不覆盖人工顺序）。manual_order
    为空列表表示"未调整过"，使用算法顺序。
    """

    manual_order: list[str] = Field(default_factory=list, max_length=500)
    duplicate_mode: Literal["all", "consolidated"] = "all"


class ReadingOrderItem(BaseModel):
    """单条文献的阅读顺序条目。

    category 由规则分类器依据 publication_types 等真实字段得出，模型输出
    不得改变它；priority 为 1..n 的阅读顺序；reason 为可解释文本（含
    为什么推荐 + 先读/后读 + 背景/方法/前沿 + 相关性 + 全文状态 + 不确定性）；
    evidence_features 为触发分类的真实特征列表（如 ["publication_type=Review"]），
    不包含被引量/影响因子等不可得数据。
    """

    pmid: str
    category: ReadingCategory
    priority: int = Field(ge=1)
    reason: str
    evidence_features: list[str]
    title: str | None = None
    year: int | None = None


class ReadingOrderRead(BaseModel):
    """一次阅读顺序生成的结果（含全部条目与来源结果 id）。

    order_source 为 "rule"（算法顺序）或 "manual"（用户人工顺序优先），
    供前端明确展示排序来源。
    """

    result_id: int
    order_source: Literal["rule", "manual"]
    duplicate_mode: Literal["all", "consolidated"] = "all"
    generated_at: datetime
    items: list[ReadingOrderItem] = Field(default_factory=list)


class ReadingOrderSaveRequest(BaseModel):
    """保存人工顺序的请求：完整 PMID 列表，位置即顺序。

    manual_order 全量替换：前端拖拽结束后提交完整列表，避免增量合并的
    顺序歧义。列表长度与结果条目数不要求严格一致（检索更新后部分 PMID
    可能消失），服务端只按 PMID 收敛。
    """

    manual_order: list[str] = Field(min_length=0, max_length=500)
    duplicate_mode: Literal["all", "consolidated"] = "all"
