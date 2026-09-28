# 研究资源资料库后端验收追溯

> 本文是“研究资源 → 资料库”后端能力的验收来源。每个 AC 都先由可执行测试定义；只有对应测试、迁移和质量门禁全部通过，状态才能标为通过。

## 统计口径

- `total`：纳入资料库范围的所有持久化 `Document`。
- `processed`：`parse_status=succeeded`，不以 `total - processing` 推导；它可与下列结果状态重叠。
- `ai_available`：解析成功、索引成功且 `paperqa_index_key` 非空。
- `processing`：尚未归入问题状态，且解析或索引为 `pending`、`parsing`、`indexing`。
- `needs_attention`：解析失败、索引失败/过期、扫描过期、源文件丢失、来源不可用，或远端元数据项无法建立 AI 索引。

`total` 与最终健康分类（AI 可用 / 处理中 / 需处理）互斥；`processed` 是流水线里程碑，因此可与 `ai_available` 或“内容已更新”重叠。所有计数均从数据库状态聚合，不从当前分页推断。

## 验收追溯

| AC | Given / When / Then | 主要测试 | 初始状态 | 最终结果 |
|---|---|---|---|---|
| AC-LIB-01 | 给定混合解析/索引状态；请求 summary；返回五类事实计数、问题/来源拆分和快照时间 | `tests/modules/library/test_library_api.py::test_summary_uses_persisted_state` | RED | 通过 |
| AC-LIB-02 | 给定多个历史和活动任务；刷新资料项；返回最新活动任务及真实进度 | `tests/modules/library/test_library_api.py::test_item_exposes_latest_active_task` | RED | 通过 |
| AC-LIB-03 | 给定标题、路径、来源名和正文命中；用单一 q 查询；返回统一页和安全摘要 | `tests/modules/library/test_library_query.py::test_unified_search_matches_all_fields` | RED | 通过 |
| AC-LIB-04 | 给定多条件和并列排序；翻页并请求 facets；总数、顺序和 self-excluding facets 正确 | `tests/modules/library/test_library_query.py::test_filters_sorting_and_facets_are_global` | RED | 通过 |
| AC-LIB-05 | 给定本地/Obsidian 深层目录；请求来源树并按节点筛选；直接/后代计数和 Windows 规范路径正确 | `tests/modules/library/test_source_tree.py::test_source_tree_counts_and_node_filter` | RED | 通过 |
| AC-LIB-06 | 给定显式 opened 和只读请求；查询 recent；只显式打开改变计数，排序分页稳定 | `tests/modules/library/test_recent_access.py::test_document_opened_is_persistent_and_idempotent` | RED | 通过 |
| AC-LIB-07 | 给定 PDF/DOCX/PPTX/MD/TXT 批量上传；导入；逐项接受并建立可追踪持久化任务 | `tests/modules/library/test_library_import.py::test_multi_format_import_creates_document_tasks` | RED | 通过 |
| AC-LIB-08 | 给定路径穿越、伪 MIME、超限、重复和恶意 ZIP；导入；逐项拒绝且无孤儿文件 | `tests/modules/library/test_library_import.py::test_import_rejects_unsafe_inputs_and_deduplicates` | RED | 通过 |
| AC-LIB-09 | 给定托管/外部/丢失/重复资产和可选配额；请求 storage；返回真实聚合与诚实配额状态 | `tests/modules/library/test_storage.py::test_storage_separates_managed_and_external_bytes` | RED | 通过 |
| AC-LIB-10 | 给定无 Zotero 配置；测试/同步；返回稳定 `zotero_not_configured`，本地 API 正常 | `tests/modules/library/test_zotero.py::test_zotero_not_configured_is_structured` | RED | 通过 |
| AC-LIB-11 | 给定 mock Zotero 版本流、集合、附件和 429；增量同步；恢复游标且按 Retry-After 重试 | `tests/modules/library/test_zotero.py`（adapter、附件、集合、tombstone） | RED | 通过：429、游标、集合缓存/树、官方附件下载、受管资产与 tombstone 均由 mock 合约测试覆盖 |
| AC-LIB-12 | 给定无附件的 Zotero item；同步并汇总；标记 metadata_only 且不计入 AI 可用 | `tests/modules/library/test_zotero.py::test_zotero_metadata_only_is_not_ai_available` | RED | 通过 |
| AC-LIB-13 | 给定内容哈希变化；列表后重处理；先为 outdated、成功后恢复 AI 可用 | `tests/modules/library/test_library_api.py::test_outdated_document_recovers_after_reprocess` | RED | 通过 |
| AC-LIB-14 | 给定 PDF/DOCX 和其他格式；列表、详情、preview；能力声明与实际服务一致 | `tests/modules/library/test_preview_contract.py::test_preview_capability_matches_preview_service` | RED | 通过 |
| AC-LIB-15 | 给定失败/取消/重试及并发重复提交；执行动作；幂等且刷新可恢复 | `tests/modules/library/test_task_lifecycle.py::test_document_task_lifecycle_is_idempotent` | RED | 通过 |
| AC-LIB-16 | 给定文档访问和外部来源文件；删除文档；访问记录/任务关联消失，外部文件保留 | `tests/modules/library/test_recent_access.py::test_document_delete_cascades_access_without_deleting_external_file` | RED | 通过 |
| AC-LIB-17 | 给定搜索、路径、上传和 Zotero 错误；调用 API；返回结构化安全错误且不暴露绝对路径/凭证 | `tests/modules/library/test_library_security.py::test_library_errors_do_not_leak_paths_or_credentials` | RED | 通过 |
| AC-LIB-18 | 给定空临时数据库；upgrade→downgrade→upgrade 与 check；迁移可逆且相关回归全绿 | `tests/modules/library/test_library_migration.py::test_library_migration_roundtrip` | RED | 通过：资料库 migration 回环、完整图末端回环与 `alembic check` 均通过 |

## 验证门禁

- 定向资料库、document、preview、upload、task、sync 测试。
- 临时 SQLite 迁移回环和 `alembic check`；不连接正式数据库。
- `ruff check`、仓库配置的 `mypy`、`git diff --check`。
- 在风险允许时运行完整后端 `pytest`，并把实际结果回填本文件。

## 本轮实际验证（2026-08-30）

- 新增资料库验收：`pytest tests/modules/library -q` → **41 passed**，1 条既有 Starlette/httpx 弃用警告。
- 受影响回归：knowledge_source、document、document_preview、document_upload、sync、task 与 library → **136 passed, 2 skipped**，1 条同类弃用警告。
- 临时 SQLite：本资料库 migration `i2j3k4l5m6n` 已验证 upgrade → downgrade → upgrade；完整迁移图也已在当前 head 执行 downgrade → upgrade。
- `mypy app/modules/library` → **Success: no issues found in 10 source files**；全项目 mypy 仍有 22 个来自并行 recommendation/evaluation/conversation/literature 模块的既有错误。
- `ruff check app tests` → **All checks passed**。
- 完整后端：`pytest -q` → **891 passed, 13 skipped**，Starlette/httpx 弃用警告及既有 aiosqlite 测试线程清理警告各 1 条。
- `alembic heads` → **单一 head `m4n5o6p7q8r9`**；临时完整库的 `alembic check` → **No new upgrade operations detected**。
- 全局 `git diff --check` 未通过，原因是用户已有的 `frontend/src/views/LiteratureSearch/HistoryPagination.vue:12` EOF 空白行；资料库新增文件未报告 whitespace error。
