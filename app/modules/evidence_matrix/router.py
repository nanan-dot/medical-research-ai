"""HTTP interface for evidence matrices; no persistence or generation logic here."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.evidence_matrix.schema import (
    EvidenceMatrixList,
    EvidenceMatrixRead,
    ExportRequest,
    MatrixCellEdit,
    MatrixCreate,
    MatrixDocumentAdd,
    MatrixDocumentRemove,
    MatrixDocumentUpdate,
    MatrixFieldAdd,
    MatrixUpdate,
)
from app.modules.evidence_matrix.service import EvidenceMatrixService

router = APIRouter(prefix="/evidence-matrices")


def service(session: AsyncSession = Depends(get_session)) -> EvidenceMatrixService:
    return EvidenceMatrixService(session)


@router.post("", response_model=EvidenceMatrixRead, status_code=201)
async def create_matrix(
    payload: MatrixCreate,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.create(
        name=payload.name,
        description=payload.description,
        fields=payload.fields,
        source_comparison_id=payload.source_comparison_id,
    )


@router.get("", response_model=EvidenceMatrixList)
async def list_matrices(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixList:
    items = await matrix_service.list_matrices(offset, limit)
    return EvidenceMatrixList(items=items, total=await matrix_service.count())


@router.get("/{matrix_id}", response_model=EvidenceMatrixRead)
async def get_matrix(
    matrix_id: int,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.get(matrix_id)


@router.patch("/{matrix_id}", response_model=EvidenceMatrixRead)
async def update_matrix(
    matrix_id: int,
    payload: MatrixUpdate,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.update(
        matrix_id,
        name=payload.name,
        description=payload.description,
        status=payload.status.value if payload.status else None,
    )


@router.delete("/{matrix_id}", status_code=204)
async def delete_matrix(
    matrix_id: int,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> None:
    await matrix_service.delete(matrix_id)
    return None


@router.post("/{matrix_id}/documents", response_model=EvidenceMatrixRead)
async def add_matrix_documents(
    matrix_id: int,
    payload: MatrixDocumentAdd,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.add_documents(matrix_id, payload.document_ids)


@router.delete("/{matrix_id}/documents", response_model=EvidenceMatrixRead)
async def remove_matrix_documents(
    matrix_id: int,
    payload: MatrixDocumentRemove,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.remove_documents(matrix_id, payload.document_ids)


@router.patch("/{matrix_id}/documents/{document_id}", response_model=EvidenceMatrixRead)
async def update_matrix_document(
    matrix_id: int,
    document_id: int,
    payload: MatrixDocumentUpdate,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.update_document(matrix_id, document_id, payload)


@router.post("/{matrix_id}/fields", response_model=EvidenceMatrixRead)
async def add_matrix_field(
    matrix_id: int,
    payload: MatrixFieldAdd,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.add_field(
        matrix_id, payload.field_key, payload.field_label
    )


@router.delete("/{matrix_id}/fields/{field_key}", response_model=EvidenceMatrixRead)
async def remove_matrix_field(
    matrix_id: int,
    field_key: str,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.remove_field(matrix_id, field_key)


@router.patch("/{matrix_id}/cells", response_model=EvidenceMatrixRead)
async def edit_matrix_cell(
    matrix_id: int,
    payload: MatrixCellEdit,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.edit_cell(matrix_id, payload)


@router.post("/{matrix_id}/regenerate", response_model=EvidenceMatrixRead)
async def regenerate_matrix(
    matrix_id: int,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> EvidenceMatrixRead:
    return await matrix_service.regenerate(matrix_id)


@router.post("/{matrix_id}/export")
async def export_matrix(
    matrix_id: int,
    payload: ExportRequest,
    matrix_service: EvidenceMatrixService = Depends(service),
) -> Response:
    content = await matrix_service.export(matrix_id, payload.format)
    media_type = (
        "text/csv; charset=utf-8"
        if payload.format == "csv"
        else "text/markdown; charset=utf-8"
    )
    filename = (
        f"evidence-matrix-{matrix_id}.{'csv' if payload.format == 'csv' else 'md'}"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
