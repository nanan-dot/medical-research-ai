"""论文库查询参数定义。"""

from dataclasses import dataclass, field
from enum import StrEnum


class PaperLibraryView(StrEnum):
    ALL = "all"
    RECENT = "recent"
    READING = "reading"
    ANALYZING = "analyzing"
    UNCLASSIFIED = "unclassified"


class PaperSort(StrEnum):
    RECENT_ACTIVITY = "recent_activity"
    ADDED_AT = "added_at"
    YEAR = "year"
    TITLE = "title"


class AnalysisStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PaperLibraryFilters:
    reading_status: list[str] = field(default_factory=list)
    analysis_status: list[str] = field(default_factory=list)
    paper_types: list[str] = field(default_factory=list)
    research_roles: list[str] = field(default_factory=list)
    research_ids: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    query: str = ""
