"""Shared fixtures for the library acceptance tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401 - register all acceptance-test models.
from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource


@pytest.fixture
def library_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[TestClient, Callable[..., int], Path]]:
    """Expose an isolated HTTP client and a synchronous document seeder."""

    database_path = tmp_path / "library.db"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source_ids: dict[tuple[str, str], int] = {}
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def seed_document(
        *,
        source_name: str = "Local source",
        source_type: str = "local_folder",
        relative_path: str = "notes/paper.md",
        parse_status: str = "pending",
        index_status: str = "pending",
        index_key: str | None = None,
        parsed_content: str | None = None,
        error_code: str | None = None,
        source_id: int | None = None,
        file_bytes: bytes = b"# test\nbody",
    ) -> int:
        async def insert() -> int:
            async with session_factory() as session:
                if source_id is None:
                    source_key = (source_name, source_type)
                    existing_id = source_ids.get(source_key)
                    if existing_id is None:
                        root = source_root / f"{source_type}-{source_name}"
                        root.mkdir()
                        source = KnowledgeSource(
                            name=source_name,
                            source_type=source_type,
                            root_path=str(root),
                            normalized_root_path=str(root).casefold(),
                            enabled=True,
                            sync_status="idle",
                        )
                        session.add(source)
                        await session.flush()
                        source_ids[source_key] = source.id
                    else:
                        source = await session.get(KnowledgeSource, existing_id)
                        assert source is not None
                        root = Path(source.root_path)
                else:
                    source = await session.get(KnowledgeSource, source_id)
                    assert source is not None
                    root = Path(source.root_path)
                path = root.joinpath(*relative_path.replace("\\", "/").split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(file_bytes)
                stat = path.stat()
                document = Document(
                    knowledge_source_id=source.id,
                    file_path=relative_path,
                    normalized_file_path=relative_path.replace("\\", "/").casefold(),
                    file_hash=f"{source.id:064x}"[-64:],
                    file_size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime, UTC),
                    modified_time_ns=stat.st_mtime_ns,
                    scan_state="pending",
                    parse_status=parse_status,
                    index_status=index_status,
                    paperqa_index_key=index_key,
                    parsed_content=parsed_content,
                    error_code=error_code,
                )
                session.add(document)
                await session.commit()
                return document.id

        return asyncio.run(insert())

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client, seed_document, source_root
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
