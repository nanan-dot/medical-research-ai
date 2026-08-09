from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.core.database import get_session
from app.modules.literature_search.status_classifier import Status, classify
from app.modules.literature_search.status_model import LiteratureStatusRecord
from app.modules.literature_search.status_schema import (
    LiteratureStatusPersistRequest,
    LiteratureStatusRead,
    LiteratureStatusRequest,
)

router = APIRouter(prefix="/literature-status", tags=["literature-status"])
@router.post("/check", response_model=LiteratureStatusRead)
async def check_status(payload: LiteratureStatusRequest) -> LiteratureStatusRead:
    return LiteratureStatusRead(status=classify(**payload.model_dump()))

@router.post("/check-and-save", response_model=LiteratureStatusRead)
async def check_and_save(payload: LiteratureStatusPersistRequest, session: AsyncSession = Depends(get_session)) -> LiteratureStatusRead:
    status_type = classify(**payload.model_dump(exclude={"document_id", "source", "notice_url_or_id"}))
    record = LiteratureStatusRecord(document_id=payload.document_id, status_type=status_type, source=payload.source, notice_url_or_id=payload.notice_url_or_id)
    session.add(record); await session.flush(); await session.refresh(record)
    return LiteratureStatusRead(status=status_type, persistent=True, checked_at=record.checked_at)

@router.get("/documents/{document_id}", response_model=LiteratureStatusRead)
async def get_document_status(document_id: int, session: AsyncSession = Depends(get_session)) -> LiteratureStatusRead:
    row = await session.execute(select(LiteratureStatusRecord).where(LiteratureStatusRecord.document_id == document_id).order_by(LiteratureStatusRecord.checked_at.desc()))
    record = row.scalars().first()
    if record is None: raise NotFoundError("Literature status has not been checked")
    return LiteratureStatusRead(status=cast(Status, record.status_type), persistent=True, checked_at=record.checked_at)
