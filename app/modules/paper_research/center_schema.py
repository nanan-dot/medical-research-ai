"""Stable HTTP contracts for the paper-research center."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchStage(StrEnum):
    PROBLEM_DEFINITION = "problem_definition"
    LITERATURE_READING = "literature_reading"
    PAPER_UNDERSTANDING = "paper_understanding"
    EVIDENCE_ORGANIZATION = "evidence_organization"
    CONCLUSION_FORMATION = "conclusion_formation"


class CurrentContextUpdate(BaseModel):
    research_context_id: int | None
    stage: ResearchStage = ResearchStage.PROBLEM_DEFINITION
    expected_version: int = Field(ge=1)


class CurrentContextStageUpdate(BaseModel):
    stage: ResearchStage
    expected_version: int = Field(ge=1)


class CurrentContextRead(BaseModel):
    research_context_id: int | None
    research_name: str | None
    stage: ResearchStage
    version: int


class NextActionRead(BaseModel):
    kind: str
    title: str
    description: str
    reason_codes: list[str]
    target: dict[str, object] | None
    is_available: bool
    unavailable_reason: str | None


class ContinueTaskRead(BaseModel):
    paper_item_id: int
    title: str | None
    journal: str | None
    year: int | None
    work_mode: str
    current_section: str | None
    reading_progress_percent: int
    analysis_completed: int
    analysis_total: int
    last_work_at: datetime | None
    entry_available: bool
    next_action: NextActionRead
    sort_reason: str


class ActivityRead(BaseModel):
    id: int
    kind: str
    occurred_at: datetime
    paper_item_id: int
    paper_title: str | None
    research_context_id: int | None
    research_name: str | None
    target: dict[str, object] | None
    summary: str | None
    target_available: bool
    unavailable_reason: str | None


class ActivityPage(BaseModel):
    items: list[ActivityRead]
    next_cursor: str | None


class RecentPaperRead(BaseModel):
    paper_item_id: int
    title: str | None
    journal: str | None
    year: int | None
    reading_status: str
    entry_available: bool
    last_work_at: datetime | None


class CenterSummaryRead(BaseModel):
    papers: int
    reading: int
    deep_reading: int
    completed: int
    pending_confirmation_items: int
    pending_confirmation_fields: int


class CenterRead(BaseModel):
    current_research: CurrentContextRead | None
    continue_tasks: list[ContinueTaskRead]
    recent_activities: list[ActivityRead]
    recent_papers: list[RecentPaperRead]
    summary: CenterSummaryRead
    capabilities: dict[str, str]
