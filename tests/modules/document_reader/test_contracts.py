from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.conversation.schema import MessageCreate
from app.modules.document_reader.copilot import validate_copilot_context
from app.modules.document_reader.errors import IdempotencyKeyReusedError
from app.modules.document_reader.history import decode_cursor, encode_cursor
from app.modules.document_reader.idempotency import (
    ensure_payload_matches,
    payload_digest,
)
from app.modules.document_reader.policy import (
    ensure_revision_fence,
    no_evidence_answer_status,
)
from app.modules.document_reader.records import (
    classify_annotation,
    filter_record_items,
    summarize_record_items,
)


def test_revision_fence_rejects_mixed_generation() -> None:
    with pytest.raises(ValueError):
        ensure_revision_fence(anchor_revision_id=7, segmentation_anchor_revision_id=8)


def test_record_summary_matches_filtered_list() -> None:
    records = [
        {"record_type": "highlight", "section_id": 1, "text": "alpha"},
        {"record_type": "annotation", "section_id": 1, "text": "beta"},
        {"record_type": "question", "section_id": 2, "text": "alpha"},
    ]
    filtered = filter_record_items(records, record_type=None, section_id=1, query=None)
    assert sum(summarize_record_items(filtered).values()) == len(filtered)
    assert classify_annotation(None) != classify_annotation("note")


def test_idempotency_reuses_same_payload() -> None:
    digest = payload_digest({"source_anchor_id": 1, "note": "x"})
    ensure_payload_matches(digest, digest)


def test_idempotency_rejects_different_payload() -> None:
    with pytest.raises(IdempotencyKeyReusedError):
        ensure_payload_matches(payload_digest({"a": 1}), payload_digest({"a": 2}))


def test_no_evidence_policy_returns_no_answer() -> None:
    assert no_evidence_answer_status([]) == "no_answer"


def test_history_cursor_round_trip() -> None:
    timestamp = datetime.now(UTC).replace(microsecond=0)
    assert decode_cursor(encode_cursor(timestamp, 8)) == (timestamp, 8)
    with pytest.raises(ValueError):
        decode_cursor("not-a-cursor")


@pytest.mark.asyncio
async def test_copilot_reader_context_requires_revision_fence() -> None:
    session = AsyncMock()
    with pytest.raises(ValueError):
        await validate_copilot_context(
            session,
            MessageCreate(question="explain", document_id=3, source_anchor_id=4),
        )
