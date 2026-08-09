"""Versioned, annotation-only evaluation dataset support."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

QuestionType = Literal["sample_size", "study_design", "method", "outcome", "statistics", "result", "limitation", "comparison", "no_answer", "citation_support"]
ReviewStatus = Literal["draft", "reviewed", "approved"]
Split = Literal["development", "test"]


class EvaluationQuestion(BaseModel):
    """Human-annotated question; full paper text is intentionally excluded."""

    question_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=4000)
    answer: str | None = Field(default=None, max_length=8000)
    evidence_document_id: int | None = Field(default=None, gt=0)
    page: int | None = Field(default=None, gt=0)
    section: str | None = Field(default=None, max_length=500)
    question_type: QuestionType
    no_answer: bool = False
    difficulty: Literal["easy", "medium", "hard"]
    review_status: ReviewStatus
    dataset_version: str = Field(min_length=1, max_length=100)
    split: Split

    @model_validator(mode="after")
    def validate_annotation(self) -> EvaluationQuestion:
        if self.no_answer and self.answer is not None:
            raise ValueError("No-answer questions cannot contain a reference answer")
        if not self.no_answer and (self.answer is None or self.evidence_document_id is None):
            raise ValueError("Answerable questions require answer and evidence_document_id")
        if self.page is not None and self.evidence_document_id is None:
            raise ValueError("A page requires an evidence_document_id")
        return self


class EvaluationDataset(BaseModel):
    version: str
    split: Split
    questions: list[EvaluationQuestion]
    sha256: str


def load_jsonl(path: Path, *, split: Split) -> EvaluationDataset:
    """Load and validate an annotation-only JSONL split with a stable content hash."""
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset does not exist: {path}")
    raw_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError("Evaluation dataset is empty")
    questions = [EvaluationQuestion.model_validate_json(line) for line in raw_lines]
    ids = [item.question_id for item in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation dataset has duplicate question_id values")
    versions = {item.dataset_version for item in questions}
    if len(versions) != 1:
        raise ValueError("Evaluation dataset must contain one dataset_version")
    if any(item.split != split for item in questions):
        raise ValueError("Evaluation dataset split does not match file split")
    canonical = "\n".join(json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in questions)
    return EvaluationDataset(version=versions.pop(), split=split, questions=questions, sha256=hashlib.sha256(canonical.encode()).hexdigest())
