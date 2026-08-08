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
- 推荐模块测试：12 passed；
- 全量 `pytest`：435 passed，13 skipped，1 warning；
- Ruff/mypy、Alembic check、`git diff --check`：通过。

