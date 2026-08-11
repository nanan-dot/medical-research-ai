from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import NotFoundError
from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.research_context.schema import ResearchContextCreate
from app.modules.research_context.service import ResearchContextService
from tests.modules.document.conftest import create_document


@pytest.fixture
async def service(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'context.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield ResearchContextService(session), session
    await engine.dispose()


@pytest.mark.asyncio
async def test_context_persists_real_document_associations(service, tmp_path: Path) -> None:
    context_service, session = service
    document, _ = await create_document(session, tmp_path / "paper.pdf", "paper.pdf")
    context = await context_service.create(
        ResearchContextCreate(name="EGFR review", description="scope")
    )

    attached = await context_service.add_documents(context.id, [document.id])

    assert attached.document_ids == [document.id]
    assert (await context_service.get(context.id)).document_ids == [document.id]


@pytest.mark.asyncio
async def test_context_rejects_unknown_document_without_affecting_unlinked_data(
    service,
) -> None:
    context_service, _ = service
    context = await context_service.create(ResearchContextCreate(name="Review"))

    with pytest.raises(NotFoundError, match="Document not found"):
        await context_service.add_documents(context.id, [999])

    assert (await context_service.get(context.id)).document_ids == []
