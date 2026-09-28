# 医学文献实时翻译 Phase 1 验收追踪矩阵

状态：实施中（任何条目只有在所列自动化测试真实通过后才改为“通过”）

范围：PDF 阅读页自由选区的可信翻译闭环。复用 A2 共享原文锚点；不包含全文翻译、预取、论文库改造或专家黄金集结论。

| ID | Given / When / Then | 自动化证据 | 状态 |
|---|---|---|---|
| MT-P1-01 | 给定合法 A2 锚点，创建翻译时，生成排队任务且相同幂等键只生成一个作业 | `tests/modules/medical_translation/test_api.py` | 通过 |
| MT-P1-02 | 给定作业，执行时只允许 queued → running → quality_checking → succeeded/failed/cancelled，终态不可回退 | `tests/modules/medical_translation/test_state_quality.py` | 通过 |
| MT-P1-03 | 给定并发取消与完成，取消请求已生效时，迟到结果不得发布为成功 | `tests/modules/medical_translation/test_worker.py` | 通过 |
| MT-P1-04 | 给定租约过期或提供商失败，有限重试；超过上限后以安全错误失败，日志和 API 不泄露正文 | `tests/modules/medical_translation/test_worker.py` | 通过 |
| MT-P1-05 | 给定相同锚点和所有版本，相同缓存键命中；任一源文本、模型、提示、术语或校验版本变化即失效 | `tests/modules/medical_translation/test_state_quality.py` | 通过 |
| MT-P1-06 | 给定成功机器翻译，保存不可变修订、对齐、术语证据、质量报告和来源链 | `tests/modules/medical_translation/test_worker.py` | 通过 |
| MT-P1-07 | 给定数字、百分比、P 值、区间、95% CI、HR/RR/OR、单位、剂量、频次、方向和否定变化，确定性检查返回稳定代码、严重度及阻断标志 | `tests/modules/medical_translation/test_state_quality.py` | 通过 |
| MT-P1-08 | 给定无法确认或歧义术语，仅以本地规则标记 unresolved/ambiguous，不伪称 MeSH/UMLS 权威匹配；用户修订仅在文档/目标语言作用域生效 | `tests/modules/medical_translation/test_state_quality.py`、`test_api.py`、`test_worker.py` | 通过 |
| MT-P1-09 | 给定人工修订及正确乐观锁，新建不可变 human 修订；陈旧版本返回冲突且不覆盖历史 | `tests/modules/medical_translation/test_api.py` | 通过 |
| MT-P1-10 | 给定跨文档锚点、失效文件版本、超限文本或非法状态操作，请求被稳定错误模型拒绝 | `tests/modules/medical_translation/test_api.py` | 部分通过（跨文档、文件版本和状态操作已覆盖；超限 API 需补充） |
| MT-P1-11 | 给定快速连续选区，旧请求响应不得覆盖新选区；取消、重试、阻断、空态和错误态可访问 | `frontend/src/components/document/MedicalTranslationPanel.test.ts` | 部分通过（快速选区、空态、阻断和人工修订已覆盖；取消/重试 UI 由 API 单测覆盖） |
| MT-P1-12 | 给定真实阅读页构建，TypeScript、Vitest、生产构建及 Playwright 阅读页回归通过 | 命令证据记录于本文末尾 | 部分通过 |

## 冻结质量语义

- 作业成功只表示执行完成，不表示医学内容已由专家确认。
- `machine_checked`：确定性门禁通过；`needs_review`：存在非阻断风险；`blocked`：存在阻断问题；`human_reviewed`：人工保存了新修订。
- 失败、取消或 `blocked` 修订不会作为可直接采用的“当前成功译文”发布。
- 生产提供商通过依赖注入调用已配置模型；自动化测试只使用确定性假提供商。

## RED 基线

2026-09-01：`pytest tests/modules/medical_translation -q` 在收集阶段因 `app.modules.medical_translation` 不存在而失败；随后按验收项实现并转绿。

## GREEN 验证证据

2026-09-01：

- `pytest tests/modules/medical_translation -q`：21 passed。
- `pytest tests/modules/medical_translation tests/modules/document_anchor tests/modules/document_layout tests/modules/document_selection tests/modules/document_relocation -q`：167 passed。
- `ruff check app/modules/medical_translation app/cli/medical_translation_worker.py tests/modules/medical_translation ...`：passed。
- `npm run typecheck`、阅读页相关 Vitest（7 passed）和 `npm run build`：passed。
- `npm run test`：245/247 passed；2 个失败均为既有检索策略术语页 `StrategyWorkspaceV2.test.ts` 的文案断言，不涉及 PDF 翻译页，本次未修改该模块。
- Playwright `e2e/a4-reader-window.spec.ts e2e/a4-reading-context.spec.ts e2e/a2-source-selection.spec.ts --workers=1`：6/6 passed。使用隔离合成 PDF/SQLite 夹具和真实 API，覆盖跨页选区、锚点重开高亮、版本不匹配拒绝以及三种 PDF.js 视口。
- 后端全量 `pytest -q`：1071 passed、13 skipped；唯一失败是 `tests/test_database.py` 的注册表清单尚缺并发新增的 4 张论文库表。医学翻译表已纳入清单，且按任务边界未改动论文库。
- 干净 SQLite 数据库 `alembic upgrade head`：升级至 `f1b3c5d7e9a2` 成功，单一 head。

未执行且不能据此宣称完成的验证：真实模型连通性/结构化输出、真实医学专家黄金标注集、浏览器端到端 Playwright。生产环境接入前必须配置获授权的默认模型，并由领域专家完成黄金集复核。
