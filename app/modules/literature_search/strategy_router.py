"""HTTP boundary for persisted search strategies."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.schema import LiteratureSearchTaskCreateResult
from app.modules.literature_search.strategy_schema import (
    StrategyCompareRead,
    StrategyCountRead,
    StrategyCreate,
    StrategyMeshPatch,
    StrategyMeshRead,
    StrategyPatch,
    StrategyRead,
    StrategyRemapRead,
    StrategyTermCreate,
    StrategyTermPatch,
    StrategyTermRead,
    StrategyValidationRead,
    StrategyVersionRead,
)
from app.modules.literature_search.strategy_service import (
    SearchStrategyService,
    version_read,
)

router = APIRouter(prefix="/literature-search/strategies", tags=["Search strategies"])


@router.post("", response_model=StrategyRead, status_code=201)
async def create_strategy(request: StrategyCreate, session: AsyncSession = Depends(get_session)) -> StrategyRead:
    return await SearchStrategyService(session).create(request)


@router.get("/latest-complete", response_model=StrategyRead)
async def get_latest_complete_strategy(session: AsyncSession = Depends(get_session)) -> StrategyRead:
    return await SearchStrategyService(session).latest_complete()


@router.get("/{strategy_id}", response_model=StrategyRead)
async def get_strategy(strategy_id: int, session: AsyncSession = Depends(get_session)) -> StrategyRead:
    return await SearchStrategyService(session).get(strategy_id)


@router.patch("/{strategy_id}", response_model=StrategyRead)
async def patch_strategy(strategy_id: int, request: StrategyPatch, session: AsyncSession = Depends(get_session)) -> StrategyRead:
    return await SearchStrategyService(session).patch(strategy_id, request)


@router.post("/{strategy_id}/terms", response_model=StrategyTermRead, status_code=201)
async def add_term(strategy_id: int, request: StrategyTermCreate, session: AsyncSession = Depends(get_session)) -> StrategyTermRead:
    return await SearchStrategyService(session).add_term(strategy_id, request)


@router.post("/{strategy_id}/terms/remap", response_model=StrategyRemapRead)
async def remap_terms(strategy_id: int, session: AsyncSession = Depends(get_session)) -> StrategyRemapRead:
    # 静态 remap 必须在动态 term_id 之前注册，否则 FastAPI 会把它当作整数解析。
    return StrategyRemapRead(**(await SearchStrategyService(session).remap_terms(strategy_id)))


@router.patch("/{strategy_id}/terms/{term_id}", response_model=StrategyTermRead)
async def patch_term(strategy_id: int, term_id: int, request: StrategyTermPatch, session: AsyncSession = Depends(get_session)) -> StrategyTermRead:
    return await SearchStrategyService(session).patch_term(strategy_id, term_id, request)


@router.delete("/{strategy_id}/terms/{term_id}", status_code=204)
async def delete_term(strategy_id: int, term_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    await SearchStrategyService(session).delete_term(strategy_id, term_id)
    return Response(status_code=204)


@router.post("/{strategy_id}/mesh/refresh", response_model=StrategyRead)
async def refresh_mesh(strategy_id: int, session: AsyncSession = Depends(get_session)) -> StrategyRead:
    return await SearchStrategyService(session).refresh_mesh(strategy_id)


@router.patch("/{strategy_id}/mesh/{mesh_term_id}", response_model=StrategyMeshRead)
async def patch_mesh(
    strategy_id: int,
    mesh_term_id: int,
    request: StrategyMeshPatch,
    session: AsyncSession = Depends(get_session),
) -> StrategyMeshRead:
    return await SearchStrategyService(session).patch_mesh(
        strategy_id,
        mesh_term_id,
        request,
    )


@router.post("/{strategy_id}/validate", response_model=StrategyValidationRead)
async def validate_strategy(strategy_id: int, session: AsyncSession = Depends(get_session)) -> StrategyValidationRead:
    return StrategyValidationRead(**(await SearchStrategyService(session).validate(strategy_id)))


@router.post("/{strategy_id}/count", response_model=StrategyCountRead)
async def count_strategy(strategy_id: int, fingerprint: str, session: AsyncSession = Depends(get_session)) -> StrategyCountRead:
    return StrategyCountRead(**(await SearchStrategyService(session).count(strategy_id, fingerprint)))


@router.post("/{strategy_id}/versions", response_model=StrategyVersionRead)
async def create_version(strategy_id: int, response: Response, session: AsyncSession = Depends(get_session)) -> StrategyVersionRead:
    service = SearchStrategyService(session)
    versions = await service.list_versions(strategy_id)
    version = await service.create_version(strategy_id)
    if not versions or versions[0].id != version.id:
        response.status_code = 201
    return version_read(version)


@router.get("/{strategy_id}/versions", response_model=list[StrategyVersionRead])
async def list_versions(strategy_id: int, session: AsyncSession = Depends(get_session)) -> list[StrategyVersionRead]:
    return [version_read(version) for version in await SearchStrategyService(session).list_versions(strategy_id)]


@router.get("/{strategy_id}/compare", response_model=StrategyCompareRead)
async def compare_versions(strategy_id: int, from_version: int, to_version: int, session: AsyncSession = Depends(get_session)) -> StrategyCompareRead:
    return StrategyCompareRead(**(await SearchStrategyService(session).compare_versions(strategy_id, from_version, to_version)))


@router.post("/{strategy_id}/execute", response_model=LiteratureSearchTaskCreateResult)
async def execute_strategy(strategy_id: int, session: AsyncSession = Depends(get_session)) -> LiteratureSearchTaskCreateResult:
    return await SearchStrategyService(session).execute(strategy_id)
