"""写作项目 HTTP 接口。"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.writing_project.schema import (
    UserMaterialCreate,
    UserMaterialRead,
    WritingEvidenceReferenceCreate,
    WritingEvidenceReferenceRead,
    WritingProjectCreate,
    WritingProjectRead,
    WritingProjectUpdate,
    WritingVersionRead,
)
from app.modules.writing_project.service import WritingProjectService

router = APIRouter(prefix="/writing-projects", tags=["写作项目"])


@router.post("", response_model=WritingProjectRead)
async def create(
    payload: WritingProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> WritingProjectRead:
    return await WritingProjectService(session).create(payload)


@router.get("", response_model=list[WritingProjectRead])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[WritingProjectRead]:
    return await WritingProjectService(session).list_projects()


@router.get("/{project_id}", response_model=WritingProjectRead)
async def get(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> WritingProjectRead:
    return await WritingProjectService(session).get(project_id)


@router.patch("/{project_id}", response_model=WritingProjectRead)
async def update(
    project_id: int,
    payload: WritingProjectUpdate,
    session: AsyncSession = Depends(get_session),
) -> WritingProjectRead:
    return await WritingProjectService(session).update(project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    await WritingProjectService(session).delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/materials", response_model=UserMaterialRead)
async def add_material(
    project_id: int,
    payload: UserMaterialCreate,
    session: AsyncSession = Depends(get_session),
) -> UserMaterialRead:
    return await WritingProjectService(session).add_material(project_id, payload)


@router.post("/{project_id}/evidence-references", response_model=WritingEvidenceReferenceRead)
async def add_evidence_reference(
    project_id: int,
    payload: WritingEvidenceReferenceCreate,
    session: AsyncSession = Depends(get_session),
) -> WritingEvidenceReferenceRead:
    return await WritingProjectService(session).add_evidence_reference(project_id, payload)


@router.post("/{project_id}/versions", response_model=WritingVersionRead)
async def save_version(
    project_id: int,
    expected_version: int,
    session: AsyncSession = Depends(get_session),
) -> WritingVersionRead:
    return await WritingProjectService(session).save_version(
        project_id,
        expected_version=expected_version,
    )


@router.get("/{project_id}/versions", response_model=list[WritingVersionRead])
async def list_versions(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[WritingVersionRead]:
    return await WritingProjectService(session).list_versions(project_id)


@router.post(
    "/{project_id}/versions/{version}/restore",
    response_model=WritingProjectRead,
)
async def restore_version(
    project_id: int,
    version: int,
    expected_version: int,
    session: AsyncSession = Depends(get_session),
) -> WritingProjectRead:
    return await WritingProjectService(session).restore_version(
        project_id,
        version,
        expected_version=expected_version,
    )
