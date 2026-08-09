import pytest

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.service import RecommendationEvidenceService


class FakeExecutor:
    def __init__(
        self, items: list[CitationItem], total_count: int | None = None
    ) -> None:
        self.items = items
        self.total_count = total_count if total_count is not None else len(items)
        self.query: str | None = None

    async def execute(
        self, query: str, *, retmax: int
    ) -> tuple[list[CitationItem], int]:
        self.query = query
        return self.items, self.total_count


def _item(
    pmid: str, year: int | None, *, abstract: bool = True, withdrawn: bool = False
) -> CitationItem:
    return CitationItem(
        pmid=pmid,
        title=f"Title {pmid}",
        year=year,
        verified=True,
        verified_by="pubmed",
        has_abstract=abstract,
        withdrawn=withdrawn,
    )


@pytest.mark.asyncio
async def test_filters_unusable_records_sorts_and_limits() -> None:
    executor = FakeExecutor(
        [
            _item("1", 2020),
            _item("2", 2024),
            _item("3", 2025, abstract=False),
            _item("4", 2023, withdrawn=True),
        ]
    )

    result = await RecommendationEvidenceService(executor=executor).search(
        "肺癌", candidate_count=2
    )

    assert [item.pmid for item in result.items] == ["2", "1"]
    assert result.warnings == []
    assert executor.query is not None


@pytest.mark.asyncio
async def test_empty_quality_filtered_results_return_warning() -> None:
    executor = FakeExecutor([_item("1", 2024, abstract=False)])

    result = await RecommendationEvidenceService(executor=executor).search(
        "肺癌", candidate_count=5
    )

    assert result.items == []
    assert "未找到可验证文献" in result.warnings
