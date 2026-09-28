"""受控 Agent 证据适配器；默认不接入模型或外部服务。"""

from dataclasses import dataclass
from typing import Protocol

from app.agents.state import AgentGraphState
from app.rag.schemas import EvidenceSet, GroundedAnswer, RetrievalTrace


@dataclass(frozen=True)
class AgentEvidenceResult:
    """一次工具边界返回的证据、答案草案和可回放检索轨迹。"""

    evidence: EvidenceSet
    answer: GroundedAnswer
    trace: RetrievalTrace


class AgentEvidenceAdapter(Protocol):
    """真实 RAG 编排器的可注入边界，测试可使用确定性替身。"""

    def execute(self, state: AgentGraphState) -> AgentEvidenceResult: ...
