"""OCR 任务创建、运行和结果回写。"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.parsers.schemas import ParsedDocument, ParsedPage
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import IndexStatus, ParseStatus
from app.modules.document_ocr.engine import (
    OcrEngineUnavailableError,
    OcrPageProcessingError,
    TesseractOcrEngine,
)
from app.modules.document_ocr.model import DocumentOcrJob, DocumentOcrPage
from app.modules.document_ocr.output_storage import persist_ocr_output
from app.modules.document_ocr.repository import DocumentOcrRepository
from app.modules.document_ocr.schema import OcrJobRead, OcrJobStatus, OcrPageRead
from app.modules.document_preview.service import DocumentPreviewService


class OcrJobConflictError(ConflictError):
    code = "ocr_job_conflict"


class DocumentOcrService:
    """创建和查询 OCR 任务；实际耗时执行由独立 runner 完成。"""

    def __init__(self, session: AsyncSession, engine: TesseractOcrEngine | None = None):
        self._documents = DocumentRepository(session)
        self._jobs = DocumentOcrRepository(session)
        self._previews = DocumentPreviewService(session)
        self._engine = engine or TesseractOcrEngine()

    async def request(self, document_id: int) -> OcrJobRead:
        document = await self._get_document(document_id)
        await self._previews.get_pdf_path(document_id)
        latest_job = await self._jobs.latest_job(document_id)
        if latest_job and latest_job.status in {
            OcrJobStatus.QUEUED.value,
            OcrJobStatus.PROCESSING.value,
        }:
            raise OcrJobConflictError("该文档已有正在进行的 OCR 任务")

        try:
            engine_info = await asyncio.to_thread(self._engine.probe)
            job = DocumentOcrJob(
                document_id=document.id,
                status=OcrJobStatus.QUEUED.value,
                engine_name=engine_info.name,
                engine_version=engine_info.version,
                language=settings.OCR_LANGUAGE,
            )
        except OcrEngineUnavailableError as exc:
            job = DocumentOcrJob(
                document_id=document.id,
                status=OcrJobStatus.FAILED.value,
                engine_name="tesseract",
                language=settings.OCR_LANGUAGE,
                error_code="ocr_engine_unavailable",
                error_message=str(exc),
                finished_at=datetime.now(UTC),
            )
        job = await self._jobs.create_job(job)
        return await self._to_read(job)

    async def latest(self, document_id: int) -> OcrJobRead | None:
        await self._get_document(document_id)
        job = await self._jobs.latest_job(document_id)
        return await self._to_read(job) if job else None

    async def request_cancel(self, document_id: int) -> OcrJobRead:
        job = await self._jobs.latest_job(document_id)
        if job is None:
            raise NotFoundError("OCR 任务不存在")
        if job.status not in {OcrJobStatus.QUEUED.value, OcrJobStatus.PROCESSING.value}:
            raise OcrJobConflictError("当前 OCR 任务无法取消")
        job.cancel_requested = True
        job = await self._jobs.save_job(job)
        return await self._to_read(job)

    async def _get_document(self, document_id: int) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("文档不存在")
        return document

    async def _to_read(self, job: DocumentOcrJob) -> OcrJobRead:
        pages = await self._jobs.list_pages(job.id)
        return OcrJobRead(
            id=job.id,
            document_id=job.document_id,
            status=job.status,
            engine_name=job.engine_name,
            engine_version=job.engine_version,
            language=job.language,
            page_count=job.page_count,
            completed_pages=job.completed_pages,
            failed_pages=job.failed_pages,
            output_sha256=job.output_sha256,
            error_code=job.error_code,
            error_message=job.error_message,
            cancel_requested=job.cancel_requested,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            pages=[
                OcrPageRead(
                    page_number=page.page_number,
                    text=page.text,
                    confidence=page.confidence,
                    error_code=page.error_code,
                    error_message=page.error_message,
                )
                for page in pages
            ],
        )


class DocumentOcrRunner:
    """在独立数据库会话中执行逐页 OCR，HTTP 请求不等待其完成。"""

    def __init__(self, session: AsyncSession, engine: TesseractOcrEngine | None = None):
        self._session = session
        self._documents = DocumentRepository(session)
        self._jobs = DocumentOcrRepository(session)
        self._previews = DocumentPreviewService(session)
        self._engine = engine or TesseractOcrEngine()

    async def run(self, job_id: int) -> None:
        job = await self._jobs.get_job(job_id)
        if job is None or job.status != OcrJobStatus.QUEUED.value:
            return
        try:
            await self._mark_processing(job)
            document = await self._get_document(job.document_id)
            pdf_path = await self._previews.get_pdf_path(document.id)
            page_count = await asyncio.to_thread(self._engine.page_count, pdf_path)
            if page_count > settings.OCR_MAX_PAGES:
                await self._mark_failed(
                    job, "ocr_page_limit_exceeded", "PDF 页数超过 OCR 安全上限"
                )
                return
            job.page_count = page_count
            await self._jobs.save_job(job)
            await self._session.commit()

            for page_number in range(1, page_count + 1):
                await self._session.refresh(job)
                if job.cancel_requested:
                    await self._mark_cancelled(job)
                    return
                await self._process_page(job, pdf_path, page_number)

            pages = await self._jobs.list_pages(job.id)
            successful_pages = [page for page in pages if page.text is not None]
            if not successful_pages:
                await self._mark_failed(
                    job, "ocr_no_page_succeeded", "没有页面成功完成 OCR"
                )
                return
            output_path, output_hash = await asyncio.to_thread(
                persist_ocr_output,
                job.id,
                successful_pages,
            )
            await self._apply_ocr_result(document, pages)
            job.output_relative_path = output_path
            job.output_sha256 = output_hash
            job.status = (
                OcrJobStatus.SUCCEEDED.value
                if job.failed_pages == 0
                else OcrJobStatus.PARTIAL_FAILED.value
            )
            job.finished_at = datetime.now(UTC)
            job.error_code = None
            job.error_message = None
            await self._jobs.save_job(job)
            await self._session.commit()
        except asyncio.CancelledError:
            if job is not None:
                await self._mark_cancelled(job)
            return
        except OcrEngineUnavailableError as exc:
            await self._mark_failed(job, "ocr_engine_unavailable", str(exc))
        except Exception:
            await self._mark_failed(job, "ocr_execution_failed", "OCR 任务执行失败")

    async def _mark_processing(self, job: DocumentOcrJob) -> None:
        job.status = OcrJobStatus.PROCESSING.value
        job.started_at = datetime.now(UTC)
        job.error_code = None
        job.error_message = None
        await self._jobs.save_job(job)
        await self._session.commit()

    async def _process_page(
        self, job: DocumentOcrJob, pdf_path, page_number: int
    ) -> None:
        try:
            result = await asyncio.to_thread(
                self._engine.extract_page,
                pdf_path,
                page_number,
                job.language,
            )
            page = DocumentOcrPage(
                job_id=job.id,
                page_number=page_number,
                text=result.text,
                confidence=result.confidence,
                text_sha256=hashlib.sha256(result.text.encode("utf-8")).hexdigest(),
            )
            job.completed_pages += 1
        except OcrPageProcessingError:
            page = DocumentOcrPage(
                job_id=job.id,
                page_number=page_number,
                error_code="ocr_page_failed",
                error_message=f"第 {page_number} 页 OCR 失败",
            )
            job.failed_pages += 1
        await self._jobs.create_page(page)
        await self._jobs.save_job(job)
        await self._session.commit()

    async def _apply_ocr_result(
        self,
        document: Document,
        pages: list[DocumentOcrPage],
    ) -> None:
        parsed = ParsedDocument(
            source_path=f"ocr://document/{document.id}",
            title=document.parsed_title,
            text="\n\n".join(page.text or "" for page in pages),
            pages=[
                ParsedPage(page_number=page.page_number, text=page.text or "")
                for page in pages
            ],
            is_scanned=True,
        )
        document.parsed_content = parsed.model_dump_json()
        document.parsed_is_scanned = True
        document.parsed_page_count = len(pages)
        document.parse_status = ParseStatus.SUCCEEDED.value
        document.index_status = IndexStatus.OUTDATED.value
        document.indexed_hash = None
        document.index_error = None
        document.error_code = None
        document.error_message = None
        await self._documents.save(document)

    async def _mark_failed(self, job: DocumentOcrJob, code: str, message: str) -> None:
        job.status = OcrJobStatus.FAILED.value
        job.error_code = code
        job.error_message = message
        job.finished_at = datetime.now(UTC)
        await self._jobs.save_job(job)
        await self._session.commit()

    async def _mark_cancelled(self, job: DocumentOcrJob) -> None:
        job.status = OcrJobStatus.CANCELLED.value
        job.finished_at = datetime.now(UTC)
        await self._jobs.save_job(job)
        await self._session.commit()

    async def _get_document(self, document_id: int) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("文档不存在")
        return document
