from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StrategySort = Literal["pinned", "updated_at", "created_at", "name"]
ExecutionStatusFilter = Literal["running", "succeeded", "failed"]


class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    research_context_id: int | None = None
    framework: str = "topic"
    original_query: str = Field(min_length=1, max_length=1000)
    structured_query: str = ""
    search_string: str = Field(min_length=1, max_length=5000)
    filters: str = ""
    model_version: str = Field(min_length=1, max_length=200)
    user_edits: str = ""
    term_groups: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    start_year: int | None = None
    end_year: int | None = None


class StrategyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    research_context_id: int | None = None
    is_pinned: bool | None = None


class StrategyVersionCreate(BaseModel):
    expected_current_version: int = Field(ge=1)
    original_query: str
    structured_query: str = ""
    search_string: str
    filters: str = ""
    model_version: str
    user_edits: str = ""
    term_groups: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    start_year: int | None = None
    end_year: int | None = None


class StrategyVersionRead(BaseModel):
    id: int
    version: int
    original_query: str
    search_string: str
    filters: str
    model_version: str
    term_groups: list[str]
    mesh_terms: list[str]
    start_year: int | None
    end_year: int | None
    change_summary: dict[str, object]
    created_at: datetime


class ExecutionRead(BaseModel):
    id: int
    strategy_version_id: int
    version: int
    result_id: int | None
    status: str
    result_count: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    requested_retmax: int
    previous_result_id: int | None
    added_count: int | None
    removed_count: int | None
    added_pmids: list[str] | None
    removed_pmids: list[str] | None
    has_changes: bool | None


class StrategyRead(BaseModel):
    id: int
    name: str
    research_context_id: int | None
    framework: str
    database: str
    is_pinned: bool
    is_archived: bool
    current_version: StrategyVersionRead
    versions: list[StrategyVersionRead]
    executions: list[ExecutionRead]
    updated_at: datetime


class StrategyListItem(BaseModel):
    id: int
    name: str
    research_context_id: int | None
    framework: str
    is_pinned: bool
    is_archived: bool
    current_version: int
    original_query: str
    keyword_count: int
    mesh_count: int
    start_year: int | None
    end_year: int | None
    latest_execution: ExecutionRead | None


class StrategyPage(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[StrategyListItem]


class StrategyCloneRequest(BaseModel):
    name: str | None = Field(default=None, max_length=300)


class StrategyCompareRead(BaseModel):
    from_version: int
    to_version: int
    changes: dict[str, object]


class StrategyExecuteRequest(BaseModel):
    """一次策略版本执行的可变运行参数。

    策略版本本身不可变；retmax 仅限制本次从 PubMed 取回的文献条目数，
    不会回写策略快照，也不影响后续重放的可复现输入。
    """

    retmax: int = Field(default=20, ge=1, le=500)


class StrategyExportRead(BaseModel):
    exported_at: datetime
    total: int
    strategies: list[StrategyRead]
