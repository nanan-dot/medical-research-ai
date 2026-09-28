"""Agent 运行仓库；同步边界避免 LangGraph MemorySaver 参与恢复。"""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.agents.model import AgentRunRecord


class AgentRunRepository:
    """以原子替换保存运行快照和审计事件。"""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, record: AgentRunRecord) -> None:
        with Session(self._engine) as session:
            session.merge(record)
            session.commit()

    def get(self, run_id: str) -> AgentRunRecord | None:
        with Session(self._engine) as session:
            return session.scalar(
                select(AgentRunRecord).where(AgentRunRecord.run_id == run_id)
            )
