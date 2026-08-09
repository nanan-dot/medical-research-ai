"""进程内 Agent 运行与审批恢复服务。"""

from typing import cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from app.agents.graph import build_agent_graph
from app.agents.state import AgentGraphState
from app.agents.trace import TraceEvent, create_event


class AgentRunService:
    """使用同一图实例和 thread_id 管理暂停中的审批运行。"""

    # 进程内跟踪上限：防止常驻服务下 _known_runs/_traces 无界增长。
    # 超过上限时按创建顺序淘汰最旧运行（FIFO）。真实多用户部署应改用持久化存储。
    MAX_TRACKED_RUNS = 1000

    def __init__(self) -> None:
        self._graph = build_agent_graph()
        self._known_runs: set[str] = set()
        self._run_order: list[str] = []
        self._traces: dict[str, list[TraceEvent]] = {}

    def _track(self, run_id: str) -> None:
        self._known_runs.add(run_id)
        self._run_order.append(run_id)
        # 超过上限时淘汰最旧运行的本地追踪（known_runs + traces）。
        # 注：langgraph MemorySaver 检查点无法按 thread 删除，但其按线程
        # 键控存储不会随本类追踪增长；真实多用户部署应换持久化 checkpointer。
        while len(self._run_order) > self.MAX_TRACKED_RUNS:
            oldest = self._run_order.pop(0)
            self._known_runs.discard(oldest)
            self._traces.pop(oldest, None)

    def start(self, state: AgentGraphState) -> tuple[str, AgentGraphState]:
        """启动一次受限运行并返回运行标识与当前状态。"""

        run_id = str(uuid4())
        self._track(run_id)
        result = self._graph.invoke(state, config=self._config(run_id))
        self._traces[run_id] = [create_event(run_id, "graph_start", state, result)]
        return run_id, cast(AgentGraphState, result)

    def resume(self, run_id: str, decision: str) -> AgentGraphState:
        """以同一 thread_id 恢复已暂停的运行。"""

        if run_id not in self._known_runs:
            raise KeyError(run_id)
        snapshot = self._graph.get_state(self._config(run_id))
        if snapshot.values.get("workflow_status") != "awaiting_confirmation":
            raise ValueError("agent run is not awaiting confirmation")
        result = self._graph.invoke(
            Command(resume={"decision": decision}), config=self._config(run_id)
        )
        self._traces[run_id].append(create_event(run_id, "human_approval", decision, result))
        return cast(AgentGraphState, result)

    def get_trace(self, run_id: str) -> list[TraceEvent]:
        """读取某次已知运行的本地脱敏轨迹。"""
        if run_id not in self._known_runs:
            raise KeyError(run_id)
        return list(self._traces[run_id])

    @staticmethod
    def _config(run_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": run_id}}
