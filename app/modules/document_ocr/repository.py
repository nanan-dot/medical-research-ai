"""OCR 任务和逐页结果持久化访问。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_ocr.model import DocumentOcrJob, DocumentOcrPage


class DocumentOcrRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_job(self, job: DocumentOcrJob) -> DocumentOcrJob:
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_job(self, job_id: int) -> DocumentOcrJob | None:
        result = await self._session.execute(
            select(DocumentOcrJob).where(DocumentOcrJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def latest_job(self, document_id: int) -> DocumentOcrJob | None:
        result = await self._session.execute(
            select(DocumentOcrJob)
            .where(DocumentOcrJob.document_id == document_id)
            .order_by(DocumentOcrJob.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_pages(self, job_id: int) -> list[DocumentOcrPage]:
        result = await self._session.execute(
            select(DocumentOcrPage)
            .where(DocumentOcrPage.job_id == job_id)
            .order_by(DocumentOcrPage.page_number)
        )
        return list(result.scalars().all())

    async def create_page(self, page: DocumentOcrPage) -> DocumentOcrPage:
        self._session.add(page)
        await self._session.flush()
        await self._session.refresh(page)
        return page

    async def save_job(self, job: DocumentOcrJob) -> DocumentOcrJob:
        await self._session.flush()
        await self._session.refresh(job)
        return job
