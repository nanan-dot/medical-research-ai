# R4-WP12 LangGraph Agent 工作流

## 范围

该图是受限的单 Agent 编排基础设施。它只编排调用方已提供的状态和后续可注入的服务，不发起真实 PubMed 请求、不调用模型，也不生成医学结论、证据或论文草稿。

## 状态与检查点

- `AgentState` 仅包含 JSON 原生值，可用 `serialize()` / `restore()` 保存和恢复。
- `AgentGraphState` 是 LangGraph 节点使用的 TypedDict 契约。
- `build_agent_graph()` 使用进程内 `MemorySaver`。调用方以 `configurable.thread_id` 标识一次运行，并可通过 `graph.get_state(config)` 读取最后的检查点。
- 进程内检查点不跨服务重启保存；持久化检查点属于后续基础设施工作，不能将其误称为已实现。

## 图结构

```text
START -> classify_task -> plan_task
                         |- evidence_qa -> local_search -> evidence_check
                         |- literature_search -> pubmed_search -> evidence_check
                         |- research_direction -> direction_analysis -> citation_check
                         `- writing -> writing -> citation_check

evidence_check -> citation_check | pubmed_search | human_confirmation | error
citation_check -> complete | error
human_confirmation -> END
error -> END
complete -> END
```

任务分支完全根据显式 `task_type`、`evidence`、`needs_external_search`、`pending_confirmations` 和 `errors` 选择；不使用自由文本作为控制条件。`max_steps` 在每个节点推进时强制检查，避免条件边造成无限循环。

## 调用示例

```python
from app.agents.graph import build_agent_graph

graph = build_agent_graph()
config = {"configurable": {"thread_id": "example-run"}}
result = graph.invoke(
    {
        "user_query": "What evidence is available?",
        "task_type": "evidence_qa",
        "evidence": ["caller-provided source excerpt"],
    },
    config=config,
)
snapshot = graph.get_state(config)
```

当没有提供证据时，图会以失败状态结束并报告 `evidence_not_available_after_search`，不会伪造证据。出现 `pending_confirmations` 时，图结束于 `awaiting_confirmation`；真正的 LangGraph `interrupt/resume` 人工确认机制留给 R4-WP14。

## 数据库

本工作包无数据库模型和 Alembic 迁移。
