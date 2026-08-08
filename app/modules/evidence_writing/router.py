"""证据驱动写作路由，不直接访问数据库。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.evidence_writing.schema import DraftRequest, OutlineRequest, PolishRequest
from app.modules.evidence_writing.service import EvidenceWritingService
from app.modules.writing_project.schema import WritingProjectRead

router = APIRouter(prefix="/writing-projects", tags=["evidence-writing"])


@router.post("/{project_id}/outline", response_model=WritingProjectRead)
async def submit_outline(
    project_id: int, payload: OutlineRequest, session: AsyncSession = Depends(get_session)
) -> WritingProjectRead:
    return await EvidenceWritingService(session).submit_outline(project_id, payload)


@router.post("/{project_id}/draft", response_model=WritingProjectRead)
async def generate_draft(
    project_id: int, payload: DraftRequest, session: AsyncSession = Depends(get_session)
) -> WritingProjectRead:
    return await EvidenceWritingService(session).generate_draft(project_id, payload)


@router.patch("/{project_id}/draft", response_model=WritingProjectRead)
async def edit_draft(
    project_id: int, payload: DraftRequest, session: AsyncSession = Depends(get_session)
) -> WritingProjectRead:
    return await EvidenceWritingService(session).edit_draft(project_id, payload)


@router.post("/{project_id}/polish", response_model=WritingProjectRead)
async def polish(
    project_id: int, payload: PolishRequest, session: AsyncSession = Depends(get_session)
) -> WritingProjectRead:
    return await EvidenceWritingService(session).polish(project_id, payload)
