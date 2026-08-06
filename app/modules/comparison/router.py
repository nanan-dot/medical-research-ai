"""HTTP interface for comparison service; no persistence logic belongs here."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.comparison.schema import ComparisonCellEdit, ComparisonCreate, ComparisonTaskRead
from app.modules.comparison.service import ComparisonExportFormat, ComparisonService

router = APIRouter(prefix="/comparisons")


def service(session: AsyncSession = Depends(get_session)) -> ComparisonService:
    return ComparisonService(session)


@router.post("", response_model=ComparisonTaskRead, status_code=201)
async def create_comparison(
    payload: ComparisonCreate,
    comparison_service: ComparisonService = Depends(service),
) -> ComparisonTaskRead:
    return await comparison_service.create(payload)


@router.get("/{comparison_id}", response_model=ComparisonTaskRead)
async def get_comparison(
    comparison_id: int,
    comparison_service: ComparisonService = Depends(service),
) -> ComparisonTaskRead:
    return await comparison_service.get(comparison_id)


@router.patch("/{comparison_id}/cells", response_model=ComparisonTaskRead)
async def edit_comparison_cell(
    comparison_id: int,
    payload: ComparisonCellEdit,
    comparison_service: ComparisonService = Depends(service),
) -> ComparisonTaskRead:
    return await comparison_service.edit_cell(comparison_id, payload)


@router.post("/{comparison_id}/regenerate", response_model=ComparisonTaskRead)
async def regenerate_comparison(
    comparison_id: int,
    comparison_service: ComparisonService = Depends(service),
) -> ComparisonTaskRead:
    return await comparison_service.regenerate(comparison_id)


@router.get("/{comparison_id}/export")
async def export_comparison(
    comparison_id: int,
    export_format: Annotated[ComparisonExportFormat, Query(alias="format")] = "csv",
    comparison_service: ComparisonService = Depends(service),
) -> Response:
    content = await comparison_service.export(comparison_id, export_format)
    media_type = "text/csv; charset=utf-8" if export_format == "csv" else "text/markdown; charset=utf-8"
    filename = f"comparison-{comparison_id}.{ 'csv' if export_format == 'csv' else 'md'}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
