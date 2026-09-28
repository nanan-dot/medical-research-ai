"""AC-01—05：PubMed 滚动检索窗口。"""

import pytest

from app.modules.literature_search.query_model import (
    DateRange,
    LiteratureSearchRangeOutsidePolicyError,
    append_publication_filter,
    constrain_date_range,
)


def test_default_window_is_15_years() -> None:
    result = constrain_date_range(None, 2026)
    assert (result.effective_range.start_year, result.effective_range.end_year) == (
        2012,
        2026,
    )
    assert result.was_defaulted


def test_narrower_range_is_preserved() -> None:
    result = constrain_date_range(DateRange(start_year=2022, end_year=2026), 2026)
    assert result.effective_range == DateRange(start_year=2022, end_year=2026)
    assert not result.was_clipped


def test_partial_range_is_clipped_with_warning() -> None:
    result = constrain_date_range(DateRange(start_year=2010, end_year=2020), 2026)
    assert result.effective_range.start_year == 2012
    assert result.warnings == ["publication_date_range_clipped_to_15_year_policy"]


def test_disjoint_range_raises_policy_error_without_pubmed_call() -> None:
    with pytest.raises(LiteratureSearchRangeOutsidePolicyError):
        constrain_date_range(DateRange(start_year=2000, end_year=2010), 2026)


def test_rerun_uses_saved_effective_range() -> None:
    saved = append_publication_filter(
        "cancer", DateRange(start_year=2011, end_year=2025)
    )
    assert '"2011"[Date - Publication]' in saved
    assert '"2025"[Date - Publication]' in saved
