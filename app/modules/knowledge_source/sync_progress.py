"""同步任务进度的纯计算与类型化快照。"""

from dataclasses import dataclass
from enum import StrEnum

MAX_RUNNING_PROGRESS_PERCENT = 99
COMPLETED_PROGRESS_PERCENT = 100


class SyncPhase(StrEnum):
    """同步流水线中可对用户展示的真实阶段。"""

    QUEUED = "queued"
    SCANNING = "scanning"
    HASHING = "hashing"
    PERSISTING = "persisting"
    PARSING = "parsing"
    INDEXING = "indexing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


@dataclass(frozen=True)
class SyncProgress:
    """一个任务在某时刻的可持久化同步工作量快照。"""

    phase: SyncPhase
    completed_units: int
    total_units: int | None
    progress_percent: int | None
    current_item: str | None


def calculate_progress(
    phase: SyncPhase,
    completed_units: int,
    total_units: int | None,
    current_item: str | None = None,
) -> SyncProgress:
    """根据真实工作单位计算未完成任务的单调百分比。"""
    if total_units is None or total_units <= 0:
        return SyncProgress(phase, max(0, completed_units), None, None, current_item)
    bounded_completed = min(max(0, completed_units), total_units)
    percentage = min(
        MAX_RUNNING_PROGRESS_PERCENT,
        (bounded_completed * MAX_RUNNING_PROGRESS_PERCENT) // total_units,
    )
    return SyncProgress(
        phase,
        bounded_completed,
        total_units,
        percentage,
        current_item,
    )


def completed_progress() -> SyncProgress:
    """仅在任务提交成功后生成终态 100%。"""
    return SyncProgress(
        SyncPhase.COMPLETED,
        COMPLETED_PROGRESS_PERCENT,
        COMPLETED_PROGRESS_PERCENT,
        COMPLETED_PROGRESS_PERCENT,
        None,
    )
