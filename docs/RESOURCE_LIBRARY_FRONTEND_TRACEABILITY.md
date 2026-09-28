# 资料库前端验收追溯

## 范围与约束

- 路由保持为 `/documents` 和 `/documents/:id`；产品文案改为“资料库/资料”。
- 旧 `Document` 领域模型、详情和预览接口保持兼容；统一资料库查询只使用已存在的 `/api/v1/library` 契约。
- 所有可见的数量、来源、状态、进度和资料名称必须来自 API；未提供的能力显示明确的不可用状态。
- 本轮不修改后端、数据库迁移或其他页面的业务实现。侧栏、面包屑和首页入口仅做用户明确要求的资料库名称替换。

## 组件复用 / 修改 / 新增矩阵

| 分类 | 文件或组件 | 处理 | 职责 |
|---|---|---|---|
| 复用 | `DocumentDetailsDrawer.vue` | 修改 | 保留既有预览和焦点陷阱，按资料库文案、URL Drawer 深链接调用。 |
| 复用 | `DocumentTable.vue` | 修改 | 保留语义表格、当前页选择、修复/详情动作；对接统一资料库状态映射。 |
| 复用 | `DocumentSummaryCards.vue` | 修改 | 由 4 张文档统计改为 5 项真实资料库汇总。 |
| 复用 | `DocumentScopeNav.vue` | 修改 | 由平面来源列表改为来源树、最近使用、树搜索与键盘导航。 |
| 复用 | `DocumentFilters.vue` | 修改 | 由基础文档筛选改为统一资料搜索、真实 facets 和 URL 筛选工具栏。 |
| 复用 | `DocumentManager.vue` | 修改 | 保留页面编排、分页、批量选择和详情；转为资料库 API 的薄编排层。 |
| 复用 | `DocumentsView.vue` | 修改 | 保留 `/documents` 路由入口，更新标题区和操作。 |
| 新增 | `api/resourceLibrary.ts` | 新增 | `/api/v1/library` 契约、输入校验、请求适配。 |
| 新增 | `composables/useResourceLibrary.ts` | 新增 | 资料库并发请求、取消、可恢复 URL 状态的数据加载。 |
| 新增 | `ResourceTaskBanner.vue` | 新增 | 已持久化行任务的当前视图任务摘要；没有后端聚合时明确不显示。 |
| 新增 | `ResourceImportDialog.vue` | 新增 | 真实多文件导入与逐项结果反馈。 |

## 数据/API 门禁

| 能力 | 状态 | 已验证契约/说明 |
|---|---|---|
| 全局汇总 | LIVE | `GET /api/v1/library/summary`。 |
| 统一查询、服务端筛选、分页和 facets | LIVE | `GET /items`、`GET /facets`。 |
| 来源树与去重计数 | LIVE | `GET /source-tree`；使用 `descendant_count`。 |
| 最近明确打开资料 | LIVE | `POST /items/:id/opened` + `GET /recent`。 |
| 行任务状态 | LIVE（无百分比时降级） | `LibraryItemRead.task_status/phase/current_item`；只在返回真实 `progress` 时显示百分比。 |
| 资料导入 | LIVE | `POST /imports`，逐项返回 `status/document_id/task_id/error_code`。 |
| 存储统计 | LIVE | `GET /storage`；未配置配额不显示伪造上限。 |
| Zotero 树/状态 | PARTIAL | 来源树可显示；连接、限流和同步恢复状态缺少专用 UI 契约。 |
| PDF/DOCX 预览 | LIVE | 继续复用既有 `/documents` 预览能力。 |
| 单项修复、重处理 | LIVE | `POST /items/:id/repair`、`/reprocess`。 |
| 批量修复/重处理、删除、全局任务聚合 | BACKEND_REQUIRED | 当前 `/library` 契约未提供 selection token、批量动作、删除或任务聚合端点；前端不会伪造。 |

## 验收标准到测试映射

| AC | 实现位置 | 测试 | 验证状态 |
|---|---|---|---|
| AC-RL-01 | `DocumentsView`、导航、面包屑、route meta、详情返回 | `DocumentsView.test.ts`、`AppSidebar.test.ts`、`Breadcrumbs.test.ts` | PASS |
| AC-RL-02 | `DocumentsView`、`DocumentManager` CSS | `e2e/resource-library.spec.ts` 四视口与区域截图 | PASS |
| AC-RL-03 | `resourceLibrary.ts`、`DocumentSummaryCards` | `DocumentSummaryCards.test.ts`、资料库 API 测试 | PASS |
| AC-RL-04 | `DocumentScopeNav` | `DocumentScopeNav.test.ts` | PASS |
| AC-RL-05 | `DocumentScopeNav`、资料树 API | `DocumentScopeNav.test.ts` 键盘测试、来源树后端测试 | PASS |
| AC-RL-06 | `DocumentScopeNav` | `DocumentScopeNav.test.ts` 搜索/恢复展开测试 | PASS |
| AC-RL-07 | `DocumentManager`、`resourceLibrary.ts` | `DocumentManager.test.ts` | PASS |
| AC-RL-08 | `DocumentManager` URL 状态 | `DocumentManager.test.ts`、Playwright 前进后退测试 | PASS |
| AC-RL-09 | `useResourceLibrary` | `useResourceLibrary.test.ts` 请求竞态测试 | PASS |
| AC-RL-10 | `DocumentFilters`、`resourceLibrary.ts` | `DocumentFilters.test.ts`、资料库查询后端测试 | PASS |
| AC-RL-11 | `ResourceTaskBanner`、表格 | `ResourceTaskBanner.test.ts`、`DocumentTable.test.ts` | BACKEND_REQUIRED（全局任务聚合契约缺失；当前仅安全显示查询结果中的持久化行任务） |
| AC-RL-12 | `DocumentTable` | `DocumentTable.test.ts` 状态映射测试 | PASS |
| AC-RL-13 | `DocumentManager`、`DocumentTable` | `DocumentManager.test.ts` | BACKEND_REQUIRED（批量/删除） |
| AC-RL-14 | `DocumentManager`、`useResourceLibrary` | `DocumentManager.test.ts`、Playwright 深链接测试 | PASS |
| AC-RL-15 | `DocumentDetailsDrawer`、现有预览组件 | `DocumentDetailsDrawer.test.ts`、Playwright Drawer 测试 | PASS |
| AC-RL-16 | `ResourceImportDialog` | `ResourceImportDialog.test.ts` | PASS |
| AC-RL-17 | `DocumentScopeNav`、来源管理入口 | `DocumentScopeNav.test.ts` | BACKEND_REQUIRED（恢复状态契约） |
| AC-RL-18 | 汇总、来源树、表格 | API 测试、`DocumentScopeNav.test.ts` | PASS |
| AC-RL-19 | 树、Drawer、表格、工具栏 CSS | 树/菜单/Drawer 单元键盘与焦点测试、Playwright 流程 | PASS |
| AC-RL-20 | 前端验证命令和浏览器套件 | typecheck、Vitest、build、ESLint、Playwright | BLOCKED（全仓 ESLint 被本任务未改动的 `frontend/src/components/PaperResults/PaperResults.vue:15:88` 错误阻断） |

`PASS` 只会在相应测试实际通过后填写；本文件中的 `BACKEND_REQUIRED` 表示缺少可安全调用的真实后端契约，而不是前端模拟。

## 实际验证记录（2026-08-30）

- `npm run typecheck`：通过。
- `npm test`：通过，70 个测试文件、204 项测试；`e2e/**` 已明确交由 Playwright，避免被 Vitest 当作 jsdom 测试加载。
- `npm run build`：通过；保留既有 `DocumentDetailView` 大于 500 kB 的构建提示。
- `npx playwright test e2e/resource-library.spec.ts --workers=1`：通过，8 项；覆盖桌面、紧凑桌面、平板和手机视口、空结果、修复任务、深链接、前进/后退、键盘树和 Drawer。
- 资料库后端回归：`pytest` 选定的 API、查询、来源树、最近打开、存储、导入和任务生命周期用例 13 项均通过。
- `git diff --check`：通过（仅输出仓库现存的 CRLF 提示）。
- 本次资料库文件的 ESLint：无 error；项目全量 ESLint 仍有 1 个本任务未改动的 `PaperResults.vue` error，故不把 AC-RL-20 标为 PASS。
- 截图保存在 `docs/frontend-rebuild/screenshots/resource-library/`，含 1536×960、1280×800、768×1024、390×844 及各关键区域和桌面 Drawer。
