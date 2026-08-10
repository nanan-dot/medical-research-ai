from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base
from app.modules.document.model import Document
from app.modules.document_ocr.engine import (
    OcrEngineInfo,
    OcrEngineUnavailableError,
    OcrPageProcessingError,
    OcrPageResult,
)
from app.modules.document_ocr.repository import DocumentOcrRepository
from app.modules.document_ocr.service import DocumentOcrRunner, DocumentOcrService
from app.modules.knowledge_source.model import KnowledgeSource


class SuccessfulOcrEngine:
    def probe(self) -> OcrEngineInfo:
        return OcrEngineInfo(name="fake-tesseract", version="1.0")

    def page_count(self, _: Path) -> int:
        return 2

    def extract_page(self, _: Path, page_number: int, __: str) -> OcrPageResult:
        return OcrPageResult(text=f"识别页面 {page_number}")


class PartialFailureOcrEngine(SuccessfulOcrEngine):
    def extract_page(self, _: Path, page_number: int, __: str) -> OcrPageResult:
        if page_number == 2:
            raise OcrPageProcessingError("simulated page failure")
        return OcrPageResult(text="第一页识别文本")


class UnavailableOcrEngine:
    def probe(self) -> OcrEngineInfo:
        raise OcrEngineUnavailableError("test engine unavailable")


@pytest.fixture
async def ocr_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "OCR_OUTPUT_DIR", tmp_path / "ocr-output")
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'ocr.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    root = tmp_path / "source"
    root.mkdir()
    pdf_path = root / "scanned.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as stream:
        writer.write(stream)

    async with session_factory() as session:
        source = KnowledgeSource(
            name="ocr source",
            source_type="local_folder",
            root_path=str(root),
            normalized_root_path=str(root).casefold(),
            enabled=True,
            sync_status="idle",
        )
        session.add(source)
        await session.flush()
        stat = pdf_path.stat()
        document = Document(
            knowledge_source_id=source.id,
            file_path=pdf_path.name,
            normalized_file_path=pdf_path.name,
            file_hash="a" * 64,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime, UTC),
            modified_time_ns=stat.st_mtime_ns,
            scan_state="pending",
            parse_status="succeeded",
            index_status="succeeded",
            parsed_is_scanned=True,
        )
        session.add(document)
        await session.commit()
        yield session_factory, document.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_ocr_runner_persists_real_page_results_and_marks_index_outdated(ocr_context):
    session_factory, document_id = ocr_context
    async with session_factory() as session:
        service = DocumentOcrService(session, SuccessfulOcrEngine())
        requested = await service.request(document_id)
        assert requested.status == "queued"
        await session.commit()

        await DocumentOcrRunner(session, SuccessfulOcrEngine()).run(requested.id)
        job = await DocumentOcrRepository(session).get_job(requested.id)
        document = await session.get(Document, document_id)
        assert job is not None
        assert document is not None
        assert job.status == "succeeded"
        assert job.completed_pages == 2
        assert job.failed_pages == 0
        assert job.output_sha256 is not None
        assert document.parsed_is_scanned is True
        assert document.index_status == "outdated"
        assert document.parsed_content is not None
        assert "识别页面 1" in document.parsed_content


@pytest.mark.asyncio
async def test_ocr_runner_records_partial_page_failure_without_faking_text(ocr_context):
    session_factory, document_id = ocr_context
    async with session_factory() as session:
        requested = await DocumentOcrService(session, PartialFailureOcrEngine()).request(document_id)
        await session.commit()
        await DocumentOcrRunner(session, PartialFailureOcrEngine()).run(requested.id)

        job = await DocumentOcrRepository(session).get_job(requested.id)
        pages = await DocumentOcrRepository(session).list_pages(requested.id)
        assert job is not None
        assert job.status == "partial_failed"
        assert job.completed_pages == 1
        assert job.failed_pages == 1
        assert pages[1].text is None
        assert pages[1].error_code == "ocr_page_failed"


@pytest.mark.asyncio
async def test_engine_unavailable_is_a_persisted_failed_job(ocr_context):
    session_factory, document_id = ocr_context
    async with session_factory() as session:
        job = await DocumentOcrService(session, UnavailableOcrEngine()).request(document_id)

        assert job.status == "failed"
        assert job.error_code == "ocr_engine_unavailable"
