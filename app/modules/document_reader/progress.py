"""页级 exposure 合并与进度投影纯函数。"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.modules.document_reader.constants import (
    EXPOSURE_MIN_MILLISECONDS,
    EXPOSURE_MIN_VISIBLE_RATIO,
)


@dataclass(frozen=True, slots=True)
class ExposureFact:
    page_number: int
    visible_milliseconds: int
    max_visible_ratio: float
    qualified_at: datetime | None

    @property
    def is_qualified(self) -> bool:
        return self.qualified_at is not None or (
            self.visible_milliseconds >= EXPOSURE_MIN_MILLISECONDS
            and self.max_visible_ratio >= EXPOSURE_MIN_VISIBLE_RATIO
        )


@dataclass(frozen=True, slots=True)
class ProgressProjection:
    qualified_pages: int
    total_pages: int
    percent: int


def merge_exposure(
    current: ExposureFact,
    *,
    visible_milliseconds: int,
    max_visible_ratio: float,
) -> ExposureFact:
    """同一 session/page 只合并事实，资格时间首次达标后保持不变。"""
    merged = replace(
        current,
        visible_milliseconds=current.visible_milliseconds + visible_milliseconds,
        max_visible_ratio=max(current.max_visible_ratio, max_visible_ratio),
    )
    if merged.is_qualified and merged.qualified_at is None:
        return replace(merged, qualified_at=datetime.now(UTC))
    return merged


def project_progress(
    exposures: list[ExposureFact], total_pages: int
) -> ProgressProjection:
    qualified = len({item.page_number for item in exposures if item.is_qualified})
    percent = round(qualified * 100 / total_pages) if total_pages > 0 else 0
    return ProgressProjection(qualified, total_pages, percent)

