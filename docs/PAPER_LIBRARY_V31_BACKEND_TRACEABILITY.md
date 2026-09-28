# 论文库 V3.1 后端验收追踪

本报告记录 2026-09-01 的论文库后端实现与实际验收证据。范围仅含后端、迁移、接口契约和测试；未改动论文阅读、论文分析的前端工作区或全局导航。

## 验收映射

| AC | 实现与接口 | 覆盖测试 | 实测结果 |
|---|---|---|---|
| AC-1 / B2 | `PaperAnalysis` 固化 `task_set_version`、任务集合及已完成任务；列表与概览共用同一进度投影。未知历史集合、空集合返回 `analysis_progress=null`，不会伪造完成数。`PaperAnalysisService.mark_task_completed` 支持执行器真实写入部分进度。 | `test_v31_projections.py`、`test_service.py::test_active_analysis_task_progress_is_persisted_and_idempotent` | 通过 |
| AC-2 / B1 | 多选标签改为单个 `EXISTS ... IN (...)`，实现组内 OR；其他筛选组仍为 AND；标签 facet 采用自排除计算。 | `test_api.py::test_multiple_tags_use_or_then_cross_group_uses_and` | 通过 |
| AC-3 / B3 | 列表在研究筛选下优先投影命中的论文—研究关系，`additional_relation_count` 保持完整关系数。 | `test_api.py::test_filtered_relation_is_projected_as_primary_relation` | 通过 |
| AC-4 / B2/B3 | 输出 `preferred_work_action`、`last_work_at`、`reading_entry`、`analysis_entry`；阅读/分析能力与阻断原因分开；重复阅读状态幂等，重置不保留章节或伪造继续阅读。分析开始、推进、完成更新入口，失败只记活动。 | `test_api.py` 的重复/重置/不可用/失败分析用例，`test_v31_projections.py` | 通过 |
| AC-5 / B4 | `POST /items/{id}/metadata/refresh` 复用 PubMed 与期刊指标服务，填充 DOI/PMID 对应的可信元数据；保存来源、年份、错误代码、可重试状态和原子重试次数；只补空字段，不覆盖已存用户字段。唯一标识竞争被收敛为 `identifier_conflict`，不泄漏 500。 | `test_metadata_enrichment.py` | 通过（使用模拟上游；真实 PubMed 请求【未实测】） |
| AC-6 / B5/B6 | 关系更新使用版本条件写入；同 DOI 并发添加由唯一约束兜底；列表固定批量查询；迁移 `a2c4e6f8b0d1` 从当前父迁移追加，并在空库和真实库安全副本升级。 | `test_runtime_guards.py`、空 SQLite 升级、正式库副本升级 | 通过 |

## API 契约

- `GET /api/v1/paper-library/summary`
- `GET /api/v1/paper-library/items`
- `GET /api/v1/paper-library/facets`
- `POST /api/v1/paper-library/items`
- `GET /api/v1/paper-library/items/{item_id}/overview`
- `POST /api/v1/paper-library/items/{item_id}/metadata/refresh`
- `PATCH /api/v1/paper-library/items/{item_id}/reading-state`
- `PUT /api/v1/paper-library/items/{item_id}/tags`
- `GET /api/v1/paper-library/items/{item_id}/activities`
- `PUT /api/v1/paper-library/items/{item_id}/research-relations/{research_id}`
- `DELETE /api/v1/paper-library/items/{item_id}/research-relations/{research_id}?expected_version=N`

新增论文时可提供 `doi`、`pmid` 或 `document_id`；刷新元数据时，响应的 `metadata_status` 为 `pending`、`running`、`succeeded`、`not_found` 或 `failed`。`metadata_retryable` 表示可再次触发刷新；不会把上游无结果或超时伪造成标题、作者、期刊或分区。

## 迁移影响

迁移 `a2c4e6f8b0d1_add_paper_library_v31_runtime_fields.py` 新增：

- `paper_analysiss` 的任务集合版本、任务快照和完成任务快照；
- `library_items` 的元数据处理状态、来源、错误、重试次数、最近尝试时间，以及期刊分区来源与年份。

旧分析记录没有可信任务快照时，进度明确为未知；不会回填推测值。降级会移除新增字段，因此降级前的 V3.1 元数据与任务快照无法保留；生产恢复策略是先备份数据库并仅执行向前迁移。

## 实测证据

- 论文库、论文分析、论文研究关系、研究上下文及原论文收藏回归：`50 passed, 1 warning`。
- `ruff check`：通过；`mypy app/modules/paper_library app/modules/paper_analysis --ignore-missing-imports`：通过；`compileall`：通过。
- 空 SQLite 从初始迁移升级至当前 Alembic 合并头 `n1b2c3d4e5f6`：通过。
- `data/app.db` 的安全副本升级至 `n1b2c3d4e5f6`：通过；副本：`C:\Users\ADMIN\AppData\Local\Temp\rag-medicine-paper-v31-formal-copy-20260901.db`。
- 对该安全副本执行 `summary`、`items`、`facets` API 冒烟请求均返回 200。
- 正式 `data/app.db` 已在创建备份后升级至 `a2c4e6f8b0d1`，论文库 `summary`、`items`、`facets` 冒烟请求均返回 200；备份：`data/backups/app-before-paper-library-v31-fix-20260901-1600.db`。

## 边界与待接线

- 本项目当前为本地单用户运行模型，本轮未新建或伪装多用户权限层。
- 前端尚需消费 `preferred_work_action`、`last_work_at`、两类入口和 `metadata_*` 字段；本轮未改前端，故前端联调【未实测】。
- 真实 PubMed 网络请求、外部期刊分区数据导入及真实用户文档全链路【未实测】；测试仅以模拟客户端验证成功、无结果、超时、重试、幂等和并发契约。
