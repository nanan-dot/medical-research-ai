# 论文阅读工作区后端 V1.0 验收追踪

来源：`论文阅读工作区后端支撑设计V1.0.md`、最终交互方案、页面状态与路由规则和执行提示词。以下条件均为冻结的 Given / When / Then，测试先于实现编写。

| ID | Given | When | Then | 测试 |
|---|---|---|---|---|
| PRR-AC-001 | anchor/layout 存在多个代际 | 获取 bootstrap | 只返回同一 anchor 衍生的 segmentation fence | `test_revision_fence_rejects_mixed_generation` |
| PRR-AC-002 | 已保存精确位置 | 刷新并创建/复用会话 | 恢复相同页和页内比例 | `test_position_round_trip_and_version_conflict` |
| PRR-AC-003 | 快速经过多页 | 提交 exposure | 未满足停留与可见比例的页不合格 | `test_fast_flip_is_not_qualified` |
| PRR-AC-004 | 38 页中 26 页合格 | 投影进度 | 返回 26/38 与 68% | `test_progress_projects_26_of_38` |
| PRR-AC-005 | 同 session/page 重复 exposure | 批量提交 | 合并事实且不重复累计 | `test_duplicate_exposure_merges_without_double_counting` |
| PRR-AC-006 | 相同记录过滤器 | 获取 summary 与 list | 计数一致 | `test_record_summary_matches_filtered_list` |
| PRR-AC-007 | annotation 有/无 note | 分类 | 分别只计 annotation/highlight 一次 | `test_annotation_classification_is_disjoint` |
| PRR-AC-008 | 历史与科研记录并存 | 隐藏历史 | 书签、疑问、批注不删除 | `test_history_delete_is_non_cascading` |
| PRR-AC-009 | PDF 文件已换版 | 旧会话写位置 | 409 `DOCUMENT_FILE_CHANGED`，旧记录需重定位 | `test_file_change_rejects_old_write` |
| PRR-AC-010 | 相同幂等键与载荷 | 创建 session/workspace/candidate | 返回同一资源 | `test_idempotency_reuses_same_payload` |
| PRR-AC-011 | 相同幂等键不同载荷 | 创建资源 | 409 `IDEMPOTENCY_KEY_REUSED` | `test_idempotency_rejects_different_payload` |
| PRR-AC-012 | 旧 expected_version | 修改位置/偏好/问题/收藏 | 409 且不覆盖新状态 | `test_position_round_trip_and_version_conflict` |
| PRR-AC-013 | Copilot 返回可展示引用 | 序列化消息 | citation 含 SourceAnchor 身份 | `test_citation_contract_exposes_source_anchor` |
| PRR-AC-014 | Copilot 无可靠证据 | 生成回答 | 使用 no-answer 状态 | `test_no_evidence_policy_returns_no_answer` |
| PRR-AC-015 | 翻译 unavailable | 获取 bootstrap/使用其他能力 | 阅读、记录、Copilot capability 不受阻 | `test_translation_unavailable_does_not_disable_reader` |
| PRR-AC-016 | 本地单用户部署 | 访问 reader 数据 | 稳定 actor_scope 隔离，预留认证接入点 | `test_actor_scope_is_required_and_bounded` |
| PRR-AC-017 | 越界页/超大 batch/非法 cursor/status/缺 anchor | 请求 API | 422 或领域错误拒绝 | `test_input_boundaries` |
| PRR-AC-018 | 新旧数据库 | upgrade/downgrade/heads | 往返成功且 single head | `test_reader_migration_round_trip` |
| PRR-AC-019 | 现有 A0—A4/annotation/library/conversation | 运行相关回归 | 契约不破坏 | 相关模块回归命令 |
| PRR-AC-020 | 已发布 A1 章节 | 请求 chapter bundle | 仅返回结构化原文与 revision fence | `test_chapter_bundle_is_extractive` |
| PRR-AC-021 | 活跃阅读历史 | 游标分页 | `(last_seen_at,id)` 稳定倒序且非法 cursor 被拒绝 | `test_history_cursor_round_trip` |
| PRR-AC-022 | reader 可变资源 | 并发更新 | 使用 version/ETag，冲突返回可恢复状态 | `test_position_round_trip_and_version_conflict` |
| PRR-AC-023 | anchor/layout 未 ready | 获取 bootstrap | 200 降级 capability，不伪造章节 | `test_translation_unavailable_does_not_disable_reader` |

## Phase 0 RED 记录

专项验收测试在 `app.modules.document_reader` 尚不存在时运行，测试收集阶段应失败；该失败是实现前 RED 证据，不计为最终通过。

## 实际验证结果（2026-09-02）

- RED：首次运行因 `app.modules.document_reader` 不存在，收集阶段 1 error。
- GREEN：Reader 策略与契约专项 14 passed；相关 A0—A4、annotation、paper library、conversation 回归先后为 198 passed、65 passed、30 passed。
- 全后端：`python -m pytest -q` 实际为 **1147 passed、13 skipped**（1313.03 秒）；统一错误响应与模型注册表的回归契约已同步。
- 迁移：隔离 SQLite 实际执行 upgrade → downgrade → upgrade；`alembic check` 无新增操作；`r1e2a3d4e5r6` 为单一 head。
- 静态检查：Reader 范围 Ruff 与 mypy 通过。仓库 Ruff 有 6 个既有 import 排序错误；conversation 扩展 mypy 导入链有 3 个既有错误。
- 受控性能（Windows/Python 3.12，38 页、18,953 bytes、100 次）：首段 64 KiB 读取 P95 0.0946 ms；26/38 进度投影 P95 0.0028 ms；历史 cursor 解码 P95 0.0019 ms。

性能数据是受控技术基线，不等同于真实医学 PDF 的 HTTP 端到端 bootstrap SLA。
