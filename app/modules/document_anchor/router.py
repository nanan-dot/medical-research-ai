"""Minimal HTTP surface for A0 revision submission and diagnostics."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_anchor.extractor_runner import PdfTextItemExtractor
from app.modules.document_anchor.schema import (
    AnchorManifestRead,
    AnchorRevisionRead,
    AnchorRevisionRequest,
    SourcePageQualityRead,
)
from app.modules.document_anchor.service import DocumentAnchorService

router = APIRouter(tags=["document-anchor"])


@router.post(
    "/documents/{document_id}/anchor-revisions", response_model=AnchorRevisionRead
)
async def request_anchor_revision(
    document_id: int,
    payload: AnchorRevisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=128)
    ] = None,
) -> AnchorRevisionRead:
    """Queue one stable A0 extraction; body file hash prevents stale submissions."""
    revision = await DocumentAnchorService(session).request(
        document_id, payload, idempotency_key
    )
    response.status_code = (
        status.HTTP_200_OK if revision.task_id is None else status.HTTP_202_ACCEPTED
    )
    return revision


@router.get(
    "/documents/{document_id}/anchor-manifest", response_model=AnchorManifestRead
)
async def get_anchor_manifest(
    document_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> AnchorManifestRead:
    return await DocumentAnchorService(session).manifest(document_id)


@router.get(
    "/document-anchor-revisions/{revision_id}", response_model=AnchorRevisionRead
)
async def get_anchor_revision(
    revision_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> AnchorRevisionRead:
    return await DocumentAnchorService(session).get_revision(revision_id)


@router.get(
    "/documents/{document_id}/anchor-revisions/{revision_id}/pages/{page_number}/quality",
    response_model=SourcePageQualityRead,
)
async def get_anchor_page_quality(
    document_id: int,
    revision_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    page_number: int = Path(ge=1),
) -> SourcePageQualityRead:
    return await DocumentAnchorService(session).page_quality(
        document_id, revision_id, page_number
    )


@router.get(
    "/document-anchor-revisions/{revision_id}/pages/{page_number}/quality",
    response_model=SourcePageQualityRead,
)
async def get_revision_page_quality(
    revision_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    page_number: int = Path(ge=1),
) -> SourcePageQualityRead:
    service = DocumentAnchorService(session)
    revision = await service.get_revision(revision_id)
    return await service.page_quality(revision.document_id, revision_id, page_number)


@router.get("/document-anchor-capability")
async def get_anchor_capability() -> dict[str, object]:
    return {"status": "AVAILABLE", "toolchain": await PdfTextItemExtractor().probe()}
