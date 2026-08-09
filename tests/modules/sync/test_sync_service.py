import os
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base
from app.common.exceptions import ConflictError
from app.modules.document.repository import DocumentRepository
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceType,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.scanner import DirectoryScan
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService


@pytest.fixture
async def session(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'sync.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def create_source(session, root: Path):
    return await KnowledgeSourceService(session).create(
        KnowledgeSourceCreate(
            name="research files",
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )


@pytest.mark.asyncio
async def test_first_idempotent_modified_timestamp_and_deleted_sync(
    session, tmp_path: Path
):
    root = tmp_path / "source"
    root.mkdir()
    files = {
        "paper.pdf": b"%PDF-test",
        "notes.md": b"notes",
        "draft.docx": b"docx-placeholder",
        "readme.txt": b"text",
    }
    for name, content in files.items():
        (root / name).write_bytes(content)
    (root / "ignored.csv").write_text("ignored", encoding="utf-8")
    for ignored in (".obsidian", ".git", ".trash"):
        directory = root / ignored
        directory.mkdir()
        (directory / "hidden.md").write_text("must not scan", encoding="utf-8")

    source = await create_source(session, root)
    service = KnowledgeSourceSyncService(session)
    first = await service.sync(source.id)
    assert first.model_dump(
        include={"added", "modified", "deleted", "skipped", "failed"}
    ) == {
        "added": 4,
        "modified": 0,
        "deleted": 0,
        "skipped": 0,
        "failed": 0,
    }

    second = await service.sync(source.id)
    assert second.added == 0
    assert second.skipped == 4
    documents = await DocumentRepository(session).list_by_source(source.id)
    assert len(documents) == 4

    notes = root / "notes.md"
    notes.write_text("changed notes", encoding="utf-8")
    changed = await service.sync(source.id)
    assert changed.modified == 1
    changed_document = next(item for item in documents if item.file_path == "notes.md")
    assert changed_document.scan_state == "outdated"

    text = root / "readme.txt"
    old_stat = text.stat()
    os.utime(text, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 2_000_000_000))
    timestamp_only = await service.sync(source.id)
    assert timestamp_only.modified == 0
    assert timestamp_only.skipped == 4

    (root / "paper.pdf").unlink()
    deleted = await service.sync(source.id)
    assert deleted.deleted == 1
    assert len(await DocumentRepository(session).list_by_source(source.id)) == 3


@pytest.mark.asyncio
async def test_new_file_and_single_hash_failure_do_not_block_sync(
    session, tmp_path: Path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    good = root / "good.txt"
    locked = root / "locked.txt"
    good.write_text("good", encoding="utf-8")
    locked.write_text("locked", encoding="utf-8")
    source = await create_source(session, root)

    def selective_hash(path: Path) -> str:
        if path.name == "locked.txt":
            raise PermissionError("simulated file lock")
        return "a" * 64

    monkeypatch.setattr(
        "app.modules.knowledge_source.sync_service.sha256_file", selective_hash
    )
    summary = await KnowledgeSourceSyncService(session).sync(source.id)
    assert summary.added == 1
    assert summary.failed == 1
    assert summary.sync_status == "completed_with_errors"
    documents = await DocumentRepository(session).list_by_source(source.id)
    assert [document.file_path for document in documents] == ["good.txt"]
    assert "simulated file lock" not in (summary.error_message or "")


@pytest.mark.asyncio
async def test_failed_existing_file_is_not_deleted(
    session, tmp_path: Path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    paper = root / "paper.pdf"
    paper.write_bytes(b"%PDF-first")
    source = await create_source(session, root)
    service = KnowledgeSourceSyncService(session)
    await service.sync(source.id)
    paper.write_bytes(b"%PDF-changed")

    def locked_hash(_path: Path) -> str:
        raise OSError("locked")

    monkeypatch.setattr(
        "app.modules.knowledge_source.sync_service.sha256_file", locked_hash
    )
    summary = await service.sync(source.id)
    assert summary.failed == 1
    assert summary.deleted == 0
    assert len(await DocumentRepository(session).list_by_source(source.id)) == 1


@pytest.mark.asyncio
async def test_disabled_source_cannot_sync(session, tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    source = await create_source(session, root)
    source.enabled = False
    with pytest.raises(ConflictError, match="Disabled knowledge source"):
        await KnowledgeSourceSyncService(session).sync(source.id)


@pytest.mark.asyncio
async def test_temporary_directory_failure_preserves_existing_records(
    session, tmp_path: Path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "paper.txt").write_text("tracked", encoding="utf-8")
    source = await create_source(session, root)
    service = KnowledgeSourceSyncService(session)
    await service.sync(source.id)

    monkeypatch.setattr(
        "app.modules.knowledge_source.sync_service.scan_directory",
        lambda _root: DirectoryScan(failed_prefixes={""}, failures=1),
    )
    summary = await service.sync(source.id)
    assert summary.failed == 1
    assert summary.deleted == 0
    assert len(await DocumentRepository(session).list_by_source(source.id)) == 1
