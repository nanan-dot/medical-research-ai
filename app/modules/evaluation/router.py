"""Evaluation run HTTP endpoints; execution is deliberately out of request scope."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.core.database import get_session
from app.modules.evaluation.model import EvaluationRunRecord, EvaluationRunResult
from app.modules.evaluation.schema import (
    EvaluationCreate,
    EvaluationResultCreate,
    EvaluationResultRead,
    EvaluationRunRead,
)

router = APIRouter(prefix="/evaluations", tags=["evaluation"])

@router.post("", response_model=EvaluationRunRead, status_code=status.HTTP_201_CREATED)
async def create_evaluation(payload: EvaluationCreate, session: AsyncSession = Depends(get_session)) -> EvaluationRunRead:
    entity = EvaluationRunRecord(dataset_version=payload.dataset_version, config_json=json.dumps(payload.model_dump(exclude={"dataset_version"}, by_alias=True), ensure_ascii=False), status="pending")
    session.add(entity); await session.flush(); await session.refresh(entity)
    return EvaluationRunRead.model_validate(entity)

@router.get("/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation(run_id: int, session: AsyncSession = Depends(get_session)) -> EvaluationRunRead:
    entity = await session.get(EvaluationRunRecord, run_id)
    if entity is None: raise NotFoundError("Evaluation run not found")
    return EvaluationRunRead.model_validate(entity)

@router.get("/{run_id}/results", response_model=list[EvaluationResultRead])
async def get_results(run_id: int, session: AsyncSession = Depends(get_session)) -> list[EvaluationResultRead]:
    if await session.get(EvaluationRunRecord, run_id) is None: raise NotFoundError("Evaluation run not found")
    rows = await session.execute(select(EvaluationRunResult).where(EvaluationRunResult.run_id == run_id).order_by(EvaluationRunResult.id))
    return [EvaluationResultRead.model_validate(item) for item in rows.scalars()]

@router.post("/{run_id}/results", response_model=EvaluationResultRead, status_code=status.HTTP_201_CREATED)
async def append_result(run_id: int, payload: EvaluationResultCreate, session: AsyncSession = Depends(get_session)) -> EvaluationResultRead:
    """Internal runner write boundary; callers must supply raw execution output, never metrics."""
    run = await session.get(EvaluationRunRecord, run_id)
    if run is None:
        raise NotFoundError("Evaluation run not found")
    # 已完成/已取消的 run 不再接受结果追加，防止事后篡改评测记录。
    if run.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Evaluation run is already finished")
    # 同一 run 内 question_id 唯一，防止重复注入结果。
    existing = await session.execute(
        select(EvaluationRunResult).where(
            EvaluationRunResult.run_id == run_id,
            EvaluationRunResult.question_id == payload.question_id,
        )
    )
    if existing.scalars().first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question result already recorded")
    entity = EvaluationRunResult(run_id=run_id, **payload.model_dump())
    session.add(entity); await session.flush(); await session.refresh(entity)
    return EvaluationResultRead.model_validate(entity)
