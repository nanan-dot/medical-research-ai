from datetime import UTC, datetime, timedelta

import pytest

from app.modules.document_reader.constants import (
    EXPOSURE_MIN_MILLISECONDS,
    EXPOSURE_MIN_VISIBLE_RATIO,
)
from app.modules.document_reader.errors import ReaderStateVersionConflictError
from app.modules.document_reader.progress import (
    ExposureFact,
    merge_exposure,
    project_progress,
)
from app.modules.document_reader.records import classify_annotation
from app.modules.document_reader.schema import (
    CitationAnchorContext,
    ExposureBatchCreate,
    ExposureCreate,
    ReaderPositionUpdate,
)


def test_fast_flip_is_not_qualified() -> None:
    fact = ExposureFact(1, EXPOSURE_MIN_MILLISECONDS - 1, 1.0, None)
    assert not fact.is_qualified


def test_progress_projects_26_of_38() -> None:
    facts = [ExposureFact(page, 10_000, 1.0, datetime.now(UTC)) for page in range(1, 27)]
    projected = project_progress(facts, 38)
    assert (projected.qualified_pages, projected.total_pages, projected.percent) == (26, 38, 68)


def test_duplicate_exposure_merges_without_double_counting() -> None:
    first = ExposureFact(3, 1200, 0.7, None)
    merged = merge_exposure(first, visible_milliseconds=900, max_visible_ratio=0.9)
    assert merged.visible_milliseconds == 2100
    assert merged.max_visible_ratio == 0.9
    assert merged.is_qualified
    assert project_progress([merged], 10).qualified_pages == 1


def test_annotation_classification_is_disjoint() -> None:
    assert classify_annotation(None) == "highlight"
    assert classify_annotation("  ") == "highlight"
    assert classify_annotation("clinical note") == "annotation"


def test_position_round_trip_and_version_conflict() -> None:
    payload = ReaderPositionUpdate(
        page=12, viewport_offset_ratio=0.31, expected_version=3,
        expected_file_hash="a" * 64,
    )
    assert payload.page == 12
    error = ReaderStateVersionConflictError(current_state={"page": 13, "version": 4})
    assert error.code == "READER_STATE_VERSION_CONFLICT"
    assert error.detail["current_state"]["page"] == 13


def test_citation_contract_exposes_source_anchor() -> None:
    citation = CitationAnchorContext(source_anchor_id=9, anchor_status="exact")
    assert citation.source_anchor_id == 9


def test_input_boundaries() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        ExposureCreate(page_number=0, visible_milliseconds=1, max_visible_ratio=1, first_visible_at=now, last_visible_at=now)
    with pytest.raises(ValueError):
        ExposureBatchCreate(exposures=[ExposureCreate(page_number=1, visible_milliseconds=1, max_visible_ratio=1, first_visible_at=now, last_visible_at=now)] * 101)
    with pytest.raises(ValueError):
        ExposureCreate(page_number=1, visible_milliseconds=1, max_visible_ratio=EXPOSURE_MIN_VISIBLE_RATIO, first_visible_at=now, last_visible_at=now-timedelta(seconds=1))

