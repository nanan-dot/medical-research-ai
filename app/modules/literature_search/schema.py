"""Literature search API structures."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    versions: list[LiteratureSearchTaskVersion] = Field(default_factory=list)


class LiteratureSearchTaskList(BaseModel):
    """检索历史列表页（分页；不携带条目明细，避免响应过大）。"""

    total: int
    offset: int
    limit: int
    items: list[LiteratureSearchTaskRead]


class LiteratureSearchTaskRerun(BaseModel):
    """重跑任务后返回的更新后任务详情。"""

    task: LiteratureSearchTaskRead
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


class LiteratureSearchResultRead(BaseModel):
    """检索执行结果（不含正文摘录，避免暴露超长内容）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    total_count: int
    created_at: datetime
    items: list[CitationItem]
