"""Agent 工作流的检查点构造函数。"""

from langgraph.checkpoint.memory import MemorySaver


def create_memory_checkpointer() -> MemorySaver:
    """创建进程内检查点存储，供调用方按 thread_id 恢复状态快照。"""

    return MemorySaver()
