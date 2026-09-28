"""LangGraph 可持久化 Agent 状态契约。"""

import json
from dataclasses import asdict, dataclass, field
from typing import Literal, TypedDict, cast

TaskType = Literal[
    "evidence_qa",
    "literature_search",
    "research_direction",
    "writing",
]


class AgentGraphState(TypedDict, total=False):
    """在 LangGraph 节点间传递的 JSON 原生状态。"""

    user_query: str
    task_type: TaskType
    selected_documents: list[int]
    evidence: list[dict[str, object]]
    grounded_answer: dict[str, object] | None
    retrieval_trace: dict[str, object] | None
    publish_requested: bool
    search_history: list[str]
    candidate_directions: list[str]
    draft: str | None
    citations: list[dict[str, object]]
    pending_confirmations: list[str]
    errors: list[str]
    step_count: int
    max_steps: int
    needs_external_search: bool
    workflow_status: str
    tool_calls: int
    max_tool_calls: int
    resource_units: int
    max_resource_units: int
    decision: str | None
    approval_payload: dict[str, object]
    execution: dict[str, object]


@dataclass
class AgentState:
    """应用层 Agent 状态；仅保存可 JSON 序列化的值以支持恢复。"""

    user_query: str
    task_type: TaskType | None = None
    selected_documents: list[int] = field(default_factory=list)
    evidence: list[dict[str, object]] = field(default_factory=list)
    grounded_answer: dict[str, object] | None = None
    retrieval_trace: dict[str, object] | None = None
    publish_requested: bool = False
    search_history: list[str] = field(default_factory=list)
    candidate_directions: list[str] = field(default_factory=list)
    draft: str | None = None
    citations: list[dict[str, object]] = field(default_factory=list)
    pending_confirmations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    step_count: int = 0
    max_steps: int = 12
    needs_external_search: bool = False
    workflow_status: str = "pending"
    tool_calls: int = 0
    max_tool_calls: int = 8
    resource_units: int = 0
    max_resource_units: int = 100
    decision: str | None = None
    approval_payload: dict[str, object] = field(default_factory=dict)

    def advance(self) -> bool:
        """推进一次工作流，并返回是否仍在允许的最大步数内。"""

        self.step_count += 1
        return self.step_count <= self.max_steps

    def to_graph_state(self) -> AgentGraphState:
        """转换为 LangGraph 可检查点保存的原生状态。"""

        return cast(AgentGraphState, asdict(self))

    def serialize(self) -> str:
        """序列化状态；不可序列化的调用方数据会显式抛出 TypeError。"""

        return json.dumps(self.to_graph_state(), ensure_ascii=False)

    @classmethod
    def restore(cls, payload: str) -> "AgentState":
        """从先前保存的 JSON 状态恢复 AgentState。"""

        return cls(**json.loads(payload))
