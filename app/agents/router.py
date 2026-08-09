"""Agent 任务路由 HTTP 接口：仅做分类，不执行任何工具。"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.agents.classifier import AgentTaskClassifier
from app.agents.run_service import AgentRunService
from app.agents.schemas import (
    AgentApprovalRequest,
    AgentRoutingDecision,
    AgentRunRequest,
    AgentRunResponse,
    AgentTaskRequest,
    TaskDecision,
)

router = APIRouter(prefix="/agent", tags=["Agent 任务路由"])
# 进程内单例：仅支持单 worker 部署（uvicorn --workers>1 时跨实例无法恢复
# 审批中的运行）。真实多用户部署需换持久化 checkpointer 与运行存储。
run_service = AgentRunService()


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


@router.post("/runs", response_model=AgentRunResponse)
async def start_agent_run(payload: AgentRunRequest) -> AgentRunResponse:
    """启动只会等待人工确认的受限运行，不执行真实工具。"""

    run_id, state = run_service.start(
        {
            "user_query": payload.query,
            "task_type": payload.task_type,
            "evidence": payload.evidence,
            "pending_confirmations": payload.confirmations,
        }
    )
    return AgentRunResponse(run_id=run_id, workflow_status=state["workflow_status"])


@router.post("/runs/{run_id}/approve", response_model=AgentRunResponse)
async def approve_agent_run(
    run_id: str, payload: AgentApprovalRequest
) -> AgentRunResponse:
    """以同一检查点恢复已暂停运行；拒绝不会继续执行。"""

    try:
        state = run_service.resume(run_id, payload.decision)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return AgentRunResponse(
        run_id=run_id,
        workflow_status=state["workflow_status"],
        decision=state.get("decision"),
    )


@router.post("/runs/{run_id}/cancel", response_model=AgentRunResponse)
async def cancel_agent_run(run_id: str) -> AgentRunResponse:
    """取消已暂停运行；取消后不再进入任何工具节点。"""

    try:
        state = run_service.resume(run_id, "cancel")
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return AgentRunResponse(
        run_id=run_id,
        workflow_status=state["workflow_status"],
        decision=state.get("decision"),
    )


@router.get("/runs/{run_id}/trace")
async def get_agent_trace(run_id: str) -> list[dict[str, object]]:
    """返回本地脱敏轨迹，供用户和开发者定位失败步骤。"""
    try:
        return [event.to_dict() for event in run_service.get_trace(run_id)]
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error


@router.post("/runs/{run_id}/export-trace", response_class=PlainTextResponse)
async def export_agent_trace(run_id: str) -> str:
    """导出本地脱敏 Markdown 调试报告。"""
    try:
        events = run_service.get_trace(run_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    lines = [f"# Agent Trace: {run_id}", "", "| 节点 | 状态 | 耗时(ms) | 错误 |", "| --- | --- | ---: | --- |"]
    lines.extend(
        f"| {event.node} | {event.status} | {event.duration_ms} | {event.error or ''} |"
        for event in events
    )
    return "\n".join(lines)
