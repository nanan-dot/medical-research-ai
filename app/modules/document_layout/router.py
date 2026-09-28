from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_layout.schema import (
    SectionRead,
    SegmentationManifestRead,
    SegmentationRead,
    SegmentPageRead,
    SegmentRead,
)
from app.modules.document_layout.service import DocumentLayoutService

router = APIRouter(tags=["document-layout"])


@router.post(
    "/document-anchor-revisions/{anchor_revision_id}/segmentations",
    response_model=SegmentationRead,
)
async def request_segmentation(
    anchor_revision_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=128)
    ] = None,
) -> SegmentationRead:
    result = await DocumentLayoutService(session).request(
        anchor_revision_id, idempotency_key
    )
    response.status_code = (
        status.HTTP_200_OK if result.task_id is None else status.HTTP_202_ACCEPTED
    )
    return result


@router.get(
    "/documents/{document_id}/segmentation-manifest",
    response_model=SegmentationManifestRead,
)
async def manifest(
    document_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> SegmentationManifestRead:
    return await DocumentLayoutService(session).manifest(document_id)


@router.get("/documents/{document_id}/source-segments", response_model=SegmentPageRead)
async def segments(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    expected_anchor_revision_id: int | None = Query(default=None, ge=1),
    expected_segmentation_revision_id: int | None = Query(default=None, ge=1),
) -> SegmentPageRead:
    return await DocumentLayoutService(session).segments(
        document_id, page, offset, limit,
        expected_anchor_revision_id=expected_anchor_revision_id,
        expected_segmentation_revision_id=expected_segmentation_revision_id,
    )


@router.get("/source-segments/{segment_id}", response_model=SegmentRead)
async def segment(
    segment_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> SegmentRead:
    return await DocumentLayoutService(session).get_segment(segment_id)


@router.get("/documents/{document_id}/sections", response_model=list[SectionRead])
async def sections(
    document_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> list[SectionRead]:
    return await DocumentLayoutService(session).sections(document_id)


@router.get(
    "/documents/{document_id}/sections/{section_id}/segments",
    response_model=SegmentPageRead,
)
async def section_segments(
    document_id: int,
    section_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> SegmentPageRead:
    return await DocumentLayoutService(session).section_segments(
        document_id, section_id, offset, limit
    )
