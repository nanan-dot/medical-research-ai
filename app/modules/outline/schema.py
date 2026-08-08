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


class OutlineSection(BaseModel):
    title: str
    claims: list[OutlineClaim]


class OutlineCreate(BaseModel):
    matrix_id: int = Field(gt=0)
    kind: OutlineKind


class OutlineUpdate(BaseModel):
    sections: list[OutlineSection] = Field(min_length=1)


class OutlineRead(BaseModel):
    id: int
    matrix_id: int
    kind: OutlineKind
    sections: list[OutlineSection]
    version: int
    based_on_matrix_version: int
    retrieval_date: datetime
    document_count: int
    confirmed_by_user: bool
    confirmed_at: datetime | None
    created_at: datetime
