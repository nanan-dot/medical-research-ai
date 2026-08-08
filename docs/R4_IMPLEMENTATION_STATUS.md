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
