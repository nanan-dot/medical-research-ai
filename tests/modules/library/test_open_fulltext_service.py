"""Verified PMC acquisition tests use a local gateway and never call PMC."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base
from app.modules.library_item.model import LibraryItem
from app.modules.library_item.official_pmc_client import (
    DownloadedPmcPdf,
    VerifiedPmcFulltext,
)
from app.modules.library_item.open_fulltext_service import OpenFulltextService


class _Gateway:
    def __init__(self, verified: VerifiedPmcFulltext) -> None:
        self._verified = verified
        self.download_count = 0

    async def fetch_verified_fulltext(self, pmcid: str) -> VerifiedPmcFulltext:
        assert pmcid == self._verified.pmcid
        return self._verified

    async def download_pdf_to_path(
        self, pdf_url: str, destination: Path, maximum_bytes: int
    ) -> DownloadedPmcPdf:
        del pdf_url, maximum_bytes
        self.download_count += 1
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with destination.open("wb") as output:
            writer.write(output)
        content = destination.read_bytes()
        import hashlib

        return DownloadedPmcPdf(len(content), hashlib.sha256(content).hexdigest())

    async def aclose(self) -> None:
        return None


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'fulltext.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    previous_root = settings.OPEN_FULLTEXT_DIR
    settings.OPEN_FULLTEXT_DIR = tmp_path / "open_fulltext"
    try:
        yield factory
    finally:
        settings.OPEN_FULLTEXT_DIR = previous_root
        await engine.dispose()


async def _create_item(session: AsyncSession, *, pmid: str = "123") -> LibraryItem:
    item = LibraryItem(
        pmid=pmid,
        doi="10.1000/example",
        title="Example article",
        journal="Test Journal",
        year=2026,
        source_search_id=1,
        fulltext_status="metadata_only",
        fulltext_status_reason="No local PDF",
    )
    session.add(item)
    await session.commit()
    return item


@pytest.mark.asyncio
async def test_acquire_creates_link_only_after_verified_pdf(session_factory):
    async with session_factory() as session:
        item = await _create_item(session)
        gateway = _Gateway(
            VerifiedPmcFulltext(
                pmcid="PMC123456",
                pmid="123",
                doi="10.1000/example",
                license="CC BY 4.0",
                oai_record_url="https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/?id=123456",
                pdf_url="https://ftp.ncbi.nlm.nih.gov/pub/pmc/example.pdf",
            )
        )

        result = await OpenFulltextService(session, gateway=gateway).acquire(
            item.id, "PMC123456"
        )

        assert result.acquisition.status == "succeeded"
        assert result.item.pmcid == "PMC123456"
        assert result.item.fulltext_status == "local_pdf_available"
        assert result.item.document_id == result.acquisition.document_id
        assert gateway.download_count == 1
        assert list((settings.OPEN_FULLTEXT_DIR / "documents").glob("*.pdf"))


@pytest.mark.asyncio
async def test_identity_mismatch_is_persisted_without_downloading(session_factory):
    async with session_factory() as session:
        item = await _create_item(session)
        gateway = _Gateway(
            VerifiedPmcFulltext(
                pmcid="PMC456789",
                pmid="999",
                doi="10.2000/wrong",
                license="CC BY 4.0",
                oai_record_url="https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/?id=456789",
                pdf_url="https://ftp.ncbi.nlm.nih.gov/pub/pmc/wrong.pdf",
            )
        )

        result = await OpenFulltextService(session, gateway=gateway).acquire(
            item.id, "PMC456789"
        )

        assert result.acquisition.status == "identity_mismatch"
        assert result.item.document_id is None
        assert result.item.fulltext_status == "unavailable"
        assert gateway.download_count == 0


def test_bad_pmcid_is_rejected_at_request_boundary():
    from app.modules.library_item.open_fulltext_schema import OpenFulltextRequest

    with pytest.raises(ValueError):
        OpenFulltextRequest(pmcid="not-a-pmcid")
