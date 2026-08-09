from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCreate(BaseModel):
    dataset_version: str = Field(min_length=1, max_length=100)
    retriever_config: dict[str, object] = Field(default_factory=dict)
    model_settings: dict[str, object] = Field(default_factory=dict, alias="model_config")
    prompt_version: str = Field(min_length=1, max_length=100)

class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; dataset_version: str; status: str; created_at: datetime

class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; run_id: int; question_id: str; status: str; raw_output: str | None; elapsed_ms: int; error: str | None

class EvaluationResultCreate(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    status: str = Field(pattern="^(completed|failed)$")
    raw_output: str | None = Field(default=None, max_length=20000)
    elapsed_ms: int = Field(ge=0)
    error: str | None = Field(default=None, max_length=4000)
