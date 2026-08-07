"""R2-WP11 comparison business-rule tests (written before implementation)."""

import pytest
from pydantic import ValidationError

from app.modules.comparison.schema import ComparisonCreate
from app.modules.comparison.shared import ComparisonCellGenerated, SourceRef


@pytest.mark.parametrize(("document_count", "is_valid"), [(2, False), (10, True), (11, False)])
def test_document_count_is_limited_to_three_through_ten(document_count: int, is_valid: bool) -> None:
    payload = {"selected_document_ids": list(range(1, document_count + 1))}
    if is_valid:
        assert ComparisonCreate.model_validate(payload).selected_document_ids == payload["selected_document_ids"]
    else:
        with pytest.raises(ValidationError):
            ComparisonCreate.model_validate(payload)


def test_generated_value_without_sources_is_missing() -> None:
    cell = ComparisonCellGenerated(document_id=1, field="sample_size", generated_value="40", sources=[])
    assert cell.status == "missing"
    assert cell.cell_value == "缺失"


def test_invalid_pmid_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRef(pmid="PMID-abc", locator="abstract")
