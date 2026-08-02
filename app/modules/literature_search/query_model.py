"""Editable, conservative representation of a literature-search intent."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

MIN_YEAR = 1900
MAX_RETMX = 500


class DateRange(BaseModel):
    start_year: int | None = Field(default=None, ge=MIN_YEAR)
    end_year: int | None = Field(default=None, ge=MIN_YEAR)
    original_expression: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.start_year is not None and self.end_year is not None and self.start_year > self.end_year:
            raise ValueError("start_year cannot be after end_year")
        return self


class SearchIntentCandidate(BaseModel):
    """A proposed query intent, never a hidden final search expression."""

    topic: str = Field(min_length=1, max_length=500)
    disease: str | None = Field(default=None, max_length=200)
    intervention: str | None = Field(default=None, max_length=200)
    target: str | None = Field(default=None, max_length=200)
    mechanism: str | None = Field(default=None, max_length=200)
    date_range: DateRange | None = None
    study_types: list[str] = Field(default_factory=list, max_length=10)
    language: list[str] = Field(default_factory=list, max_length=10)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    retmax: int = Field(default=50, ge=1, le=MAX_RETMX)

    @model_validator(mode="after")
    def remove_blank_and_duplicate_values(self) -> "SearchIntentCandidate":
        for field_name in ("study_types", "language", "exclusions"):
            values = getattr(self, field_name)
            setattr(self, field_name, list(dict.fromkeys(value.strip() for value in values if value.strip())))
        return self


def relative_year_range(years: int, expression: str) -> DateRange:
    current_year = datetime.now(UTC).year
    return DateRange(
        start_year=current_year - years + 1,
        end_year=current_year,
        original_expression=expression,
    )
