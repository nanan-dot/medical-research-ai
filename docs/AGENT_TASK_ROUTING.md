# R4-WP13 Agent 任务分类与路由

## 契约

`TaskDecision` 是内部不可变分类结果，包含：

- `task_type`
- `confidence`
- `required_tools`
- `use_agent`
- `clarification_needed`
- `reason`

HTTP 契约集中在 `app/agents/schemas.py`：`AgentTaskRequest` 与 `AgentRoutingDecision`。`POST /api/v1/agent/tasks` 只返回路由计划，不执行工具、网络请求或模型调用。

## 路由原则

- 单篇论文问答、笔记问答、外部检索、多论文比较、候选方向和写作提纲均优先使用固定工作流，`use_agent=false`。
- 一条请求同时命中两个或更多受控任务类型时，标记为 `complex_research`，`use_agent=true`，工具列表由命中的固定工具去重后加上 `citation_check`。
- 没有命中规则的请求默认进入 `clarification`，不会为追求 Agent 使用率而升级为 Agent。
- 可选的复杂任务分类器只能返回高置信度、明确的 `complex_research` 决策；否则会安全降级为澄清请求。

## 工具安全

分类器只生成预定义工具名，不调用工具。后续执行层必须再通过 `ToolRegistry` 校验工具存在性和幂等性；分类结果不构成医疗建议、研究结论或自动化执行授权。

## 分类集

最小分类集位于 `data/evaluation/agent_routing.jsonl`，包含固定任务、复合任务及澄清任务。数据集只使用通用任务表述，不包含论文、患者或医学结论。

## 数据库

本工作包没有数据库变更，也没有 Alembic 迁移。
