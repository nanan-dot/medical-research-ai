"""扫描 PDF OCR 任务 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_ocr.scheduler import OcrTaskScheduler
from app.modules.document_ocr.schema import OcrJobRead
from app.modules.document_ocr.service import DocumentOcrService

router = APIRouter(tags=["document-ocr"])


@router.post(
    "/documents/{document_id}/ocr",
    response_model=OcrJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_ocr(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OcrJobRead:
    job = await DocumentOcrService(session).request(document_id)
    await session.commit()
    if job.status == "queued":
        OcrTaskScheduler.schedule(job.id)
    return job


@router.get("/documents/{document_id}/ocr", response_model=OcrJobRead | None)
async def get_latest_ocr_job(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OcrJobRead | None:
    return await DocumentOcrService(session).latest(document_id)


@router.post("/documents/{document_id}/ocr/cancel", response_model=OcrJobRead)
async def cancel_ocr(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OcrJobRead:
    job = await DocumentOcrService(session).request_cancel(document_id)
    await session.commit()
    OcrTaskScheduler.cancel(job.id)
    return job
