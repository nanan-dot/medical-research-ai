"""Literature search API structures."""

from pydantic import BaseModel, ConfigDict, Field

from app.modules.literature_search.query_model import SearchIntentCandidate


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
