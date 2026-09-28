"""Phase 1 medical translation HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_selection.service import SourceAnchorService
from app.modules.medical_translation.model import TranslationRevision
from app.modules.medical_translation.schema import (
    TranslationCorrectionCreate,
    TranslationJobCreate,
    TranslationJobRead,
    TranslationPrefetchIntentRead,
    TranslationRevisionPage,
    TranslationRevisionRead,
    TranslationSegmentIntentCreate,
    TranslationTermOverrideCreate,
    TranslationTermOverrideRead,
)
from app.modules.medical_translation.service import MedicalTranslationService

router = APIRouter(tags=["medical-translation"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/documents/{document_id}/translation-jobs",
    response_model=TranslationJobRead,
    status_code=202,
)
async def create_translation_job(
    document_id: int,
    payload: TranslationJobCreate,
    session: Session,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> TranslationJobRead:
    return await MedicalTranslationService(session).create_job(
        document_id, payload, idempotency_key
    )


@router.post(
    "/documents/{document_id}/translation-segment-intents",
    response_model=TranslationPrefetchIntentRead,
    status_code=202,
)
async def request_translation_segments(
    document_id: int,
    payload: TranslationSegmentIntentCreate,
    session: Session,
) -> TranslationPrefetchIntentRead:
    return await MedicalTranslationService(session).request_segments(document_id, payload)


@router.get("/translation-jobs/{job_id}", response_model=TranslationJobRead)
async def get_translation_job(job_id: int, session: Session) -> TranslationJobRead:
    return await MedicalTranslationService(session).get_job(job_id)


@router.post("/translation-jobs/{job_id}/cancel", response_model=TranslationJobRead)
async def cancel_translation_job(job_id: int, session: Session) -> TranslationJobRead:
    return await MedicalTranslationService(session).cancel(job_id)


@router.post(
    "/translation-jobs/{job_id}/retry",
    response_model=TranslationJobRead,
    status_code=202,
)
async def retry_translation_job(job_id: int, session: Session) -> TranslationJobRead:
    return await MedicalTranslationService(session).retry(job_id)


@router.get(
    "/documents/{document_id}/translations", response_model=TranslationRevisionPage
)
async def list_translations(
    document_id: int,
    session: Session,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TranslationRevisionPage:
    rows = list(
        (
            await session.scalars(
                select(TranslationRevision)
                .where(TranslationRevision.document_id == document_id)
                .order_by(
                    TranslationRevision.created_at.desc(), TranslationRevision.id.desc()
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    total = int(
        await session.scalar(
            select(func.count())
            .select_from(TranslationRevision)
            .where(TranslationRevision.document_id == document_id)
        )
        or 0
    )
    service = MedicalTranslationService(session)
    items = [await service.revision_read(row) for row in rows]
    return TranslationRevisionPage(items=items, total=total, offset=offset, limit=limit)


@router.get(
    "/documents/{document_id}/translation-term-overrides",
    response_model=list[TranslationTermOverrideRead],
)
async def list_translation_term_overrides(
    document_id: int, session: Session, target_language: str = "zh-CN"
) -> list[TranslationTermOverrideRead]:
    return await MedicalTranslationService(session).list_term_overrides(
        document_id, target_language
    )


@router.post(
    "/documents/{document_id}/translation-term-overrides",
    response_model=TranslationTermOverrideRead,
    status_code=201,
)
async def save_translation_term_override(
    document_id: int, payload: TranslationTermOverrideCreate, session: Session
) -> TranslationTermOverrideRead:
    return await MedicalTranslationService(session).save_term_override(
        document_id, payload
    )


@router.get(
    "/translation-revisions/{revision_id}", response_model=TranslationRevisionRead
)
async def get_translation_revision(
    revision_id: int, session: Session
) -> TranslationRevisionRead:
    revision = await session.get(TranslationRevision, revision_id)
    if revision is None:
        from app.common.exceptions import NotFoundError

        raise NotFoundError("Translation revision not found")
    await SourceAnchorService(session).get(
        revision.source_anchor_id, revision.document_id
    )
    return await MedicalTranslationService(session).revision_read(revision)


@router.post(
    "/translation-revisions/{revision_id}/corrections",
    response_model=TranslationRevisionRead,
    status_code=201,
)
async def correct_translation(
    revision_id: int, payload: TranslationCorrectionCreate, session: Session
) -> TranslationRevisionRead:
    return await MedicalTranslationService(session).correct(revision_id, payload)
