"""Shared immutable source references and anchored reading notes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.core.database import get_session
from app.modules.document_selection.assets import AnchoredAssetService
from app.modules.document_selection.context import load_context
from app.modules.document_selection.schema import (
    AnchorRead,
    ReadingNoteCreate,
    ReadingNoteRead,
    SelectionItemRead,
    SelectionPageRead,
    SelectionVersion,
    SourceAnchorDescriptor,
)
from app.modules.document_selection.service import SourceAnchorService

router = APIRouter(tags=["source-anchors"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/documents/{document_id}/selection-pages/{page_number}",
    response_model=SelectionPageRead,
)
async def selection_page(
    document_id: int,
    page_number: int,
    session: Session,
    version: Annotated[SelectionVersion, Query()],
) -> SelectionPageRead:
    context = await load_context(session, document_id, version, fence=False)
    page = context.pages.get(page_number)
    if page is None:
        raise NotFoundError("Source page not found")
    flow = {(item.page_number, item.item_index): item for item in context.flow}
    items = []
    for key, item in sorted(context.items.items()):
        if key[0] != page_number:
            continue
        mapped = flow.get(key)
        items.append(
            SelectionItemRead(
                item_index=item.item_index,
                source_array_index=item.source_array_index,
                text=item.raw_text,
                rank=mapped.rank if mapped else None,
                eligibility=mapped.eligibility if mapped else "blocked",
            )
        )
    return SelectionPageRead(
        page_number=page_number,
        rotation=page.rotation,
        anchor_revision_id=context.anchor.id,
        segmentation_revision_id=context.layout.id,
        pdfjs_version=context.anchor.pdfjs_version,
        items=items,
    )


@router.post(
    "/documents/{document_id}/source-anchors",
    response_model=AnchorRead,
    status_code=201,
)
async def create_anchor(
    document_id: int, payload: SourceAnchorDescriptor, session: Session
) -> AnchorRead:
    return await SourceAnchorService(session).create(document_id, payload)


@router.get("/source-anchors/{anchor_id}", response_model=AnchorRead)
async def read_anchor(anchor_id: int, session: Session) -> AnchorRead:
    return await SourceAnchorService(session).get(anchor_id)


@router.post(
    "/documents/{document_id}/reading-notes",
    response_model=ReadingNoteRead,
    status_code=201,
)
async def create_note(
    document_id: int,
    payload: ReadingNoteCreate,
    session: Session,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", max_length=128)],
) -> ReadingNoteRead:
    return await AnchoredAssetService(session).note(
        document_id, payload, idempotency_key
    )


@router.get(
    "/documents/{document_id}/reading-notes", response_model=list[ReadingNoteRead]
)
async def list_notes(document_id: int, session: Session) -> list[ReadingNoteRead]:
    return await AnchoredAssetService(session).notes(document_id)
