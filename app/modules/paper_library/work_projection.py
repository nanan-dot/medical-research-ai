"""论文库工作入口的纯函数投影。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.paper_library.model import PaperWorkState


@dataclass(frozen=True, slots=True)
class WorkEntryProjection:
    action: str
    enabled: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class WorkProjection:
    preferred_action: str
    last_work_at: datetime | None
    reading: WorkEntryProjection
    analysis: WorkEntryProjection


def project_work_entries(
    state: PaperWorkState | None,
    *,
    analysis_status: str,
    can_read: bool,
    can_analyze: bool,
    reading_reason: str | None,
    analysis_reason: str | None,
) -> WorkProjection:
    reading_status = state.reading_status if state else "unread"
    reading_action = {
        "unread": "start",
        "reading": "continue",
        "read": "review",
    }.get(reading_status, "start")
    analysis_action = {
        "pending": "continue",
        "analyzing": "continue",
        "completed": "review",
    }.get(analysis_status, "start")

    last_read_at = state.last_read_at if state else None
    last_analysis_at = state.last_analysis_at if state else None
    if last_analysis_at and (
        last_read_at is None
        or last_analysis_at > last_read_at
        or (
            last_analysis_at == last_read_at
            and state is not None
            and state.last_work_kind == "analysis"
        )
    ):
        preferred = "analysis"
    elif last_read_at:
        preferred = "reading"
    else:
        preferred = "reading"
    last_work_at = max(
        (value for value in (last_read_at, last_analysis_at) if value is not None),
        default=None,
    )
    return WorkProjection(
        preferred_action=preferred,
        last_work_at=last_work_at,
        reading=WorkEntryProjection(reading_action, can_read, reading_reason),
        analysis=WorkEntryProjection(analysis_action, can_analyze, analysis_reason),
    )
