# R4 实现状态

## R4-WP01 — 推荐请求理解与检索式构造

状态：已完成（后端纯函数能力）。

### 已交付

- 新增 `app/modules/recommendation/query_builder.py`；
- 新增 `app/modules/recommendation/__init__.py`；
- 复用 `literature_search.term_expansion` 和 `literature_search.query_builder`；
- 已知医学中文/英文术语使用现有 curated mapping；
- 未收录中文术语拒绝生成，避免擅自翻译或制造检索词；
- 支持综述 → PubMed `Publication Type` 约束；
- 空查询、超过1000字符和控制字符请求拒绝；
- 输出检索式、术语来源和可解释构造结果。

### 实际验证

- `pytest tests/modules/recommendation/test_recommendation_query_builder.py -q`：4 passed；
- 全量 `pytest`：427 passed，13 skipped，1 warning；
- `ruff check app/modules/recommendation tests/modules/recommendation`：通过；
- `mypy app/modules/recommendation --ignore-missing-imports`：通过；
- `alembic upgrade head` / `alembic check`：通过；
- 本 WP 无数据库迁移、无真实外部网络调用。

### 边界

- 本 WP 不检索 PubMed，不调用 LLM，不生成论文候选；
- 推荐理由和真实文献装配属于后续 WP02/WP03；
- 未收录医学术语必须由用户补充或后续经过核验的映射扩展，不能由模型凭记忆补全。

## R4-WP02 — 推荐检索与证据装配

状态：已完成（后端检索编排能力）。

### 已交付

- 新增 `RecommendationEvidenceService`；
- 复用 `PubMedExecutor` 的 ESearch + EFetch 和真实来源验证标记；
- 只保留有摘要且未撤回的真实记录；
- 按年份降序并执行可配置候选数量截断；
- 无可用记录时返回确定性警告，不制造推荐条目；
- 为 `CitationItem` 补充 PubMed真实撤回标记，旧快照缺失时兼容默认 `False`。

### 实际验证

- WP02服务测试：2 passed；
- 全量 `pytest`：429 passed，13 skipped，1 warning；
- Ruff/mypy：通过；
- Alembic upgrade/check：通过；
- 本 WP 无数据库迁移、无真实外部网络调用。

## R4-WP03 — LLM理由融合

状态：已完成（后端安全融合能力）。

### 已交付

- 新增 `RecommendationReasonService`；
- LLM输入仅包含真实摘要和固定安全指令，不提供题名、作者、PMID、DOI等元数据；
- 服务器端保留 `CitationItem` 全部真实字段，LLM只能填写 `recommendation_reason`；
- 模型输出包含论文元数据时整条理由拒绝并使用确定性降级；
- 无摘要或LLM失败时保留真实条目，不编造理由；
- `CitationItem`补充真实摘要字段，旧快照缺失时兼容 `None`。

### 实际验证

- WP03理由融合测试：3 passed；
- 全量 `pytest`：432 passed，13 skipped，1 warning；
- Ruff/mypy：通过；
- Alembic upgrade/check：通过；
- 本 WP 无数据库迁移、无真实云端调用。

## R4-WP04 — 推荐 API 与路由接入

状态：已完成（后端 MVP API）。

### 已交付

- 新增 `POST /api/v1/recommendations`；
- 请求契约：自然语言 `query`（1–1000字符）和 `candidate_count`（1–10）；
- 响应契约：`completed` / `completed_with_warnings` / `unavailable`、真实文献条目、理由和警告；
- 路由通过依赖注入使用 PubMedExecutor 和本地/云端已配置客户端；
- 本地模型不可用时不隐式切换云端，保留真实检索条目并降级理由；
- PubMed异常对外统一为503，不泄露供应商内部错误。

### 实际验证

- 推荐模块测试：10 passed；
- 全量 `pytest`：433 passed，13 skipped，1 warning；
- Ruff/mypy：通过；
- Alembic upgrade/check：通过；
- 本 WP 无数据库迁移。

## R4-WP06 — 推荐质量门

状态：已完成。

- 增加编排层回归测试，验证LLM不得改变服务器持有的PMID等元数据；
- 增加空证据集状态和警告回归测试；
- 推荐模块测试：13 passed；
- 全量 `pytest`：436 passed，13 skipped，1 warning；
- Ruff/mypy、Alembic check、`git diff --check`：通过。

## R4-WP05 — 推荐工作台前端

状态：已完成（LIVE 前端接入）。

- 新增 `/recommendations` 页面和 `recommendationApi`；
- 只调用 `/api/v1/recommendations`，不包含演示论文或前端生成医学结果；
- 展示检索中、错误、空结果、带警告结果和真实文献来源状态；
- 推荐理由与论文元数据分栏展示，并明确 LIVE · PubMed 边界；
- 加入知识资产导航和路由元数据，保留现有响应式/键盘焦点设计。

### 实际验证

- `npm run typecheck`：通过；
- `npm test -- --run`：33 passed；
- `npm run build`：通过；
- Vite `/recommendations`：HTTP 200；
- 浏览器渲染检查：通过，控制台无错误。

## R4-WP12 — LangGraph State 与工作流

状态：已完成（受限的内部 LangGraph 编排基础）。

### 已交付

- `app/agents/state.py`：可 JSON 序列化的 `AgentState` 与 LangGraph `AgentGraphState` 契约，覆盖任务类型、文档、证据、检索历史、候选方向、草稿、引用、人工确认、错误和步数。
- `app/agents/graph.py`：任务分类、规划、本地检索、外部检索、证据检查、方向、写作、引用检查、人工确认、错误和完成节点；所有条件边只读取显式状态字段，并限制最大步骤数。
- `app/agents/checkpointer.py`：进程内 `MemorySaver` 检查点，可通过 `thread_id` 和 `get_state` 读取运行快照。
- `docs/AGENT_GRAPH.md`：图结构、调用方式、边界和恢复说明。

### 验证

- `pytest tests/agents -q`：8 passed。
- 全量 `pytest -q`：476 passed，13 skipped，1 个第三方弃用警告。
- `ruff check app/agents tests/agents tests/test_database.py`：通过。
- `mypy app/agents --ignore-missing-imports`：通过。
- `pip check`：通过。

### 边界与下一步

- 本工作包不执行真实网络检索、模型调用、医学决策或内容生成；没有证据时明确失败，不伪造内容。
- 检查点目前仅在进程内保存，服务重启后不保留。
- 人工确认节点只停止在 `awaiting_confirmation`；R4-WP14 再实现 `interrupt/resume` 和确认策略。
- 无数据库迁移。

## R4-WP13 — Agent 任务分类与路由

状态：已完成（规则优先、复杂任务可注入分类器的安全路由）。

### 已交付

- `TaskDecision` 已补全任务类型、置信度、受控工具、Agent 使用标记、澄清标记与理由。
- `POST /api/v1/agent/tasks` 只返回分类和路由计划，不执行工具、模型或网络请求。
- 固定任务不启用 Agent；多工作流请求才启用 Agent；模糊任务要求用户澄清。
- `data/evaluation/agent_routing.jsonl` 与 `tests/agents/test_routing.py` 提供最小分类集和 API/安全降级回归测试。

### 验证

- `pytest tests/agents -q`：17 passed，1 个第三方弃用警告。
- `ruff check app/agents tests/agents app/api/v1/__init__.py`：通过。
- `mypy app/agents --ignore-missing-imports`：通过。

### 边界与下一步

- 默认实现不调用 LLM；复杂模型分类仅允许以注入依赖提供，并会拒绝低置信或非复杂任务建议。
- 分类结果不是工具执行授权，执行层仍需通过 `ToolRegistry` 校验。
- 无数据库迁移。
- 下一工作包为 R4-WP14：Agent 限制与人工确认。

## R4-WP14 — Agent 限制与人工确认

状态：已完成（受限审批与恢复基础）。

- 使用 `interrupt()` 暂停确认，并仅用相同 `thread_id` 的 `Command(resume=...)` 恢复；批准继续、拒绝/取消终止。
- 新增 `AgentLimits`，覆盖步骤、工具调用、资源单位和总时长限制的纯规则校验。
- 新增进程内 `AgentRunService` 与启动、批准、取消 API；不执行实际工具或云端调用。
- 无数据库迁移；检查点与运行记录仅在进程内保存，重启后失效。
- 验证：全量 `pytest -q` 为 488 passed、13 skipped；Ruff、mypy、pip check 和 git diff --check 通过。

## R4-WP15 — Agent 执行轨迹与可观测性

状态：已完成（本地脱敏轨迹与导出）。

- 记录运行开始和人工审批的节点、状态、摘要、耗时与审批信息；摘要会脱敏 API Key、Token、Password 和 `sk-` 密钥模式并截断。
- 提供 `GET /agent/runs/{id}/trace` 与 `POST /agent/runs/{id}/export-trace`。
- 运行轨迹默认仅保存在进程内；无数据库迁移，服务重启后不可恢复。
- 验证：全量 `pytest -q` 为 491 passed、13 skipped；Ruff、mypy、pip check 和 git diff --check 通过。
