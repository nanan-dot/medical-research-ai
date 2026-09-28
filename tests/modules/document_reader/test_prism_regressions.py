"""Behavioral regression tests derived from the Prism review findings."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.conversation.schema import ReaderContext
from app.modules.conversation.service import ConversationService
from app.modules.document_reader.copilot import validate_copilot_context
from app.modules.document_reader.errors import ReaderResourceNotFoundError
from app.modules.document_reader.record_projector import ReaderRecordProjector
from app.modules.document_reader.schema import ExposureCreate, SessionCreate
from app.modules.document_reader.service import ReaderSessionService


def test_exposure_rejects_claimed_duration_outside_observed_interval() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValueError, match="exceeds observed interval"):
        ExposureCreate(
            page_number=1,
            visible_milliseconds=2_000,
            max_visible_ratio=1,
            first_visible_at=now,
            last_visible_at=now + timedelta(milliseconds=100),
        )


def test_record_cursor_is_stable_and_non_overlapping() -> None:
    rows = [
        {"record_id": "question:3", "created_at": "2026-09-02T10:00:00+00:00"},
        {"record_id": "bookmark:2", "created_at": "2026-09-02T09:00:00+00:00"},
        {"record_id": "annotation:1", "created_at": "2026-09-02T08:00:00+00:00"},
    ]

    first, cursor = ReaderRecordProjector._page(rows, None, limit=2)
    second, next_cursor = ReaderRecordProjector._page(rows, cursor, limit=2)

    assert [item["record_id"] for item in first] == ["question:3", "bookmark:2"]
    assert [item["record_id"] for item in second] == ["annotation:1"]
    assert next_cursor is None


@pytest.mark.asyncio
async def test_session_reuse_requires_current_document_file_hash() -> None:
    database = AsyncMock()
    service = ReaderSessionService(database)
    item = SimpleNamespace(id=8)
    document = SimpleNamespace(id=9, file_hash="a" * 64)
    service._item_document = AsyncMock(return_value=(item, document))
    service._repo.session_by_idempotency_key = AsyncMock(return_value=None)
    service._repo.active_session = AsyncMock(return_value=SimpleNamespace(
        id=3,
        library_item_id=8,
        document_id=9,
        document_file_hash="a" * 64,
        last_page=1,
        viewport_offset_ratio=0,
        status="active",
        version=1,
    ))

    await service.create_or_reuse(8, SessionCreate(device_id="web"), "same-key")

    assert service._repo.active_session.await_args.args == (8, "web", "local:default", "a" * 64)


@pytest.mark.asyncio
async def test_copilot_rejects_context_document_outside_conversation() -> None:
    payload = SimpleNamespace(
        document_id=10,
        source_anchor_id=None,
        active_segment_id=None,
        section_id=None,
        expected_anchor_revision_id=20,
        expected_segmentation_revision_id=None,
    )

    with pytest.raises(ReaderResourceNotFoundError, match="不属于该会话"):
        await validate_copilot_context(AsyncMock(), payload, {11})


def test_citation_context_is_labeled_as_context_not_evidence_identity() -> None:
    context = ReaderContext(document_id=4, source_anchor_id=5, expected_anchor_revision_id=6)

    assert ConversationService._citation_context_values(context, 4) == {
        "source_anchor_id": 5,
        "anchor_status": "reader_context",
    }
    assert ConversationService._citation_context_values(context, 7) == {}
