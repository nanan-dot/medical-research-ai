from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.model_config.schema import (
    ConnectionTestRequest,
    ConnectionTestResult,
    ModelConfigCreate,
    ModelConfigRead,
)
from app.modules.model_config.service import ModelConfigService

router = APIRouter(prefix="/model-configs", tags=["模型配置"])


@router.get("", response_model=list[ModelConfigRead])
async def list_configs(session: AsyncSession = Depends(get_session)):
    return await ModelConfigService(session).list()


@router.post("", response_model=ModelConfigRead)
async def create_config(
    request: ModelConfigCreate, session: AsyncSession = Depends(get_session)
):
    return await ModelConfigService(session).create(request)


@router.post("/{id}/test", response_model=ConnectionTestResult)
async def test_config(
    id: int,
    request: ConnectionTestRequest,
    session: AsyncSession = Depends(get_session),
):
    return await ModelConfigService(session).test(id, request.acknowledge_possible_cost)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(id: int, session: AsyncSession = Depends(get_session)):
    await ModelConfigService(session).delete(id)
    return Response(status_code=204)
