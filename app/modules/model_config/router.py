"""model_config — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.model_config.service import ModelConfigService

router = APIRouter(prefix="/model-config", tags=["模型配置"])


@router.get("")
async def list_model_config(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = ModelConfigService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_model_config(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ModelConfigService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_model_config(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ModelConfigService(session)
    await service.delete(id)
