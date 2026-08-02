from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.export.schema import ExportRead, MarkdownExportCreate
from app.modules.export.service import ExportService

router = APIRouter(prefix="/exports", tags=["导出"])


@router.post("/markdown", response_model=ExportRead)
async def create_export(
    request: MarkdownExportCreate, session: AsyncSession = Depends(get_session)
):
    return await ExportService(session).create(request)


@router.get("/{id}/download")
async def download_export(id: int, session: AsyncSession = Depends(get_session)):
    path = await ExportService(session).path(id)
    return FileResponse(path, media_type="text/markdown", filename=path.name)
