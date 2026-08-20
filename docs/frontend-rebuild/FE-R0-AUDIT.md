# FE-R0 基线冻结与契约盘点

## 恢复点与保护范围

- Git 恢复点：`ac8ac1b`（`feature/r0-wp01-baseline`）。
- 本次重建不移动、不删除 `frontend/`，也不清理 `.frontend-legacy-snapshot`。
- 用户明确保留的前端工作区差异：13 个已跟踪修改和 2 个未跟踪组件。下列 SHA-256 是开始增量整合前的内容指纹；后续只可在此基础上作可追踪的修改。

```text
13c71365b920e6a626323f2a529c1938b55032f14ced48d90416f0e516b6a5bb  src/api/documents.ts
794145d7721307518f69fb014601503067b983d09858c40be4d6d465fa9f91dc  src/api/knowledgeSources.ts
e1977605f3f51b90135dc6d9a3d7bba517939801a33884338dad7cf1f23d2277  src/components/document-navigation/DocumentNavigationPanel.vue
b424fd049b07399b5adb483a78db509016eab5743e123b4c56da43b2cc5cf427  src/components/document/DocumentFilters.vue
51a809311896d7130b65deaf1d147966b61229c1143a822cebfe698d29779627  src/components/document/DocumentManager.test.ts
6e88a4020c9737c3a2d13bf9a84b8138c84526c5731f78127eab3835ac5851e2  src/components/document/DocumentManager.vue
8c00e438219ba861e7a815778409f10d3590956efdf65246d537450d5dc45af5  src/components/document/DocumentScopeNav.vue
2be16f565434a45579dbb9e5846bb331a70d9615a61170ff126780fe695599cd  src/components/document/DocumentTable.test.ts
3afcd65f5a795c5f538dd537007db52125952670f498af16002664c6f57aafb8  src/components/document/DocumentTable.vue
6eea32d2bd633603d40064e1b8f98520003200f3c41156810e3d125ffc739e79  src/composables/useDocuments.ts
d1e69dea0ac1a3c654c53e76e28821eab559bd627afa246a3fe6a9dc95f2f554  src/layouts/AppShell.vue
ad69ab2d3ce950f8b5c91208494a8b742cff57f0b40f7ef99f819dac2e52e23f  src/views/Documents/DocumentsView.vue
0d106f275836c39e14dd1a9a96b3af24ca6750aeede74cb303143e8928ea2e28  vite.config.ts
```

未跟踪且同样受保护：`src/components/document/DocumentDetailsDrawer.vue`、`src/components/document/DocumentSummaryCards.vue`。

## 路由契约

| 路径 | 当前实现 | FE-R2 处理 |
|---|---|---|
| `/documents` | 文档库 | 保持；查询参数承载列表状态 |
| `/documents/:id` | 完整文档详情 | 保持；列表抽屉不替代此页面 |
| `/sources` | 知识库 | 保持；来源管理跳转目标 |
| `/analysis?documentId=:id` | 论文分析 | 保持现有文档跳转 |

## 真实 API 能力矩阵

| 页面能力 | 真实接口 | 状态 |
|---|---|---|
| 列表/全文搜索/来源/类型/状态/排序 | `GET /api/v1/documents` | LIVE |
| 全库统计 | `GET /api/v1/documents/statistics` | LIVE |
| 来源列表/摘要 | `GET /api/v1/knowledge-sources`、`/summary` | LIVE |
| 单项修复 | `POST /api/v1/documents/:id/repair` | LIVE |
| 解析/索引重试 | `POST /api/v1/documents/:id/retry-parse`、`retry-index` | LIVE |
| 任务进度 | 文档接口未提供任务状态轮询契约 | BACKEND_REQUIRED |
| 从问答资产中排除 | 无对应文档 API | BACKEND_REQUIRED |

## 已验证基线

- `npm test`：49 测试文件、119 测试通过（既有测试警告未阻断）。
- `npm run typecheck`：通过。
- `npm run build`：通过；Vite 报告既有大 chunk 警告。
- `npm run lint`：未定义 npm 脚本。

## FE-R1 / FE-R2 增量整合记录

- 沿用已有 Vue 3 + TypeScript + Vite 骨架；未替换或删除任何用户已有前端文件。
- `src/styles/tokens.css` 已收敛为 DESIGN.md 的锁定主色、语义色和圆角比例。
- `DocumentTable.vue` 从非语义列表增量升级为真实 `table`，保留既有 API 类型、事件与移动端适配；增加当前页全选和真实 `progress` 才显示的进度条。
- RED 证据：`DocumentTable.test.ts` 的“真实表格语义/当前页全选”先失败（缺少 `table`），随后实现后通过。

## Acceptance Traceability（本轮可验证项）

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-01 | `DocumentManager.test.ts`、`DocumentTable.test.ts` | PASS（结构自动化；视觉截图未完成） |
| AC-03/04/09/10 | `DocumentManager.test.ts` 的 sourceId 与 URL 测试 | PASS |
| AC-05 | `useDocuments.ts` 请求序号实现 | 未新增延迟响应测试 |
| AC-06/07 | `DocumentManager.test.ts` 服务端筛选测试 | PASS |
| AC-11/12/13 | `DocumentTable.test.ts`、现有详情/状态测试 | PASS（真实 progress 才显示） |
| AC-16 | `DocumentTable.test.ts` 当前页全选测试 | PASS |
| AC-19/23/25 | 现有 `DocumentManager.test.ts` 与 Vue 文本插值 | PASS |
| AC-20 | `DocumentDetailsDrawer.vue` 已实现 trap/Esc/焦点恢复；未新增自动化焦点断言 | 未完全验证 |
| AC-21/22 | 未完成菜单/四视口真实截图 | 未完全验证 |
| AC-02/08/14/15/17/18/24 | 有部分既有实现或测试，但未形成完整端到端验收 | 未完全验证 |

## BACKEND_REQUIRED

- 任务状态读取及进度轮询接口：现有 repair 只返回排队结果，没有可由文档页轮询的稳定任务查询契约。
- 从问答资产中排除：文档 API 未提供该操作；前端未展示该动作。

## 视觉验证

- 已尝试使用本地 Vite（`http://[::1]:5173`）和 Edge headless 生成 1440×900 截图；当前环境没有写出 PNG，不能标记为通过。
- 1024×768、768×1024、390×844：未实测。
