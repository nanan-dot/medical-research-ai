# 知识库后端能力验收报告

## 1. 实施结论

知识库分页、汇总、健康状态、来源偏好、问题文档筛选以及持久化同步任务均已落地。同步接口只负责持久化入队；独立 Worker 负责领取、续租、执行与落库，避免请求内长任务和进程内伪任务。

Worker 启动命令：

```powershell
$env:PYTHONPATH = ""
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m app.cli.knowledge_source_sync_worker
```

单次领取一项任务后退出：

```powershell
$env:PYTHONPATH = ""
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m app.cli.knowledge_source_sync_worker --once
```

生产部署应将 API 与 Worker 作为两个受监督进程运行。Worker 收到 `SIGINT` 或 `SIGTERM` 后停止领取新任务；执行中的任务依靠数据库租约和心跳避免被其他 Worker 提前恢复。

## 2. 数据库迁移

迁移 `m1n2o3p4q5r6_add_knowledge_source_preferences.py` 增加：

- `knowledge_sources.auto_sync`
- `knowledge_sources.is_pinned`
- `task_records.idempotency_key`
- `task_records.lease_owner`
- `task_records.lease_expires_at`
- `task_records.heartbeat_at`

SQLite 连接统一启用 `PRAGMA foreign_keys=ON`，确保来源删除时数据库 Document 记录按声明级联删除，同时不会删除授权目录中的原文件。

## 3. API 与兼容性

- 保留 `GET /api/v1/knowledge-sources` 数组响应。
- 新增 `GET /api/v1/knowledge-sources/page`。
- 新增 `GET /api/v1/knowledge-sources/summary`。
- `PATCH /api/v1/knowledge-sources/{id}` 支持独立更新 `enabled`、`auto_sync`、`is_pinned`。
- `POST /api/v1/knowledge-sources/{id}/sync` 返回 `202 Accepted` 和持久化任务地址。
- `GET /api/v1/documents` 支持 `needs_attention=true`。

## 4. Acceptance Traceability

| AC | 自动化测试 | 结果 |
|---|---|---|
| AC-01 空库 | `tests/modules/knowledge_source/test_summary.py::test_empty_summary_has_zero_counts_and_null_percent` | PASS |
| AC-02 汇总与分页 | `tests/modules/knowledge_source/test_query_api.py::test_page_filters_full_dataset_and_keeps_old_array_contract` 同时断言分页与未分页汇总 | PASS |
| AC-03 类型动态计数 | `tests/modules/knowledge_source/test_service.py::test_summary_counts_source_types_once_and_classifies_each_issue_once`、`test_query_api.py` 混合类型数据 | PASS |
| AC-04 可用度 | `tests/modules/knowledge_source/test_service.py::test_stats_grouped_for_mixed_and_empty_sources` | PASS |
| AC-05 问题分类唯一 | `tests/modules/knowledge_source/test_service.py::test_summary_counts_source_types_once_and_classifies_each_issue_once` | PASS |
| AC-06 搜索安全 | `tests/modules/knowledge_source/test_query_api.py::test_page_search_escapes_like_and_preferences_are_independent` | PASS |
| AC-07 完整数据集筛选分页 | `tests/modules/knowledge_source/test_query_api.py::test_page_filters_full_dataset_and_keeps_old_array_contract` | PASS |
| AC-08 稳定排序 | `tests/modules/knowledge_source/test_query_api.py::test_page_sort_is_stable_and_pinned_sources_are_first` | PASS |
| AC-09 enabled/auto_sync 分离 | `tests/modules/knowledge_source/test_query_api.py::test_page_search_escapes_like_and_preferences_are_independent` | PASS |
| AC-10 置顶持久化 | 同上，跨请求 Session 读取并验证置顶 | PASS |
| AC-11 文档问题筛选 | `tests/modules/document/test_needs_attention_filter.py::test_document_list_accepts_needs_attention_filter` | PASS |
| AC-12 来源不可访问 | `tests/modules/knowledge_source/test_service.py::test_moved_directory_becomes_unavailable`、`test_api.py::test_permission_and_network_errors_are_explicit` | PASS |
| AC-13 同步重复提交 | `tests/modules/sync/test_persistent_sync_task.py::test_sync_submission_is_accepted_and_idempotent` | PASS |
| AC-14 同步恢复与心跳 | `test_expired_running_task_is_claimable_again`、`test_active_worker_can_renew_its_lease`、`test_worker_poll_loop_stops_cleanly` | PASS |
| AC-15 向后兼容 | `tests/modules/knowledge_source/test_api.py`、`test_query_api.py`、`tests/modules/sync/test_sync_api.py` | PASS |
| AC-16 删除影响 | `tests/modules/knowledge_source/test_service.py::test_delete_source_cascades_documents_but_preserves_file` | PASS |
| AC-17 静态路由 | `tests/modules/knowledge_source/test_summary.py::test_static_page_and_summary_routes_are_not_captured_as_ids` | PASS |
| AC-18 默认离线测试 | 上述验收测试只使用临时目录、临时 SQLite 与测试替身；全量默认测试未访问云模型、Ollama 或真实用户目录 | PASS |

## 5. RED → GREEN 记录

新增 Worker 验收测试首次执行结果为 `2 failed, 2 passed`：

- 缺少 `TaskRepository.renew_lease`；
- 缺少 `KnowledgeSourceSyncWorker.run`。

实现后定向结果为 `5 passed`，覆盖续租所有权、租约过期恢复、幂等提交、持续轮询和受监督退出。

## 6. 运行和部署约束

- `auto_sync` 当前只表示持久化偏好，尚未实现定时调度器。
- Worker 必须由 Windows 服务、任务调度器、Docker Compose、systemd 或其他进程管理器监督；仅启动 FastAPI 不会自动启动 Worker。
- 可横向启动多个 Worker；任务通过数据库条件更新领取，同一活动任务使用稳定幂等键。
- SQLite 适合当前本地优先部署；多机并发或高吞吐部署应迁移到 PostgreSQL 后重新做锁竞争与故障恢复压测。

## 7. 最终验证结果

- 后端全量 pytest：`603 passed, 13 skipped`。
- 本次相关 Ruff（`app`、`tests`、新增迁移）：通过。
- 全量 Mypy：`350 source files`，通过。
- 隔离的最新数据库执行 `alembic check`：通过，无待生成迁移。
- 前端 Vitest：`49 files / 118 tests`，通过。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run build`：通过；存在既有的单块大于 500 kB 提示，不影响构建成功。
- Worker CLI `--help`：通过，持续模式与 `--once` 模式均已暴露。

全量 `ruff check app tests alembic` 仍会报告 4 个历史迁移的既有导入空行问题：

- `a8c9d0e1f2a3_add_document_annotations.py`
- `b9d0e1f2a3b4_add_document_ocr_jobs.py`
- `c0e1f2a3b4c5_add_pmc_open_fulltext_acquisitions.py`
- `f7b8c9d0e1f2_add_document_assets.py`

本任务遵守“禁止修改历史迁移”，因此没有为了全量 Ruff 改写这些已存在 revision。当前 `data/app.db` 尚未升级到新 revision；为避免未经授权修改用户数据，本次只在隔离数据库验证了完整升级与 schema 一致性。正式运行前需要先备份数据库，再执行 `alembic upgrade head`。
