# 医学实时翻译 Phase 2 验收追踪

状态：实施中（2026-09-01）。本文件仅覆盖医学翻译与既有 A0-A4 阅读器衔接；不涉及论文库。

## Given / When / Then 追踪

| ID | Given | When | Then | 自动化证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P2-FOLLOW-01 | A4 给出活动段 | 同段停留不足/达到 300ms | 不切换/只在阈值后切换 | `translationFollowPolicy.test.ts`；`medical-translation-follow.spec.ts` | PASS |
| P2-FOLLOW-02 | 人工选区、编辑或固定段存在 | 阅读器换段 | 自动跟随不得覆盖人工上下文 | `translationFollowPolicy.test.ts` | PASS |
| P2-FOLLOW-03 | 文档、A0/A1 或缩放代际变化 | 旧请求返回 | 旧上下文无效 | `translationFollowPolicy.test.ts`；组件代际 key | PASS |
| P2-ANCHOR-01 | A1 稳定段 | 提交段落意图 | 服务端通过 A2 `SourceAnchorService` 创建/复用锚点 | `test_api.py::test_segment_intent_uses_current_versions_and_deduplicates` | PASS |
| P2-DEGRADE-01 | 段为 blocked/review_required | 自动翻译意图 | 返回明确 `degraded` 原因，不伪造译文 | 服务端 `request_segments` | IMPLEMENTED |
| P2-CACHE-01 | 同文档同版本同段 | 重复提交意图 | 重用在途/成功任务，避免重复排队 | `test_api.py::test_segment_intent_uses_current_versions_and_deduplicates` | PASS |
| P2-PREFETCH-01 | 活动、相邻、远处可见段 | 预取队列排序 | 活动 > 相邻 > 远处，去重且有界 | `translationPrefetchPolicy.test.ts` | PASS |
| P2-PREFETCH-02 | 省流、弱网、后台或关闭跟随 | 预取 | 停止投机性预取 | `translationPrefetchPolicy.test.ts` | PASS |
| P2-PREFETCH-03 | 活动段与预取段都在队列 | worker 领取任务 | 活动段先于预取段执行 | `test_worker.py::test_worker_claims_active_reading_priority_before_prefetch` | PASS |
| P2-BILINGUAL-01 | 已有锚定译文 | 切换双语模式 | PDF 保持中央原文，右侧显示独立对照 | `BilingualTranslationView.test.ts` | PASS |
| P2-BILINGUAL-02 | provider 有/无精确对齐 | 点击原文句段 | 有对齐则回到 A2 锚点；无对齐明确降级 | `BilingualTranslationView.test.ts`；`PdfAnnotationReader.locateSourceAnchor` | PASS |
| P2-STATE-01 | 模式、跟随、固定状态 | 重开同文档 | 仅恢复偏好与标识，不在 localStorage 保存原文/译文 | 面板实现与安全检索 | PASS |

`P2-DEGRADE-01` 的正常、扫描件及复杂版面黄金样本尚未具备，故仅标记为已实现，不能替代人工医学/版面验收。

## RED → GREEN 记录

- RED：新增段落意图 API 测试首次暴露版本端点假设错误，后改为使用 A2 fixture 已创建的锚点版本。
- GREEN：段落意图 API 的当前版本/去重和过期版本测试通过；前端跟随、预取、面板和双语对照测试通过；TypeScript typecheck、生产构建、翻译后端 `mypy`、`py_compile` 与翻译范围 Ruff 通过。
- 尚未声称：真实翻译提供商、真实论文黄金集/专家医学审核、性能阈值、全量 API/E2E 回归。

## 实际门禁记录

- PASS：`pytest tests/modules/medical_translation/test_api.py::test_segment_intent_uses_current_versions_and_deduplicates`。
- PASS：`pytest tests/modules/medical_translation/test_api.py::test_segment_intent_rejects_stale_versions`。
- PASS：`pytest tests/modules/medical_translation/test_worker.py`（5 项）。
- PASS：`pytest tests/modules/medical_translation/test_worker.py`（更新后 6 项，含阅读优先级领取）。
- PASS：Phase 2 相关 Vitest（9 项）、`npm run typecheck`、`npm run build`。
- PASS：Playwright `medical-translation-follow.spec.ts`（隔离 SQLite、真实 FastAPI、真实 PDF.js 与合成 PDF；不调用外部翻译提供商）。
- PASS：医学翻译模块 `ruff`、`mypy`、`py_compile`。
- PASS：独立 SQLite 从空库 `alembic upgrade head` 到当前 `s2f3g4h5i6j7`；`alembic heads` 为单一 head，且日志确认执行 `b7d9f1a3c5e7` Phase 2 翻译迁移。
- 未通过（外部漂移）：独立库 `alembic check` 仍报告 A3 relocation 与论文库索引差异；复验后不含本次 `medical_translation_jobs.layout_segment_id` 索引。
- 未配置：当前数据库没有默认 `ModelConfig`；本地 Ollama `localhost:11434` 不可达。因此真实提供商联调没有可执行目标，未发送任何医学原文或云端请求。

## 数据与缓存边界

- 服务端 revision 是权威缓存；任务仍复用 Phase 1 的完整版本身份、质量门禁和不可变 revision。
- 客户端仅持久化 `followEnabled`、`pinnedSegmentId` 与显示模式；不持久化原文、译文、术语或解释。
- blocked、取消、失败不会被视作成功缓存；版面风险以降级状态返回。
