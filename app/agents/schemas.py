"""Agent 任务分类的路由契约：任务类型枚举与分类决策对象。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AgentTaskType(str, Enum):
    """支持的科研任务类型；值保持小写下划线以便 API 输出。"""

    SINGLE_PAPER_QA = "single_paper_qa"
    NOTE_QA = "note_qa"
    EXTERNAL_SEARCH = "external_search"
    MULTI_PAPER_COMPARISON = "multi_paper_comparison"
    CANDIDATE_DIRECTION = "candidate_direction"
    WRITING_OUTLINE = "writing_outline"
    COMPLEX_RESEARCH = "complex_research"
    CLARIFICATION = "clarification"


@dataclass(frozen=True)
class TaskDecision:
    """一次分类的确定性结果：任务类型、是否启用 Agent、所需工具与澄清标志。"""

    task_type: AgentTaskType
    use_agent: bool = False
    required_tools: list[str] = field(default_factory=list)
    clarification_needed: bool = False
    reason: str = ""
    confidence: float = 0.0


class AgentTaskRequest(BaseModel):
    """任务分类请求；端点不会执行工具。"""

    query: str = Field(min_length=2, max_length=2_000)


class AgentRoutingDecision(BaseModel):
    """对用户公开的分类与路由计划。"""

    task_type: AgentTaskType
    confidence: float = Field(ge=0.0, le=1.0)
    required_tools: list[str]
    use_agent: bool
    clarification_needed: bool
    reason: str


class AgentRunRequest(BaseModel):
    model_config = {"extra": "forbid"}
    query: str = Field(min_length=2, max_length=2_000)
    task_type: Literal[
        "evidence_qa", "literature_search", "research_direction", "writing"
    ] = "evidence_qa"
    publish_requested: bool = False


class AgentRunResponse(BaseModel):
    run_id: str
    workflow_status: str
    decision: str | None = None
    approval_payload: dict[str, object] | None = None


class AgentApprovalRequest(BaseModel):
    decision: Literal["approve", "reject"]
