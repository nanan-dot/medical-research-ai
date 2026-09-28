"""Editable, conservative representation of a literature-search intent."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

MIN_YEAR = 1900
MAX_RETMX = 500
DEFAULT_PUBLICATION_WINDOW_YEARS = 15


class DateRange(BaseModel):
    start_year: int | None = Field(default=None, ge=MIN_YEAR)
    end_year: int | None = Field(default=None, ge=MIN_YEAR)
    original_expression: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError("start_year cannot be after end_year")
        return self


class ConstrainedDateRange(BaseModel):
    """产品窗口约束后的可执行日期范围。"""

    effective_range: DateRange
    was_defaulted: bool = False
    was_clipped: bool = False
    warnings: list[str] = Field(default_factory=list)


class LiteratureSearchRangeOutsidePolicyError(ValueError):
    """请求日期与滚动产品窗口完全无交集。"""


def publication_window(current_year: int) -> DateRange:
    """返回包含首尾年份的滚动十五年窗口。"""
    return DateRange(
        start_year=current_year - DEFAULT_PUBLICATION_WINDOW_YEARS + 1,
        end_year=current_year,
    )


def constrain_date_range(
    requested: DateRange | None, current_year: int
) -> ConstrainedDateRange:
    """将用户范围与产品窗口取交集，保留可审计的裁剪信息。"""
    policy = publication_window(current_year)
    if requested is None:
        return ConstrainedDateRange(effective_range=policy, was_defaulted=True)
    requested_start = requested.start_year or MIN_YEAR
    requested_end = requested.end_year or current_year
    effective_start = max(requested_start, policy.start_year or MIN_YEAR)
    effective_end = min(requested_end, policy.end_year or current_year)
    if effective_start > effective_end:
        raise LiteratureSearchRangeOutsidePolicyError(
            "requested publication range is outside the rolling 15-year policy"
        )
    was_clipped = effective_start != requested_start or effective_end != requested_end
    return ConstrainedDateRange(
        effective_range=DateRange(
            start_year=effective_start,
            end_year=effective_end,
            original_expression=requested.original_expression,
        ),
        was_clipped=was_clipped,
        warnings=(
            ["publication_date_range_clipped_to_15_year_policy"] if was_clipped else []
        ),
    )


def append_publication_filter(query: str, date_range: DateRange) -> str:
    """在最终执行边界追加 PubMed 日期过滤器，防止手改查询绕过策略。"""
    return (
        f'({query}) AND ("{date_range.start_year}"[Date - Publication] : '
        f'"{date_range.end_year}"[Date - Publication])'
    )


class SearchIntentCandidate(BaseModel):
    """A proposed query intent, never a hidden final search expression."""

    topic: str = Field(min_length=1, max_length=500)
    disease: str | None = Field(default=None, max_length=200)
    intervention: str | None = Field(default=None, max_length=200)
    comparison: str | None = Field(default=None, max_length=200)
    outcome: str | None = Field(default=None, max_length=200)
    target: str | None = Field(default=None, max_length=200)
    mechanism: str | None = Field(default=None, max_length=200)
    date_range: DateRange | None = None
    study_types: list[str] = Field(default_factory=list, max_length=10)
    language: list[str] = Field(default_factory=list, max_length=10)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    retmax: int = Field(default=MAX_RETMX, ge=1, le=MAX_RETMX)

    @model_validator(mode="after")
    def remove_blank_and_duplicate_values(self) -> "SearchIntentCandidate":
        for field_name in ("study_types", "language", "exclusions"):
            values = getattr(self, field_name)
            setattr(
                self,
                field_name,
                list(dict.fromkeys(value.strip() for value in values if value.strip())),
            )
        return self


def relative_year_range(years: int, expression: str) -> DateRange:
    current_year = datetime.now(UTC).year
    return DateRange(
        start_year=current_year - years + 1,
        end_year=current_year,
        original_expression=expression,
    )
