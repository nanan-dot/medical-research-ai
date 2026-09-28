"""任务、不可变版本、原子发布和受限查询的行为验收。"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.common.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.modules.document_anchor.contract import validate_records
from app.modules.document_anchor.extractor_runner import (
    ExtractorExecutionError,
    PdfTextItemExtractor,
)
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.schema import AnchorRevisionRequest
from app.modules.document_anchor.service import DocumentAnchorService
from app.modules.document_anchor.worker import DocumentAnchorWorker
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.service import TaskService
from tests.modules.document_anchor.support import create_document, seal
from tests.modules.document_anchor.test_acceptance import (
    _FixedExtractor,
    _header,
    _page,
    _trailer,
)


async def setup_revision(session, tmp_path):
    document, path = await create_document(session, tmp_path / "source")
    revision = await DocumentAnchorService(session).request(
        document.id, AnchorRevisionRequest(expected_file_hash=document.file_hash)
    )
    await session.commit()
    return document, path, revision


async def test_failed_revision_retries_and_cannot_skip_execution(session, tmp_path):
    document, _, revision = await setup_revision(session, tmp_path)

    class Broken:
        async def extract(self, *args):
            raise ExtractorExecutionError("invalid_pdf")

    with pytest.raises(ExtractorExecutionError):
        await DocumentAnchorService(session).execute(revision.id, Broken())
    await DocumentAnchorService(session).execute(revision.id, _FixedExtractor())
    assert (
        await DocumentAnchorService(session).manifest(document.id)
    ).revision is not None
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourcePage)) == 1
    )


async def test_publish_failure_rolls_back_every_page_and_item(
    session, tmp_path, monkeypatch
):
    document, _, revision = await setup_revision(session, tmp_path)

    class TwoPages:
        async def extract(self, path, sha, request_id):
            header, first, second, trailer = _header(), _page(), _page(), _trailer()
            header.update(file_sha256=sha, request_id=request_id, page_count=2)
            second["page_number"] = 2
            trailer.update(request_id=request_id, pages_emitted=2, items_emitted=2)
            return validate_records(seal(header, [first, second], trailer))

    from app.modules.document_anchor import publisher

    original = publisher.page_entities

    def fail_second(revision_id, page, flags, page_hash):
        if page.page_number == 2:
            raise RuntimeError("simulated persistence boundary failure")
        return original(revision_id, page, flags, page_hash)

    monkeypatch.setattr(publisher, "page_entities", fail_second)
    with pytest.raises(RuntimeError):
        await DocumentAnchorService(session).execute(revision.id, TwoPages())
    await session.refresh(document)
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourcePage)) == 0
    )
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourceTextItem))
        == 0
    )
    assert (await DocumentAnchorService(session).manifest(document.id)).revision is None


async def test_file_change_during_extraction_cannot_publish(session, tmp_path):
    _, _path, revision = await setup_revision(session, tmp_path)

    class Mutating(_FixedExtractor):
        async def extract(self, path, sha, request_id):
            result = await super().extract(path, sha, request_id)
            path.write_bytes(path.read_bytes() + b"\n% changed")
            return result

    with pytest.raises(ConflictError):
        await DocumentAnchorService(session).execute(revision.id, Mutating())
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourcePage)) == 0
    )


async def test_new_file_revision_stales_old_without_overwriting(session, tmp_path):
    document, path, revision = await setup_revision(session, tmp_path)
    service = DocumentAnchorService(session)
    await service.execute(revision.id, _FixedExtractor())
    old_hash = (await service.get_revision(revision.id)).extraction_fingerprint
    path.write_bytes(path.read_bytes() + b"\n% new version")
    document.file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    await session.commit()
    assert (await service.manifest(document.id)).revision is None
    second = await service.request(
        document.id, AnchorRevisionRequest(expected_file_hash=document.file_hash)
    )
    await service.execute(second.id, _FixedExtractor())
    old = await service.get_revision(revision.id)
    assert old.state == "stale" and old.extraction_fingerprint == old_hash
    assert (await service.manifest(document.id)).revision.id == second.id
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourcePage)) == 2
    )


async def test_forced_diagnostic_compares_without_mutating_revision(session, tmp_path):
    document, _, revision = await setup_revision(session, tmp_path)
    service = DocumentAnchorService(session)
    await service.execute(revision.id, _FixedExtractor())
    diagnostic = await service.request(
        document.id,
        AnchorRevisionRequest(
            expected_file_hash=document.file_hash, force_new_toolchain_run=True
        ),
    )
    assert diagnostic.id == revision.id and diagnostic.task_id is not None
    await service.execute(revision.id, _FixedExtractor())
    assert (
        await session.scalar(select(func.count()).select_from(DocumentSourcePage)) == 1
    )

    class Different(_FixedExtractor):
        async def extract(self, path, sha, request_id):
            header, page, trailer = _header(), _page(), _trailer()
            header.update(file_sha256=sha, request_id=request_id)
            trailer["request_id"] = request_id
            page["items"][0]["text"] = "different"
            return validate_records(seal(header, [page], trailer))

    with pytest.raises(ConflictError):
        await service.execute(revision.id, Different())
    await session.refresh(document)
    assert (await service.manifest(document.id)).revision is not None
    assert (await service.text_items(document.id, revision.id, 1))[
        0
    ].raw_text == "Dose 5 mg"


async def test_scoped_bounded_query_and_disabled_source(session, tmp_path):
    document, _, revision = await setup_revision(session, tmp_path)
    service = DocumentAnchorService(session)
    with pytest.raises(NotFoundError):
        await service.page_quality(document.id, revision.id, 1)
    await service.execute(revision.id, _FixedExtractor())
    with pytest.raises(ValueError):
        await service.text_items(document.id, revision.id, 1, limit=201)
    assert await service.text_items(document.id, revision.id, 1, start=99) == []
    item = (await service.text_items(document.id, revision.id, 1, limit=1))[0]
    assert json.loads(item.char_map_json) and item.raw_utf16_length == 9
    source = await session.get(KnowledgeSource, document.knowledge_source_id)
    source.enabled = False
    await session.commit()
    with pytest.raises(PermissionDeniedError):
        await service.get_revision(revision.id)


async def test_queued_task_cancel_updates_revision_immediately(session, tmp_path):
    _, _, revision = await setup_revision(session, tmp_path)
    await TaskService(TaskRepository(session)).cancel(revision.task_id)
    await session.commit()
    stored = await session.get(DocumentAnchorRevision, revision.id)
    assert stored.state == "cancelled"


async def test_cancel_running_worker_does_not_publish(session, tmp_path, monkeypatch):
    _, _, revision = await setup_revision(session, tmp_path)
    started = asyncio.Event()

    async def slow(self, *args):
        started.set()
        await asyncio.sleep(60)

    monkeypatch.setattr(PdfTextItemExtractor, "extract", slow)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    running = asyncio.create_task(DocumentAnchorWorker(factory).run_once())
    await asyncio.wait_for(started.wait(), 5)
    async with factory() as other:
        await TaskService(TaskRepository(other)).cancel(revision.task_id)
        await other.commit()
    assert await asyncio.wait_for(running, 5)
    async with factory() as other:
        stored = await other.get(DocumentAnchorRevision, revision.id)
        task = await other.get(TaskRecord, revision.task_id)
        assert stored.state == "cancelled" and task.status == "cancelled"
        assert (
            await other.scalar(select(func.count()).select_from(DocumentSourcePage))
            == 0
        )


async def test_expired_lease_is_recovered_with_real_extraction(session, tmp_path):
    _, _, revision = await setup_revision(session, tmp_path)
    await session.execute(
        update(TaskRecord)
        .where(TaskRecord.id == revision.task_id)
        .values(
            status="running",
            lease_owner="dead-worker",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    await session.commit()
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    assert await DocumentAnchorWorker(factory).run_once()
    async with factory() as other:
        task = await other.get(TaskRecord, revision.task_id)
        assert task.status == "succeeded" and task.progress == 100


async def test_expired_owner_cannot_renew_its_lease(session, tmp_path):
    _, _, revision = await setup_revision(session, tmp_path)
    await session.execute(
        update(TaskRecord)
        .where(TaskRecord.id == revision.task_id)
        .values(
            status="running",
            lease_owner="expired-worker",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    assert not await TaskRepository(session).renew_lease(
        revision.task_id, "expired-worker", 60
    )


async def test_publishing_task_rejects_cancellation_without_state_change(session, tmp_path):
    _, _, revision = await setup_revision(session, tmp_path)
    task = await session.get(TaskRecord, revision.task_id)
    task.phase = "publishing"
    await session.commit()
    with pytest.raises(ConflictError, match="can no longer be cancelled"):
        await TaskService(TaskRepository(session)).cancel(revision.task_id)
    await session.refresh(task)
    assert task.status == "queued" and task.phase == "publishing"


async def test_cancel_during_real_publish_returns_conflict_immediately(
    session, tmp_path, monkeypatch
):
    _, _, revision = await setup_revision(session, tmp_path)
    from app.modules.document_anchor import service as service_module

    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked_publish(_session, _revision, _stream):
        entered.set()
        await release.wait()

    monkeypatch.setattr(service_module, "publish", blocked_publish)
    monkeypatch.setattr(PdfTextItemExtractor, "extract", _FixedExtractor().extract)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    running = asyncio.create_task(DocumentAnchorWorker(factory).run_once())
    await asyncio.wait_for(entered.wait(), 5)
    async with factory() as other:
        with pytest.raises(ConflictError, match="can no longer be cancelled"):
            await asyncio.wait_for(
                TaskService(TaskRepository(other)).cancel(revision.task_id), 1
            )
    release.set()
    assert await asyncio.wait_for(running, 5)


async def test_concurrent_submissions_share_revision_and_task(session, tmp_path):
    document, _ = await create_document(session, tmp_path / "source")
    await session.commit()
    document_id, file_hash = document.id, document.file_hash
    factory = async_sessionmaker(session.bind, expire_on_commit=False)

    async def submit():
        async with factory() as other:
            result = await DocumentAnchorService(other).request(
                document_id, AnchorRevisionRequest(expected_file_hash=file_hash)
            )
            await other.commit()
            return result

    first, second = await asyncio.gather(submit(), submit())
    assert first.id == second.id and first.task_id == second.task_id


async def test_transient_retries_are_bounded_and_eventually_fail(
    session, tmp_path, monkeypatch
):
    _, _, revision = await setup_revision(session, tmp_path)

    async def fail(self, *args):
        raise ExtractorExecutionError("anchor_process_failed")

    monkeypatch.setattr(PdfTextItemExtractor, "extract", fail)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    worker = DocumentAnchorWorker(factory)
    for _ in range(3):
        assert await worker.run_once()
    assert not await worker.run_once()
    async with factory() as other:
        task = await other.get(TaskRecord, revision.task_id)
        assert task.status == "failed" and task.retry_count == 3
        assert task.active_idempotency_key is None
        await TaskService(TaskRepository(other)).retry(task.id)
        await other.commit()

    async def succeeds(self, path, sha, request_id):
        return await _FixedExtractor().extract(path, sha, request_id)

    monkeypatch.setattr(PdfTextItemExtractor, "extract", succeeds)
    assert await worker.run_once()
    async with factory() as other:
        task = await other.get(TaskRecord, revision.task_id)
        assert task.status == "succeeded" and task.retry_count == 1


async def test_reclaimed_lease_cannot_publish_or_overwrite_new_owner(
    session, tmp_path, monkeypatch
):
    _, _, revision = await setup_revision(session, tmp_path)
    started, release = asyncio.Event(), asyncio.Event()

    async def paused(self, path, sha, request_id):
        started.set()
        await release.wait()
        return await _FixedExtractor().extract(path, sha, request_id)

    monkeypatch.setattr(PdfTextItemExtractor, "extract", paused)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    running = asyncio.create_task(DocumentAnchorWorker(factory).run_once())
    await asyncio.wait_for(started.wait(), 5)
    async with factory() as other:
        await other.execute(
            update(TaskRecord)
            .where(TaskRecord.id == revision.task_id)
            .values(lease_owner="new-owner")
        )
        await other.commit()
    release.set()
    assert await running
    async with factory() as other:
        task = await other.get(TaskRecord, revision.task_id)
        assert task.status == "running" and task.lease_owner == "new-owner"
        assert (
            await other.scalar(select(func.count()).select_from(DocumentSourcePage))
            == 0
        )


async def test_heartbeat_renews_during_long_extraction(session, tmp_path, monkeypatch):
    _, _, revision = await setup_revision(session, tmp_path)
    from app.modules.document_anchor import worker as module

    monkeypatch.setattr(module, "_LEASE_SECONDS", 1)
    monkeypatch.setattr(module, "_HEARTBEAT_SECONDS", 0.1)

    async def slow(self, path, sha, request_id):
        await asyncio.sleep(1.5)
        return await _FixedExtractor().extract(path, sha, request_id)

    monkeypatch.setattr(PdfTextItemExtractor, "extract", slow)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    assert await DocumentAnchorWorker(factory).run_once()
    async with factory() as other:
        task = await other.get(TaskRecord, revision.task_id)
        assert task.status == "succeeded"
