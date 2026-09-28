# 检索中心 V2 第四轮验收追踪

| AC | 行为验收与证据 | 状态 |
| --- | --- | --- |
| AC-R4-01 | `StrategyWorkspaceV2.test.ts`：Header 不含“开始检索”；真实流程报告 `headerHasExecute: false` | 通过 |
| AC-R4-02 | `verify-real-search-strategy-flow.mjs`：`executeButtons.length === 1` 且 class 为 `.execute` | 通过 |
| AC-R4-03 | `LiteratureSearchView.test.ts`、`test_execute_reuses_existing_literature_task_service`：真实 execute API、失败恢复与结果 ID 路由 | 自动化通过；本轮本地浏览器未触发外部 PubMed 执行【未实测】 |
| AC-R4-04 | `SearchEntryView.test.ts`：断言 parse → expand → build → create 顺序；`real-flow-acceptance.json` 对应 API 访问日志 | 通过 |
| AC-R4-05 | `test_strategy_create_persists_generated_terms_and_mesh_snapshot`：完整 DTO、服务端 ID 与 GET 持久化 | 通过 |
| AC-R4-06 | `test_strategy_create_persists_generated_terms_and_mesh_snapshot`：PICO 模式不降级；真实流程 Journey 为第 3 步 | 通过 |
| AC-R4-07 | `StrategyWorkspaceV2.test.ts` Journey `aria-current`；真实流程 `journey: 3 构建检索策略` | 通过 |
| AC-R4-08 | 后端 create/GET 持久化测试；真实刷新后 `terms: 2` | 通过 |
| AC-R4-09 | `test_mesh_unavailable_keeps_expanded_terms_and_reports_a_partial_state`；真实刷新后 `mesh: 2`、普通术语仍为 6 | 通过 |
| AC-R4-10 | create/GET 持久化测试；真实刷新后 `query` 非空 | 通过 |
| AC-R4-11 | `StrategyTermsMeshSection` 的 `content-compact` 行为测试；`workspace-real-flow-1536x1024.png` 人工查看 | 通过 |
| AC-R4-12 | fixture 位于 `frontend/scripts/visual-test-only/`；生产 `src/` 未导入 fixture（最终静态检索） | 待最终门禁 |
| AC-R4-13 | `verify-real-search-strategy-flow.mjs` 生成真实 API 截图及刷新报告 | 通过 |
| AC-R4-14 | fixture 六视口 `geometry-report.json`；真实流程 `scrollWidth === clientWidth` | 通过（fixture/1536 真实流）；移动真实流【未实测】 |
| AC-R4-15 | 本次相关 ESLint、pytest、Vitest、typecheck；全量 gate 待最终运行 | 进行中 |
| AC-R4-16 | 本文、`real-flow-acceptance.json`、六视口截图、overlay/diff/geometry | 进行中 |

真实业务证据与视觉 fixture 严格分离。真实流程使用本地 API；fixture 只供可重复几何与截图检查。
