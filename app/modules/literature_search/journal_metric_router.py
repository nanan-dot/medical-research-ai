"""期刊指标 CSV 导入管理路由。"""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.journal_metric_schema import (
    JournalMetricImportBatchList,
    JournalMetricImportBatchRead,
    JournalMetricImportPreview,
)
from app.modules.literature_search.journal_metric_service import JournalMetricService

router = APIRouter(prefix="/journal-metrics/imports", tags=["Journal metrics"])


@router.get("", response_model=JournalMetricImportBatchList)
async def list_imports(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> JournalMetricImportBatchList:
    return await JournalMetricService(session).list_batches(offset, limit)


@router.post("/preview", response_model=JournalMetricImportPreview)
async def preview_import(
    file: UploadFile = File(...), session: AsyncSession = Depends(get_session)
) -> JournalMetricImportPreview:
    return await JournalMetricService(session).preview(file)


@router.post(
    "/commit",
    response_model=JournalMetricImportBatchRead,
    status_code=status.HTTP_201_CREATED,
)
async def commit_import(
    file: UploadFile = File(...),
    expected_file_hash: str = Form(..., min_length=64, max_length=64),
    provider: str = Form(..., min_length=1, max_length=100),
    provider_version: str = Form(..., min_length=1, max_length=100),
    edition_year: int = Form(..., ge=1900, le=2200),
    license_provenance: str = Form(..., min_length=1, max_length=5000),
    session: AsyncSession = Depends(get_session),
) -> JournalMetricImportBatchRead:
    return await JournalMetricService(session).commit(
        file,
        expected_file_hash=expected_file_hash,
        provider=provider,
        provider_version=provider_version,
        edition_year=edition_year,
        license_provenance=license_provenance,
    )


@router.post("/{batch_id}/activate", response_model=JournalMetricImportBatchRead)
async def activate_import(
    batch_id: int, session: AsyncSession = Depends(get_session)
) -> JournalMetricImportBatchRead:
    return await JournalMetricService(session).activate(batch_id)


@router.post("/{batch_id}/archive", response_model=JournalMetricImportBatchRead)
async def archive_import(
    batch_id: int, session: AsyncSession = Depends(get_session)
) -> JournalMetricImportBatchRead:
    return await JournalMetricService(session).archive(batch_id)
