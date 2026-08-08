from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from app.modules.comparison.shared import SourceRef

OutlineKind = Literal["review", "proposal"]


class OutlineClaim(BaseModel):
    text: str
    evidence: list[SourceRef] = Field(default_factory=list)
    missing_evidence: bool = False
    status: Literal["fact", "candidate"] = "fact"


class OutlineCreate(BaseModel):
    matrix_id: int = Field(gt=0)
    kind: OutlineKind


class OutlineRead(BaseModel):
    id: int
    matrix_id: int
    kind: OutlineKind
    claims: list[OutlineClaim]
    version: int
    confirmed_by_user: bool
    confirmed_at: datetime | None
    created_at: datetime
