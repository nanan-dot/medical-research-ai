"""旧 JSON AgentRun 的只读兼容边界。

旧记录可以继续展示和恢复判断，但不得被解释为结构化正式产物、确认或审计事件。
"""

from dataclasses import dataclass
from typing import Any

from app.agents.enums import RunStatus
from app.agents.model import AgentRunRecord


@dataclass(frozen=True)
class LegacyRunSnapshot:
    run_id: str
    status: str
    state: dict[str, Any]
    events: tuple[dict[str, Any], ...]
    retrieval_trace: dict[str, Any] | None
    formal_artifacts_available: bool = False


class LegacyRunAdapter:
    """将旧行限制为只读视图，避免新流程误用 JSON 作为正式交接。"""

    def read(self, record: AgentRunRecord) -> LegacyRunSnapshot:
        if not record.is_legacy:
            raise ValueError("structured runs must use the M0 runtime service")
        try:
            status = RunStatus(record.workflow_status).value
        except ValueError:
            status = RunStatus.FAILED.value
        return LegacyRunSnapshot(
            run_id=record.run_id,
            status=status,
            state=dict(record.state_json or {}),
            events=tuple(dict(item) for item in (record.events_json or [])),
            retrieval_trace=dict(record.retrieval_trace_json)
            if record.retrieval_trace_json
            else None,
        )
