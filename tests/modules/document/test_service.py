from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.common.exceptions import ConflictError
from app.modules.document.schema import ParseStatus
from app.modules.document.service import DocumentService, MAX_ERROR_MESSAGE_LENGTH
from tests.modules.document.conftest import create_document


@pytest.mark.asyncio
async def test_failed_parse_can_retry_and_running_retry_conflicts(session, tmp_path: Path, caplog):
    document, _ = await create_document(session, tmp_path / "source", parse_status="failed")
    service = DocumentService(session)
    retried = await service.retry_parse(document.id)
    assert retried.parse_status == "pending"
    assert retried.retry_count == 1
    assert retried.error_message is None
    assert "document_state_changed" in caplog.text

    retried.parse_status = "parsing"
    retried.started_at = datetime.now(UTC)
    with pytest.raises(ConflictError, match="already running"):
        await service.retry_parse(document.id)


@pytest.mark.asyncio
async def test_failed_and_outdated_index_retry_requires_successful_parse(session, tmp_path: Path):
    document, _ = await create_document(
        session, tmp_path / "source", parse_status="succeeded", index_status="failed"
    )
    service = DocumentService(session)
    retried = await service.retry_index(document.id)
    assert retried.index_status == "pending"
    assert retried.retry_count == 1

    retried.index_status = "outdated"
    retried.parse_status = "failed"
    with pytest.raises(ConflictError, match="parsed successfully"):
        await service.retry_index(document.id)


@pytest.mark.asyncio
async def test_stalled_task_becomes_failed_and_error_is_bounded(session, tmp_path: Path):
    document, _ = await create_document(session, tmp_path / "source", parse_status="parsing")
    document.started_at = datetime.now(UTC) - timedelta(hours=1)
    service = DocumentService(session)
    reconciled = await service.get(document.id)
    assert reconciled.parse_status == "failed"
    assert reconciled.error_code == "task_stalled"
    assert reconciled.finished_at is not None

    reconciled.parse_status = "parsing"
    await service.mark_parse_status(
        reconciled,
        ParseStatus.FAILED,
        "x" * 100,
        "api_key=sk-sensitive12345678\n" + "y" * 1000,
    )
    assert len(reconciled.error_code or "") == 64
    assert len(reconciled.error_message or "") == MAX_ERROR_MESSAGE_LENGTH
    assert "\n" not in (reconciled.error_message or "")
    assert "sk-sensitive" not in (reconciled.error_message or "")
    assert "[REDACTED]" in (reconciled.error_message or "")


@pytest.mark.asyncio
async def test_missing_external_file_never_remains_successful(session, tmp_path: Path):
    document, file_path = await create_document(
        session, tmp_path / "source", parse_status="succeeded", index_status="succeeded"
    )
    file_path.unlink()
    reconciled = await DocumentService(session).get(document.id)
    assert reconciled.parse_status == "failed"
    assert reconciled.index_status == "outdated"
    assert reconciled.error_code == "source_file_missing"


@pytest.mark.asyncio
async def test_filter_pagination_and_total_are_consistent(session, tmp_path: Path):
    await create_document(session, tmp_path / "one", parse_status="failed")
    await create_document(session, tmp_path / "two", parse_status="succeeded")
    await create_document(session, tmp_path / "three", parse_status="failed")
    page = await DocumentService(session).list(offset=1, limit=1, parse_status=ParseStatus.FAILED)
    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].parse_status == ParseStatus.FAILED


@pytest.mark.asyncio
async def test_delete_index_does_not_delete_source_file(session, tmp_path: Path):
    document, file_path = await create_document(
        session, tmp_path / "source", parse_status="succeeded", index_status="succeeded"
    )
    reset = await DocumentService(session).delete_index(document.id)
    assert reset.index_status == "pending"
    assert file_path.read_text(encoding="utf-8") == "test fixture"
