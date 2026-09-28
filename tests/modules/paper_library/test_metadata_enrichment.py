"""可信元数据补全、失败可恢复及幂等验收。"""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base
from app.integrations.pubmed.exceptions import PubMedTimeoutError
from app.integrations.pubmed.schemas import PubMedRecord, PubMedSearchResult
from app.modules.library_item.model import LibraryItem
from app.modules.paper_library.metadata_service import PaperMetadataService


class SequencedMetadataClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.closed = 0

    async def search(self, query: str, *, retmax: int = 20) -> PubMedSearchResult:
        return PubMedSearchResult(pmids=["123"], total_count=1)

    async def fetch_records(self, pmids: list[str]) -> list[PubMedRecord]:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome  # type: ignore[return-value]

    async def aclose(self) -> None:
        self.closed += 1


@pytest.fixture
async def metadata_session(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'metadata.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def verified_record() -> PubMedRecord:
    return PubMedRecord(
        pmid="123",
        doi="10.1000/verified",
        title="Verified kidney trial",
        authors=["Researcher A", "Researcher B"],
        journal="Verified Journal",
        year=2025,
        publication_types=["Randomized Controlled Trial"],
    )


async def add_item(session, *, pmid: str | None = "123") -> LibraryItem:
    item = LibraryItem(
        pmid=pmid,
        doi=None if pmid else "10.1000/verified",
        source_search_id=None,
        fulltext_status="metadata_only",
        fulltext_status_reason="metadata pending",
    )
    session.add(item)
    await session.flush()
    return item


@pytest.mark.asyncio
async def test_pubmed_success_fills_only_blank_metadata(metadata_session):
    item = await add_item(metadata_session)
    item.title = "User-kept title"
    client = SequencedMetadataClient([[verified_record()]])

    await PaperMetadataService(
        metadata_session, client_factory=lambda: client
    ).enrich(item)

    assert item.metadata_status == "succeeded"
    assert item.metadata_source == "pubmed"
    assert item.title == "User-kept title"
    assert item.authors == "Researcher A; Researcher B"
    assert item.paper_type == "RCT"
    assert item.journal_quartile is None
    assert item.journal_quartile_source is None
    assert client.closed == 1


@pytest.mark.asyncio
async def test_timeout_is_observable_and_retry_can_succeed(metadata_session):
    item = await add_item(metadata_session)
    client = SequencedMetadataClient(
        [PubMedTimeoutError("upstream timeout"), [verified_record()]]
    )
    service = PaperMetadataService(metadata_session, client_factory=lambda: client)

    await service.enrich(item)
    assert item.metadata_status == "failed"
    assert item.metadata_error_code == "pubmed_timeout"
    assert item.metadata_retry_count == 1

    await service.enrich(item)
    assert item.metadata_status == "succeeded"
    assert item.metadata_error_code is None
    assert item.metadata_retry_count == 2


@pytest.mark.asyncio
async def test_no_result_and_identifier_conflict_are_not_fabricated(metadata_session):
    item = await add_item(metadata_session, pmid=None)
    no_result = SequencedMetadataClient([])

    async def empty_search(query: str, *, retmax: int = 20) -> PubMedSearchResult:
        return PubMedSearchResult(pmids=[], total_count=0)

    no_result.search = empty_search  # type: ignore[method-assign]
    await PaperMetadataService(
        metadata_session, client_factory=lambda: no_result
    ).enrich(item)

    assert item.metadata_status == "not_found"
    assert item.title is None
    assert item.metadata_error_code == "metadata_not_found"


@pytest.mark.asyncio
async def test_concurrent_metadata_refresh_keeps_both_attempts(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'metadata-race.db').as_posix()}",
        connect_args={"timeout": 10},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        paper = await add_item(session)
        await session.commit()
        item_id = paper.id

    async def refresh() -> None:
        async with factory() as session:
            current = await session.get(LibraryItem, item_id)
            assert current is not None
            await PaperMetadataService(
                session,
                client_factory=lambda: SequencedMetadataClient(
                    [[verified_record()]]
                ),
            ).enrich(current)
            await session.commit()

    import asyncio

    await asyncio.gather(refresh(), refresh())
    async with factory() as session:
        saved = await session.get(LibraryItem, item_id)
        assert saved is not None
        assert saved.metadata_status == "succeeded"
        assert saved.metadata_retry_count == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_late_identifier_uniqueness_conflict_is_returned_as_metadata_state(
    metadata_session, monkeypatch
):
    item = await add_item(metadata_session, pmid=None)
    metadata_session.add(
        LibraryItem(
            pmid="123",
            doi="10.1000/other-paper",
            source_search_id=None,
            fulltext_status="metadata_only",
            fulltext_status_reason="existing identity",
        )
    )
    await metadata_session.flush()
    service = PaperMetadataService(
        metadata_session,
        client_factory=lambda: SequencedMetadataClient([[verified_record()]]),
    )

    async def miss_race_window(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(service, "_identity_owned_by_another_item", miss_race_window)
    result = await service.enrich(item)

    assert result.metadata_status == "failed"
    assert result.metadata_error_code == "identifier_conflict"
    assert result.pmid is None
