from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.knowledge_source.schema import KnowledgeSourceCreate, KnowledgeSourceType
from app.modules.knowledge_source.service import KnowledgeSourceService


@pytest.fixture
async def session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'documents.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def create_document(
    session,
    root: Path,
    name: str = "paper.txt",
    parse_status: str = "pending",
    index_status: str = "pending",
) -> tuple[Document, Path]:
    root.mkdir(exist_ok=True)
    file_path = root / name
    file_path.write_text("test fixture", encoding="utf-8")
    source = await KnowledgeSourceService(session).create(
        KnowledgeSourceCreate(
            name=root.name,
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )
    stat = file_path.stat()
    document = await DocumentRepository(session).create(
        Document(
            knowledge_source_id=source.id,
            file_path=name,
            normalized_file_path=name,
            file_hash="a" * 64,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime, UTC),
            modified_time_ns=stat.st_mtime_ns,
            scan_state="pending",
            parse_status=parse_status,
            index_status=index_status,
        )
    )
    return document, file_path
