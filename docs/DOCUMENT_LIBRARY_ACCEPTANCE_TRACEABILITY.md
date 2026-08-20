# 文档库页面重构验收追踪

> 规格来源：`文档库页面设计融合实施提示词-2.md` 与用户提供的文档库预览图。
>
> 本文件只记录实际实现与验证证据；未执行的验证不得标为通过。

## 能力矩阵

| 能力 | 后端 | 前端策略 | 分类 |
|---|---|---|---|
| 全库文档统计 | `GET /api/v1/documents/statistics` | 统计卡从真实聚合读取（全部/可用/处理中/需处理） | LIVE |
| 二级导航 | — | 一级「文档与知识」下展开「知识库 / 文档库」 | LIVE |
| 常驻来源树 | `knowledge_source_id`、知识来源列表 | 左侧来源树：全部文档 / 最近使用 / 本地文件夹 / Obsidian Vault；图标为内联 SVG | LIVE |
| 来源浏览与筛选 | `knowledge_source_id`、知识来源列表 | URL 恢复（`sourceId`）、来源树选中 | LIVE |
| 文件名/路径搜索 | `mode=document&query=` | 主搜索带 | LIVE |
| 文件类型/三态/稳定排序 | `file_type`、`health_status`、`sort_by`、`sort_order` | 轻量筛选带（文件类型/处理状态/排序/清除） | LIVE |
| 统一修复 | `POST /documents/{id}/repair` + durable task | 提交中禁用、刷新状态 | LIVE |
| 批量建立索引 | `POST /documents/batch-index` | 按选择显示 | LIVE |
| 临时文档详情 | 既有详情能力 | 可访问 Drawer（ESC / 遮罩 / 焦点循环 / 背景锁） | LIVE |
| 正文内容搜索与定位 | `mode=content&query=`（后端仍保留） | **已按用户要求从文档库 UI 移除**，不在文档库展示 | DEFERRED |
| 批量重新处理 | `POST /documents/batch-repair` | 仅在真实接口与 UI 交互完成后显示 | LIVE |
| 删除知识来源/源文件 | 不属于文档库边界 | 不展示 | DEFERRED |

## 验收映射

| AC | 主要证据 | 当前状态 |
|---|---|---|
| AC-01 | `tests/modules/document/test_query_contract_api.py` + `/documents/statistics` 实例探针 | 通过（后端） |
| AC-02–AC-07 | `DocumentManager.test.ts`、`DocumentScopeNav.test.ts` | 通过（前端） |
| AC-08–AC-11 | `tests/modules/document/test_query_contract_api.py`、`DocumentTable.test.ts`、`DocumentDetailsDrawer.test.ts` | 通过（前后端） |
| AC-12–AC-13 | `tests/modules/document/test_api.py::test_repair_submission_is_idempotent` + `DocumentManager.test.ts` 修复链路 | 通过（前后端） |
| AC-14–AC-15 | 正文定位已从文档库 UI 移除；后端内容定位接口保留并有契约测试 | 前端按用户要求 DEFERRED；后端通过 |
| AC-16–AC-20 | `DocumentDetailsDrawer.test.ts`（ESC/遮罩/dialog）、来源树与表格键盘交互 | 通过（前端） |
| AC-21 | 1440 桌面真实浏览器截图 + DOM 列对齐测量；表格对齐（处理状态/操作列）已验证 | 通过（视觉） |
| AC-22–AC-25 | 前端 `typecheck`、`eslint`(0 error)、`vitest`(125)、`build` 全绿 | 通过（前端全量） |

## 已执行验证

### 后端
- `pytest -q`：606 passed，13 skipped，1 条 Starlette/httpx 弃用警告。
- `mypy app --ignore-missing-imports`：353 source files，无问题。
- `alembic check`：无新的升级操作；`alembic current`：`n2o3p4q5r6s7 (head)`。
- `ruff check app/modules/document tests/modules/document`：通过。
- 全仓 `ruff check app tests alembic` 仍有 4 条历史 migration 的 import 排序问题；历史 migration 受“不修改已发布 revision”约束，本轮未改动。

### 前端（本轮重写）
- `vue-tsc` 类型检查：通过。
- `eslint . --ext .ts,.vue`：0 error（1598 条 warning 均为全库既有 `vue/max-attributes-per-line` 风格，非本轮引入；另清理 3 处历史未用变量）。
- `vitest run`：50 files / 125 tests 通过。
- `vite build`：通过（仅既有 `DocumentDetailView` >500kB 分块提示，非阻断）。
- 真实浏览器（127.0.0.1:5174，连接 8011 后端）：默认加载真实来源「文献」12 篇；统计 13 全库；来源树显示最近使用/本地文件夹/Obsidian 分组与 SVG 图标；工具带为「主搜索带 + 轻量筛选带」；表格表头与内容列 DOM 实测完全对齐（处理状态、操作列）。

## 本轮前端文件
- `frontend/src/components/layout/AppSidebar.vue`：一级「文档与知识」下二级「知识库 / 文档库」。
- `frontend/src/components/document/DocumentManager.vue`：去掉「全部文档/按来源浏览」胶囊与正文定位，来源树常驻，计数口径统一。
- `frontend/src/components/document/DocumentScopeNav.vue`：SVG 图标、最近使用（localStorage 持久化）、分组去杂乱（删除“N 个需处理”红字）。
- `frontend/src/components/document/DocumentFilters.vue`：删除「文档/正文定位」分段，收敛为主搜索带 + 轻量筛选带。
- `frontend/src/components/document/DocumentTable.vue`：均衡列宽、操作列左对齐（修复按钮对齐表头）。
- `frontend/src/components/document/DocumentDetailsDrawer.vue` + `.test.ts`：可访问临时详情抽屉。
- 测试：`DocumentManager.test.ts`、`DocumentScopeNav.test.ts` 适配新结构。
