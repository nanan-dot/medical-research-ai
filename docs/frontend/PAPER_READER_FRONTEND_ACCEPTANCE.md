# 论文阅读工作区前端验收矩阵

状态：进行中。视觉基准为 `论文阅读.png`；本矩阵不以演示数据替代真实 reader API。

## 2026-09-03 视觉骨架回归

| 验收项 | 结果 | 证据 |
|---|---|---|
| PRF-AC-001 三栏、顶栏、工具栏、记录区比例 | 入口通过；真实数据待后端 | `PaperReaderView.vue`、`paper-reader-entry.spec.ts`（5/5） |
| PRF-AC-015 五视口无关键布局破损 | 通过 | 1280×800、1440×900、1536×1024、1024×768、768×1024 |
| 真实 API 阅读器 E2E | 通过（8/8） | `e2e/paper-reader-real-api.spec.ts`；含五视口、翻页、历史搜索/收起、真实选区批注 |
| 类型检查 / 生产构建 | 通过 | `npm run typecheck`、`npm run build` |
| 前端 lint | 【无可执行脚本】 | `package.json` 不含 `lint` |

| ID | 可观察验收行为 | 测试 / 证据 | 状态 |
| --- | --- | --- | --- |
| PRF-AC-001 | 桌面三栏、顶部元数据、工具栏和右侧记录区域存在 | `PaperReaderView.vue` 组合层；真实五视口截图 | 通过 |
| PRF-AC-002 | bootstrap 驱动标题、页数、进度与记录数 | `usePaperReaderBootstrap`，`paperReaderApi.bootstrap`；真实 API E2E | 通过 |
| PRF-AC-003 | 真实 PDF 可继续使用 PDF.js/A0-A4 阅读器 | `PdfReadingCanvas` 包装 `PdfAnnotationReader`；真实 API E2E | 通过 |
| PRF-AC-004 | 会话创建、位置恢复与关闭 | `usePaperReaderBootstrap`；真实 API E2E | 通过 |
| PRF-AC-005 | 旧论文响应不得污染新 generation | `usePaperReaderBootstrap.test.ts` | 通过 |
| PRF-AC-006 | 阅读历史来自服务端 | 后端契约已保留；新工作区待接入历史列表 | 未完成 |
| PRF-AC-007 | 选区创建真实锚点批注/高亮 | `PdfReadingCanvas` + `useDocumentAnnotations`；真实选区 E2E | 通过 |
| PRF-AC-008 | 记录汇总来自 record summary | `ReaderContextPanel` + `recordSummary`；真实 API E2E | 通过 |
| PRF-AC-009 | 开始研读使用幂等 handoff destination | `studyWorkspace`，要求 `research_context_id` | 已实现，待真实研究上下文 |
| PRF-AC-010 | chapter bundle 的 ready/not-ready 降级 | 接口已接入，UI 面板待补齐 | 未完成 |
| PRF-AC-011 | Copilot 携带文档和 revision fence | `ReaderContextPanel` 的 `ask` payload | 通过载荷审计；发送接口存在后端 500 风险 |
| PRF-AC-012 | 翻译 unavailable 不显示假译文 | `ReaderToolbar`、`ReaderContextPanel` | 已实现 |
| PRF-AC-013 | 换版/冲突不接受旧响应 | bootstrap generation 隔离；409 视觉恢复待补齐 | 部分完成 |
| PRF-AC-014 | 键盘可达与语义 tabs/按钮 | 组件使用原生按钮、tablist/tab、labels/live region | 已实现，待 Playwright |
| PRF-AC-015 | 五个视口无关键破损 | `e2e/paper-reader-real-api.spec.ts`，真实 reader 截图 | 通过 |

## 实际执行记录

- 2026-09-03：`npm run typecheck` 通过。
- 2026-09-03：`npm run build` 通过。
- 2026-09-03：`npm run test -- --run src/composables/usePaperReaderBootstrap.test.ts src/router/router.test.ts src/components/layout/AppSidebar.test.ts`：7 tests passed。
- 2026-09-03：`npm run test:e2e -- e2e/paper-reader-entry.spec.ts`：5 passed；截图写入 `docs/frontend-rebuild/screenshots/FE-R2/`。这仅为无静态数据的一级入口验收。
- 2026-09-03：`python -m pytest -q tests/modules/document_reader`：19 passed（1 warning）。
- 2026-09-03：真实后端 `GET /openapi.json` 返回 200；`GET /api/v1/paper-library/items?view=all&offset=0&limit=5` 返回 `items: []`，不能进行真实 reader PDF/API 流程验收。
- 2026-09-03：启动 `med-research-ai` 后端后，`npm run test:e2e -- e2e/paper-reader-real-api.spec.ts`：9 passed；生成五视口真实 reader 截图。
