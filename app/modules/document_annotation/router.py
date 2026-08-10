"""PDF 批注 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_annotation.schema import AnnotationCreate, AnnotationRead, AnnotationUpdate
from app.modules.document_annotation.service import DocumentAnnotationService

router = APIRouter(tags=["document-annotations"])


@router.get("/documents/{document_id}/annotations", response_model=list[AnnotationRead])
async def list_annotations(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AnnotationRead]:
    return await DocumentAnnotationService(session).list(document_id)


@router.post(
    "/documents/{document_id}/annotations",
    response_model=AnnotationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    document_id: int,
    payload: AnnotationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnnotationRead:
    return await DocumentAnnotationService(session).create(document_id, payload)


@router.patch(
    "/documents/{document_id}/annotations/{annotation_id}",
    response_model=AnnotationRead,
)
async def update_annotation(
    document_id: int,
    annotation_id: int,
    payload: AnnotationUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnnotationRead:
    return await DocumentAnnotationService(session).update(
        document_id,
        annotation_id,
        payload,
    )


@router.delete(
    "/documents/{document_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation(
    document_id: int,
    annotation_id: int,
    expected_file_hash: Annotated[str, Query(pattern=r"^[a-f0-9]{64}$")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await DocumentAnnotationService(session).delete(
        document_id,
        annotation_id,
        expected_file_hash,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
