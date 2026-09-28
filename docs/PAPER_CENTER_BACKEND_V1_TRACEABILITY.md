# 论文中心 V1 后端追溯

## 区域与数据源

| 页面区域 | API | 数据源 |
| --- | --- | --- |
| 当前研究 | `GET/PUT/PATCH /paper-research/current-context` | `paper_research_center_preferences`、`research_contexts` |
| 继续研究 | `GET /paper-research/center` | 论文库成员、工作状态、分析快照、阅读 session |
| 近期动态 | `GET /paper-research/center`、`/activities` | `paper_activities` |
| 最近论文 | `GET /paper-research/center` | 论文库成员、工作状态 |
| 统一统计 | `GET /paper-research/center` | 论文库成员、工作状态、分析快照 |

## 固定口径

- `papers`：正式 `PaperLibraryMember` 数量。
- `reading`：`PaperWorkState.reading_status == reading` 的论文数。
- `deep_reading`：有 `pending` 或 `analyzing` 分析快照的论文数。
- `completed`：阅读完成且没有进行中分析的论文数。
- `pending_confirmation_items`：有待确认字段的论文数；`pending_confirmation_fields`：这些字段的总数。

## 下一步规则

`confirm_analysis` > `continue_analysis` > 精确 `continue_reading` > 章节降级
`continue_reading` > `start_reading` > `start_analysis` > 不可用。规则实现在纯函数
`paper_research.next_action.decide_next_action`；不可用资源不返回可执行 target。

## 验收追溯

| AC | 行为测试 |
| --- | --- |
| 01 | `test_center_empty_contract_and_limit_validation` |
| 02、03 | `test_current_context_is_explicit_versioned_and_clearable` |
| 04、17 | `test_current_context_compare_and_swap_uses_independent_sessions`（两个独立 session 并发更新） |
| 05、13 | `test_center_projects_capabilities_context_isolation_and_activity_scope` |
| 06 | `test_next_action_priority_and_fallbacks_are_explicit` |
| 07 | `test_reader_resume_uses_latest_valid_session_and_degrades_on_hash_change` |
| 08、15 | `test_center_query_budget_is_constant_and_sorting_is_stable_for_500_candidates` |
| 09、10 | `test_activity_cursor_same_timestamp_is_stable_and_actor_scoped`、`test_activity_invalid_cursor_returns_structured_validation_error` |
| 11 | `test_center_projects_capabilities_context_isolation_and_activity_scope`（最近工作论文投影） |
| 12 | `test_center_summary_uses_latest_analysis_and_distinguishes_pending_items_fields` |
| 14 | `test_failed_cancelled_and_unknown_analysis_never_forge_progress_or_completion` |
| 16 | `test_center_empty_contract_and_limit_validation`、`test_center_get_is_read_only_and_openapi_contract_is_typed` |
| 18 | `test_paper_center_migration_upgrade_downgrade_upgrade_and_check` |
| 19 | `tests/modules/{paper_research,paper_library,document_reader,paper_analysis,research_context}` |
| 20 | scoped `git diff --check`、正式库 revision 恢复与只读复核；历史“从未写入”条件无法追溯验证 |

迁移 revision：`t4u5v6w7x8y9`。查询采用 set-based join，SQLAlchemy 事件预算验证了
1 与 500 候选保持相同查询次数。

最终验收结果：AC-PCB-01～19 已映射并通过；关联模块回归共 80 项通过。
AC-PCB-20 的工作区检查通过，正式库已恢复到原 revision `p3d4e5f6a7b8`，且新增偏好表不存在；
但正式库在验收过程中曾被一个运行中的应用进程自动迁移，因此“从未写入”这一历史条件无法声明为通过。
