from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError, PermissionDeniedError
from app.core.database import Base
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceType,
)
from app.modules.knowledge_source.service import (
    KnowledgeSourceService,
    normalize_authorized_directory,
)


@pytest.fixture
async def session(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("source_type", list(KnowledgeSourceType))
async def test_create_all_source_types(session, tmp_path: Path, source_type):
    root = tmp_path / source_type.value
    root.mkdir()
    entity = await KnowledgeSourceService(session).create(
        KnowledgeSourceCreate(
            name=source_type.value, source_type=source_type, root_path=str(root)
        )
    )
    assert entity.source_type == source_type.value
    assert entity.root_path == str(root.resolve())
    assert entity.enabled is True
    assert entity.sync_status == "idle"


@pytest.mark.asyncio
async def test_duplicate_and_case_equivalent_paths_are_rejected(
    session, tmp_path: Path
):
    root = tmp_path / "Papers"
    root.mkdir()
    service = KnowledgeSourceService(session)
    await service.create(
        KnowledgeSourceCreate(
            name="first",
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )
    duplicate = (
        str(root).swapcase()
        if Path(str(root).swapcase()).exists()
        else str(root / ".." / root.name)
    )
    with pytest.raises(ConflictError):
        await service.create(
            KnowledgeSourceCreate(
                name="second",
                source_type=KnowledgeSourceType.OBSIDIAN_VAULT,
                root_path=duplicate,
            )
        )


def test_missing_file_and_symlink_resolution(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        normalize_authorized_directory(str(tmp_path / "missing"))

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Current Windows account cannot create directory symlinks")
    display, canonical = normalize_authorized_directory(str(link))
    assert display == str(target.resolve())
    assert canonical == normalize_authorized_directory(str(target))[1]


def test_permission_denied_has_stable_error(tmp_path: Path, monkeypatch):
    root = tmp_path / "restricted"
    root.mkdir()
    monkeypatch.setattr(
        "app.modules.knowledge_source.service.os.access", lambda *_: False
    )
    with pytest.raises(PermissionDeniedError, match="not readable"):
        normalize_authorized_directory(str(root))


@pytest.mark.asyncio
async def test_moved_directory_becomes_unavailable(session, tmp_path: Path):
    root = tmp_path / "movable"
    root.mkdir()
    service = KnowledgeSourceService(session)
    entity = await service.create(
        KnowledgeSourceCreate(
            name="movable",
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )
    root.rename(tmp_path / "moved")
    refreshed = await service.get(entity.id)
    assert refreshed.sync_status == "unavailable"
    assert refreshed.error_message == "Knowledge source directory does not exist"


@pytest.mark.asyncio
async def test_delete_only_removes_record(session, tmp_path: Path):
    root = tmp_path / "papers"
    root.mkdir()
    paper = root / "keep-me.txt"
    paper.write_text("private content is never read", encoding="utf-8")
    service = KnowledgeSourceService(session)
    entity = await service.create(
        KnowledgeSourceCreate(
            name="papers",
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )
    await service.delete(entity.id)
    assert await service.repo.get(entity.id) is None
    assert paper.read_text(encoding="utf-8") == "private content is never read"
