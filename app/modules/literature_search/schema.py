"""Literature search API structures."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.literature_search.query_model import MAX_RETMX, SearchIntentCandidate


class LiteratureSearchCreate(BaseModel):
    pass


class LiteratureSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int


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
