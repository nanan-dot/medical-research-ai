"""Agent 任务路由 HTTP 接口：仅做分类，不执行任何工具。"""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import create_engine

from app.agents.classifier import AgentTaskClassifier
from app.agents.repository import AgentRunRepository
from app.agents.run_service import AgentRunService
from app.agents.schemas import (
    AgentApprovalRequest,
    AgentRoutingDecision,
    AgentRunRequest,
    AgentRunResponse,
    AgentTaskRequest,
    TaskDecision,
)
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["Agent 任务路由"])


@lru_cache(maxsize=1)
def get_run_service() -> AgentRunService:
    """提供旧 API 兼容服务；数据库结构只由 Alembic 创建。"""
    database_path = Path(settings.DATA_DIR) / "app.db"
    engine = create_engine(f"sqlite:///{database_path}")
    return AgentRunService(repository=AgentRunRepository(engine))


@router.post("/tasks", response_model=AgentRoutingDecision)
async def classify_task(payload: AgentTaskRequest) -> AgentRoutingDecision:
    """对用户查询做确定性分类；只路由，不运行工具。"""
    decision: TaskDecision = AgentTaskClassifier().classify(payload.query)
    return AgentRoutingDecision(
        task_type=decision.task_type,
        confidence=decision.confidence,
        use_agent=decision.use_agent,
        required_tools=decision.required_tools,
        clarification_needed=decision.clarification_needed,
        reason=decision.reason,
    )


@router.post(
    "/runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED
)
async def start_agent_run(
    payload: AgentRunRequest,
) -> AgentRunResponse:
    """Legacy JSON Run writes are retired; use /agent-runtime/runs."""
    del payload
    raise HTTPException(status_code=410, detail="legacy_agent_run_writes_retired")


@router.post("/runs/{run_id}/approve", response_model=AgentRunResponse)
async def approve_agent_run(
    run_id: str,
    payload: AgentApprovalRequest,
) -> AgentRunResponse:
    """Legacy JSON Run writes are retired; use structured confirmations."""
    del run_id, payload
    raise HTTPException(status_code=410, detail="legacy_agent_run_writes_retired")


@router.post("/runs/{run_id}/cancel", response_model=AgentRunResponse)
async def cancel_agent_run(
    run_id: str,
) -> AgentRunResponse:
    """Legacy JSON Run writes are retired; use structured cancellation."""
    del run_id
    raise HTTPException(status_code=410, detail="legacy_agent_run_writes_retired")


@router.get("/runs/{run_id}/trace")
async def get_agent_trace(
    run_id: str, service: AgentRunService = Depends(get_run_service)
) -> list[dict[str, object]]:
    """返回本地脱敏轨迹，供用户和开发者定位失败步骤。"""
    try:
        return [event.to_dict() for event in service.get_trace(run_id)]
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error


@router.post("/runs/{run_id}/export-trace", response_class=PlainTextResponse)
async def export_agent_trace(
    run_id: str, service: AgentRunService = Depends(get_run_service)
) -> str:
    """导出本地脱敏 Markdown 调试报告。"""
    try:
        events = service.get_trace(run_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    lines = [
        f"# Agent Trace: {run_id}",
        "",
        "| 节点 | 状态 | 耗时(ms) | 错误 |",
        "| --- | --- | ---: | --- |",
    ]
    lines.extend(
        f"| {event.node} | {event.status} | {event.duration_ms} | {event.error or ''} |"
        for event in events
    )
    return "\n".join(lines)


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: str, service: AgentRunService = Depends(get_run_service)
) -> AgentRunResponse:
    """读取可恢复运行的公开状态。"""
    try:
        state = service.get(run_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    return AgentRunResponse(
        run_id=run_id,
        workflow_status=str(state["workflow_status"]),
        decision=state.get("decision"),
        approval_payload=state.get("approval_payload"),
    )
