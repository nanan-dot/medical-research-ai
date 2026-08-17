from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.common.exceptions import ConflictError
from app.modules.document.schema import ParseStatus
from app.modules.document.service import MAX_ERROR_MESSAGE_LENGTH, DocumentService
from app.modules.document_upload.model import DocumentAsset
from tests.modules.document.conftest import create_document


@pytest.mark.asyncio
async def test_failed_parse_can_retry_and_running_retry_conflicts(
    session, tmp_path: Path, caplog
):
    document, _ = await create_document(
        session, tmp_path / "source", name="retry.md", parse_status="failed"
    )
    service = DocumentService(session)
    retried = await service.retry_parse(document.id)
    assert retried.parse_status == "succeeded"
    assert retried.retry_count == 1
    assert retried.error_message is None
    assert "document_state_changed" in caplog.text

    retried.parse_status = "parsing"
    retried.started_at = datetime.now(UTC)
    with pytest.raises(ConflictError, match="already running"):
        await service.retry_parse(document.id)


@pytest.mark.asyncio
async def test_failed_and_outdated_index_retry_requires_successful_parse(
    session, tmp_path: Path
):
    document, _ = await create_document(
        session, tmp_path / "source", parse_status="succeeded", index_status="failed"
    )
    service = DocumentService(session)
    retried = await service.retry_index(document.id)
    assert retried.index_status == "pending"
    assert retried.retry_count == 1

    pending_retry = await service.retry_index(document.id)
    assert pending_retry.index_status == "pending"
    assert pending_retry.retry_count == 1

    retried.index_status = "outdated"
    retried.parse_status = "failed"
    with pytest.raises(ConflictError, match="parsed successfully"):
        await service.retry_index(document.id)


@pytest.mark.asyncio
async def test_stalled_task_becomes_failed_and_error_is_bounded(
    session, tmp_path: Path
):
    document, _ = await create_document(
        session, tmp_path / "source", parse_status="parsing"
    )
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

    file_path.write_text("source is available again", encoding="utf-8")
    recovered = await DocumentService(session).get(document.id)
    assert recovered.parse_status == "pending"
    assert recovered.error_code is None


@pytest.mark.asyncio
async def test_filter_pagination_and_total_are_consistent(session, tmp_path: Path):
    await create_document(session, tmp_path / "one", parse_status="failed")
    await create_document(session, tmp_path / "two", parse_status="succeeded")
    await create_document(session, tmp_path / "three", parse_status="failed")
    page = await DocumentService(session).list(
        offset=1, limit=1, parse_status=ParseStatus.FAILED
    )
    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].parse_status == ParseStatus.FAILED


@pytest.mark.asyncio
async def test_unfiltered_total_counts_all_documents(session, tmp_path: Path):
    await create_document(session, tmp_path / "first")
    await create_document(session, tmp_path / "second")
    await create_document(session, tmp_path / "third")

    page = await DocumentService(session).list(offset=0, limit=20)

    assert page.total == 3
    assert len(page.items) == 3


@pytest.mark.asyncio
async def test_list_filters_documents_by_knowledge_source(session, tmp_path: Path):
    first, _ = await create_document(session, tmp_path / "first")
    second, _ = await create_document(session, tmp_path / "second")

    filtered = await DocumentService(session).list(
        knowledge_source_id=first.knowledge_source_id
    )
    unfiltered = await DocumentService(session).list()
    missing_source = await DocumentService(session).list(knowledge_source_id=99999)

    assert [document.id for document in filtered.items] == [first.id]
    assert {document.id for document in unfiltered.items} == {first.id, second.id}
    assert missing_source.items == [] and missing_source.total == 0


@pytest.mark.asyncio
async def test_selector_filters_query_readiness_and_pdf_media_type(session, tmp_path: Path):
    ready, _ = await create_document(
        session, tmp_path / "ready", "Report_100%.pdf", "succeeded", "succeeded"
    )
    ready.paperqa_index_key = "ready-index"
    pending, _ = await create_document(session, tmp_path / "pending", "Report_100x.pdf")
    no_key, _ = await create_document(
        session, tmp_path / "no-key", "other.pdf", "succeeded", "succeeded"
    )
    await session.flush()
    session.add_all([
        DocumentAsset(document_id=ready.id, original_filename="Clinical_Report_100%.pdf", stored_relative_path="ready.pdf", media_type="application/pdf", byte_size=1, sha256="b" * 64),
        DocumentAsset(document_id=pending.id, original_filename="clinical report 100x.pdf", stored_relative_path="pending.pdf", media_type="application/x-pdf", byte_size=1, sha256="c" * 64),
        DocumentAsset(document_id=no_key.id, original_filename="other.pdf", stored_relative_path="no-key.pdf", media_type="text/plain", byte_size=1, sha256="d" * 64),
    ])
    await session.commit()

    service = DocumentService(session)
    matched = await service.list(query=" CLINICAL_REPORT_100% ")
    assert [item.id for item in matched.items] == [ready.id]
    assert matched.total == 1
    ready_only = await service.list(research_ready=True)
    assert [item.id for item in ready_only.items] == [ready.id]
    pdf_only = await service.list(previewable_only=True)
    assert {item.id for item in pdf_only.items} == {ready.id, pending.id}
    combined = await service.list(query="report", research_ready=True, previewable_only=True)
    assert combined.total == 1 and combined.items[0].id == ready.id


@pytest.mark.asyncio
async def test_delete_index_does_not_delete_source_file(session, tmp_path: Path):
    document, file_path = await create_document(
        session, tmp_path / "source", parse_status="succeeded", index_status="succeeded"
    )
    reset = await DocumentService(session).delete_index(document.id)
    assert reset.index_status == "pending"
    assert file_path.read_text(encoding="utf-8") == "test fixture"
