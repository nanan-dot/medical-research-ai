"""受限的单 Agent LangGraph 工作流，不执行真实医学结论或外部调用。"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from app.agents.checkpointer import create_memory_checkpointer
from app.agents.state import AgentGraphState

TASK_LOCAL_SEARCH = "evidence_qa"
TASK_EXTERNAL_SEARCH = "literature_search"
TASK_DIRECTION = "research_direction"
TASK_WRITING = "writing"
MAX_STEPS_ERROR = "maximum_workflow_steps_reached"
EVIDENCE_ERROR = "evidence_not_available_after_search"


def _default_state_fields(state: AgentGraphState) -> dict[str, object]:
    """补齐可恢复状态的集合字段，避免分支间出现不稳定的状态形状。"""

    defaults: dict[str, object] = {
        "selected_documents": [],
        "evidence": [],
        "search_history": [],
        "candidate_directions": [],
        "draft": None,
        "citations": [],
        "pending_confirmations": [],
        "errors": [],
        "step_count": 0,
        "max_steps": 12,
        "needs_external_search": False,
        "workflow_status": "pending",
        "tool_calls": 0,
        "max_tool_calls": 8,
        "resource_units": 0,
        "max_resource_units": 100,
        "decision": None,
        "approval_payload": {},
    }
    return {key: value for key, value in defaults.items() if key not in state}


def _advance_state(state: AgentGraphState) -> dict[str, object]:
    """统一限制节点次数，避免意外条件边形成无限循环。"""

    next_step_count = state.get("step_count", 0) + 1
    if next_step_count > state.get("max_steps", 12):
        return {
            "step_count": next_step_count,
            "errors": [*state.get("errors", []), MAX_STEPS_ERROR],
        }
    return {"step_count": next_step_count}


def _append_history(state: AgentGraphState, event: str) -> dict[str, object]:
    return {"search_history": [*state.get("search_history", []), event]}


def classify_task(state: AgentGraphState) -> dict[str, object]:
    """采用已声明任务类型；未声明时保守地归入本地证据问答。"""

    updates = _advance_state(state)
    if state.get("step_count", 0) >= state.get("max_steps", 12):
        return updates
    return {
        **_default_state_fields(state),
        **updates,
        "task_type": state.get("task_type", TASK_LOCAL_SEARCH),
    }


def plan_task(state: AgentGraphState) -> dict[str, object]:
    """记录计划节点完成；不从自由文本推断医学任务或结论。"""

    updates = _advance_state(state)
    if state.get("step_count", 0) >= state.get("max_steps", 12):
        return updates
    return {**updates, **_append_history(state, "plan_completed")}


def local_search(state: AgentGraphState) -> dict[str, object]:
    """记录本地检索意图，实际检索由后续服务适配器注入。"""

    updates = _advance_state(state)
    if state.get("step_count", 0) >= state.get("max_steps", 12):
        return updates
    return {**updates, **_append_history(state, "local_search_completed")}


def pubmed_search(state: AgentGraphState) -> dict[str, object]:
    """记录外部检索步骤，不在基础图中发出网络请求。"""

    updates = _advance_state(state)
    if state.get("step_count", 0) >= state.get("max_steps", 12):
        return updates
    return {**updates, **_append_history(state, "pubmed_search_completed")}


def evidence_check(state: AgentGraphState) -> dict[str, object]:
    """仅检查调用方提供的证据是否存在，不生成或篡改证据内容。"""

    return _advance_state(state)


def direction_analysis(state: AgentGraphState) -> dict[str, object]:
    """完成方向分析步骤；候选方向必须由受控服务提供。"""

    return _advance_state(state)


def writing(state: AgentGraphState) -> dict[str, object]:
    """完成写作步骤；基础图不自行生成草稿。"""

    return _advance_state(state)


def citation_check(state: AgentGraphState) -> dict[str, object]:
    """完成引用检查步骤；具体核验由已注册工具承担。"""

    return _advance_state(state)


def human_confirmation(state: AgentGraphState) -> Command:
    """暂停等待 JSON 审批；节点在恢复时无副作用地重新执行。"""

    payload = {
        "required_confirmations": state.get("pending_confirmations", []),
        "action": "approve_or_reject",
    }
    response = interrupt(payload)
    decision = response.get("decision") if isinstance(response, dict) else None
    if decision == "approve":
        return Command(
            update={
                "decision": "approved",
                "approval_payload": payload,
                "pending_confirmations": [],
                "workflow_status": "running",
            },
            goto="citation_check",
        )
    if decision in {"reject", "cancel"}:
        return Command(
            update={"decision": "cancelled", "approval_payload": payload},
            goto="cancelled",
        )
    return Command(
        update={"errors": [*state.get("errors", []), "invalid_approval_decision"]},
        goto="error",
    )


def prepare_confirmation(state: AgentGraphState) -> dict[str, object]:
    """在中断前持久化等待状态，供调用方安全展示审批界面。"""

    return {**_advance_state(state), "workflow_status": "awaiting_confirmation"}


def cancelled(state: AgentGraphState) -> dict[str, object]:
    """终止被用户拒绝或取消的任务，绝不继续执行工具。"""

    return {**_advance_state(state), "workflow_status": "cancelled"}


def workflow_error(state: AgentGraphState) -> dict[str, object]:
    """终止错误工作流，保留已收集错误供调用方展示。"""

    errors = state.get("errors") or [EVIDENCE_ERROR]
    return {
        **_advance_state(state),
        "errors": errors,
        "workflow_status": "failed",
    }


def complete(state: AgentGraphState) -> dict[str, object]:
    """终止成功工作流，不代表医学内容已通过人工审查。"""

    return {**_advance_state(state), "workflow_status": "completed"}


def _route_after_plan(state: AgentGraphState) -> str:
    if state.get("errors"):
        return "error"
    routes = {
        TASK_EXTERNAL_SEARCH: "pubmed_search",
        TASK_DIRECTION: "direction_analysis",
        TASK_WRITING: "writing",
    }
    task_type = state.get("task_type") or TASK_LOCAL_SEARCH
    return routes.get(task_type, "local_search")


def _route_after_evidence_check(state: AgentGraphState) -> str:
    if state.get("errors"):
        return "error"
    if state.get("pending_confirmations"):
        return "prepare_confirmation"
    if state.get("evidence"):
        return "citation_check"
    has_completed_external_search = "pubmed_search_completed" in state.get(
        "search_history", []
    )
    if state.get("needs_external_search") and not has_completed_external_search:
        return "pubmed_search"
    return "error"


def _route_after_local_search(state: AgentGraphState) -> str:
    return "error" if state.get("errors") else "evidence_check"


def _route_after_pubmed_search(state: AgentGraphState) -> str:
    return "error" if state.get("errors") else "evidence_check"


def _route_after_direct_task(state: AgentGraphState) -> str:
    if state.get("errors"):
        return "error"
    if state.get("pending_confirmations"):
        return "prepare_confirmation"
    return "citation_check"


def _route_after_citation_check(state: AgentGraphState) -> str:
    if state.get("errors"):
        return "error"
    return "complete"


def build_agent_graph() -> CompiledStateGraph[
    AgentGraphState, None, AgentGraphState, AgentGraphState
]:
    """构建带内存检查点的受限 Agent 图，供内部服务调用。"""

    graph = StateGraph(AgentGraphState)
    graph.add_node("classify_task", classify_task)
    graph.add_node("plan_task", plan_task)
    graph.add_node("local_search", local_search)
    graph.add_node("pubmed_search", pubmed_search)
    graph.add_node("evidence_check", evidence_check)
    graph.add_node("direction_analysis", direction_analysis)
    graph.add_node("writing", writing)
    graph.add_node("citation_check", citation_check)
    graph.add_node("human_confirmation", human_confirmation)
    graph.add_node("prepare_confirmation", prepare_confirmation)
    graph.add_node("cancelled", cancelled)
    graph.add_node("error", workflow_error)
    graph.add_node("complete", complete)
    graph.add_edge(START, "classify_task")
    graph.add_edge("classify_task", "plan_task")
    graph.add_conditional_edges("plan_task", _route_after_plan)
    graph.add_conditional_edges("local_search", _route_after_local_search)
    graph.add_conditional_edges("pubmed_search", _route_after_pubmed_search)
    graph.add_conditional_edges("evidence_check", _route_after_evidence_check)
    graph.add_conditional_edges("direction_analysis", _route_after_direct_task)
    graph.add_conditional_edges("writing", _route_after_direct_task)
    graph.add_conditional_edges("citation_check", _route_after_citation_check)
    graph.add_edge("human_confirmation", END)
    graph.add_edge("prepare_confirmation", "human_confirmation")
    graph.add_edge("cancelled", END)
    graph.add_edge("error", END)
    graph.add_edge("complete", END)
    return graph.compile(checkpointer=create_memory_checkpointer())
