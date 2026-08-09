# 功能验收追溯报告

> 验收方法：将阶段验收标准映射到可复现的自动化测试；需要真实用户、导师反馈、实时外部服务或真实文献的条件不以模拟结果代替。
>
> 验收日期：2026-08-09

## 结论

- **自动化质量门：通过。** 后端共 `431 passed, 2 skipped`，前端共 `33 passed`。
- **R0：历史阶段验收通过；本轮代码质量门通过。** 云模型、Ollama 和 PaperQA2 的实时集成未在本轮调用。
- **R1：工程自动化验收通过；真实用户验收仍待执行。**
- **R2：不可签署通过。** `R2_USER_TEST_REPORT.md` 仍为空，缺少真实用户 9 步流程、相关性评分、5 篇真实 PMID/DOI 核验和产品负责人确认。
- **R3：不可签署通过。** 缺少真实研究主题、真实用户操作和真实导师反馈；不得用模拟数据补充。

## 规格与自动化测试追溯

| 阶段 | 验收条件 | 自动化验证 | 本轮结果 | 状态 |
| --- | --- | --- | --- | --- |
| R0 | 应用健康检查、路由注册和数据库会话可用 | `tests/test_health.py`、`tests/test_smoke.py`、`tests/test_database.py` | 通过 | PASS |
| R0 | RAG 基础检索、索引和错误处理可复现 | `tests/rag/`、`tests/unit/test_r0_*.py`、`tests/experiments/` | 通过 | PASS |
| R0 | 敏感文件不被跟踪、密钥不泄漏 | `tests/security/test_r0_security.py` | 通过 | PASS |
| R0 | 静态质量门 | `ruff check app alembic scripts experiments tests`、`mypy` | 通过 | PASS |
| R1 | 知识源登记、同步、文档解析、索引与重试 | `tests/modules/knowledge_source/`、`document/`、`indexing/`、`sync/` | 通过 | PASS |
| R1 | 问答、论文分析、导出与反馈流程 | `tests/modules/qa/`、`paper_analysis/`、`export/`、`feedback/` | 通过 | PASS |
| R1 | 用户独立完成 7 项任务和错误恢复 | `docs/R1_USER_TEST_SCRIPT.md` | 需要真人试用记录 | MANUAL REQUIRED |
| R2 | 主题解析和可编辑候选条件 | `tests/modules/literature_search/test_query_model.py`、`test_query_builder.py`、前端 `LiteratureSearchView.test.ts` | 通过 | PASS（自动化部分） |
| R2 | 检索式、MeSH 术语、布尔逻辑 | `tests/modules/literature_search/test_query_builder.py`、`test_search_api.py`、前端 `QueryBuilder.test.ts` | 通过 | PASS（自动化部分） |
| R2 | 检索结果筛选、排序、去重及撤销 | `tests/modules/literature_search/test_filters.py`、`test_dedup.py`、`test_history.py`、前端 `LiteratureFilters.test.ts`、`DuplicateReview.test.ts` | 通过 | PASS（自动化部分） |
| R2 | 保存文献、引用核验、阅读顺序 | `tests/modules/library/`、`citation_check/`、`literature_search/test_reading_order.py`、前端 `ReadingPlan.test.ts` | 通过 | PASS（自动化部分） |
| R2 | 比较矩阵、证据矩阵和 Markdown/CSV 导出 | `tests/modules/comparison/`、`tests/unit/test_evidence_matrix_service.py`、`tests/modules/export/` | 通过 | PASS（自动化部分） |
| R2 | 真实 PubMed 结果相关性≥4、检索式可读性≥3、5 篇真实标识符核验 | `docs/R2_USER_TEST_SCRIPT.md`、`R2_USER_TEST_REPORT.md` | 未提供真人/网络验收记录 | MANUAL REQUIRED |
| R3 | 证据来源可追溯、候选方向保持候选状态 | `tests/modules/research_direction/`、`recommendation/`、`evidence_analysis/` | 通过 | PASS（自动化部分） |
| R3 | 引文核验、AI 披露、风险/缺证据标记 | `tests/modules/citation_check/`、`ai_disclosure/`、`evidence_writing/` | 通过 | PASS（自动化部分） |
| R3 | 写作可编辑、版本可恢复、导出不伪造内容 | `tests/modules/writing_project/`、`presentation/`、`outline/` | 通过 | PASS（自动化部分） |
| R3 | 真实主题、真实导师反馈和人工来源逐条核验 | `docs/R3_USER_TEST_SCRIPT.md`、`R3_USER_TEST_REPORT.md` | 未执行 | MANUAL REQUIRED |

## 本轮实际执行记录

| 验证门 | 命令或范围 | 结果 |
| --- | --- | --- |
| 后端核心回归 | 单元、RAG、解析、安全、健康、数据库、冒烟 | `181 passed` |
| R2/R3 关键模块回归 | 文献检索、比较、引文、推荐、研究方向、写作、证据分析、演示 | `144 passed` |
| 其余业务模块回归 | 文档、知识源、同步、问答、反馈、可行性等 | `102 passed, 2 skipped` |
| 实验回归 | `tests/experiments` | `4 passed` |
| 后端静态检查 | Ruff + Mypy | 通过；Mypy 检查 22 个源文件 |
| 前端类型检查 | `npm run typecheck` | 通过 |
| 前端单元测试 | `npm test` | `33 passed` |
| 前端生产构建 | `npm run build` | 通过 |

## 已知事项

1. 前端 Vitest 全部通过，但测试日志有 Vue Router 注入和相对 `/api` 地址的测试环境警告。它们未阻断构建或测试，但建议后续完善测试挂载时的路由与 fetch mock。
2. `tests/integrations/` 依赖外部服务或本机模型，本轮未启用；不能将其记作通过。
3. R2 前端的证据矩阵页面当前标记为 MOCK，R2 第 9 步需要直接调用后端 API 验收，前端接入仍应按 Backlog 跟踪。

## 真人验收执行入口

- R1：按 `docs/R1_USER_TEST_SCRIPT.md` 完成 7 项任务并记录结果。
- R2：按 `docs/R2_USER_TEST_SCRIPT.md` 完成 9 项真实检索任务，填写 `docs/R2_USER_TEST_REPORT.md`，再更新 `docs/R2_ACCEPTANCE.md`。
- R3：按 `docs/R3_USER_TEST_SCRIPT.md` 完成真实主题、来源、导师反馈、导出与版本恢复验证，填写 `docs/R3_USER_TEST_REPORT.md`。

在这些人工证据齐备前，不得将 R1、R2 或 R3 标记为“最终验收通过”。
