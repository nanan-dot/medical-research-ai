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
