# FE-13：文献检索「结果页 → 历史记录」返回导航修复

## 0. 唯一代码执行目录

**`H:\AI_project\rag_medicine`**（开始前先 `cd H:\AI_project\rag_medicine` 并执行 `git status --short` 确认工作区状态；不得在其他目录写入任何代码）。

## 1. 任务背景（用户实测问题）

用户在文献检索**历史记录**页（`/literature-search` 内嵌"历史记录"Tab）点击某行"查看结果"，跳到独立路由：

```text
/literature-search/results/{resultId}?task={taskId}
```

跳转后页面顶部**面包屑只有"文献检索 / 检索结果"，没有任何"返回上一个页面（历史记录）"的按钮或链接**，用户无法便捷回到历史记录。

请先复现确认当前行为（含已有"← 返回"按钮是否存在/是否有效）：

- 打开 `http://localhost:5173/literature-search` → 切到"历史记录"Tab → 点某行"查看结果" → 观察结果页顶部是否有返回入口；
- 若有"← 返回"按钮，点击后确认落点（预期是回到历史记录 Tab；实际可能回到"检索中心"Tab 或无效）。

## 2. 必读文件（按顺序）

1. `docs/CODE_STANDARDS.md`
2. `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`
3. `frontend/src/views/LiteratureSearch/LiteratureWorkspaceTabs.vue`
4. `frontend/src/views/LiteratureSearch/History.vue`
5. `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
6. `frontend/src/views/LiteratureSearch/ResultsView.vue`
7. `frontend/src/components/layout/Breadcrumbs.vue`
8. `frontend/src/components/layout/AppTopbar.vue`
9. `frontend/src/router/route-meta.ts`
10. 以上文件对应的既有测试（`frontend/src/views/LiteratureSearch/*.test.ts` 等，用 `find frontend/src -name '*.test.ts'` 确认实际文件）

## 3. 根因（已由任务外分析确认，供参考，仍需你在代码中核实）

1. **Tab 状态不随 URL 同步**：`LiteratureSearchView.vue` 的 `activeTab` 是内存 `shallowRef`（`"center" | "results" | "history" | "recommendations"`），初始化固定为 `"center"`，切换只改内存、不写 `route.query`。因此从历史记录 Tab 跳到结果页再返回时，组件重新挂载，Tab 回到"检索中心"，历史记录上下文丢失。
2. **结果页返回逻辑不完整**：`ResultsView.vue` 的 `returnToPreviousPage()` 仅 `window.history.state?.back` 存在时 `router.back()`，否则 `router.push("/literature-search")`；二者都无法保证落在"历史记录"Tab。
3. **面包屑无可点击回退**：`Breadcrumbs.vue` 的面包屑链接白名单只有"文档与知识/文档库"，"文献检索"是纯文本；结果页面包屑"文献检索 / 检索结果"整体不可点击，无返回语义。

## 4. 目标行为

1. **结果页必须有明确的返回入口**，让用户回到"历史记录"Tab：
   - 优先复用/增强结果页 header 的"← 返回"按钮（若已有）；若不存在则新增；
   - 若可行且不影响其他页面，在结果页面包屑处提供回退（可点击的"文献检索"链接或"← 返回"按钮），用户原话是"面包屑没有回退按钮"，请尽量让面包屑本身具备返回能力；
   - 按钮/链接必须有清晰 `aria-label`（如"返回检索历史"）和可见 `:focus-visible`。
2. **返回后必须落在"历史记录"Tab**（不是检索中心）：
   - 实现方案建议（二选一或组合，代码以真实结构为准）：
     - **A（推荐，根治）**：`LiteratureSearchView` 的 `activeTab` 与 URL `?tab=` 同步——初始化读 `route.query.tab`（合法值 `center|results|history|recommendations`，非法/缺失回退 `center`），切换时 `router.replace` 更新 query；结果页返回目标改为 `/literature-search?tab=history`；
     - **B（兜底）**：`HistoryTableRow.vue` 的"查看结果"跳转携带来源标记（如 `&from=history`），`ResultsView.returnToPreviousPage()` 优先 `router.back()`，无历史时按来源标记返回 `/literature-search?tab=history`，否则回 `/literature-search`。
   - 两种方案都要保证：直接访问结果页 URL、从检索中心"结果展示"进入、从历史记录进入三种来源的返回行为合理（从历史记录进入 → 回历史记录；其他来源 → 回工作区对应 Tab 或默认 Tab）。
3. **不得破坏**：
   - 历史记录 Tab 的分组展示、版本变化、重跑、分页行为；
   - 检索中心 PICO 构建/检索式构建/执行检索流程；
   - 结果页的筛选、排序、分页、保存、标记已读、去重、阅读顺序；
   - 其他页面（文档与知识、论文研究等）的面包屑显示。
4. **面包屑改动要克制**：`Breadcrumbs.vue` 是全局组件，若在其中加"文献检索"链接或回退逻辑，必须验证 `/sources`、`/documents`、`/analysis`、`/chat` 等所有既有页面面包屑无回归；优先在结果页局部解决，其次才动全局组件。

## 5. 文件边界（严格）

### 允许修改（白名单，仅限确实需要）

- `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`
- `frontend/src/views/LiteratureSearch/LiteratureWorkspaceTabs.vue`
- `frontend/src/views/LiteratureSearch/History.vue`
- `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
- `frontend/src/views/LiteratureSearch/ResultsView.vue`
- `frontend/src/components/layout/Breadcrumbs.vue`（仅在局部方案不足时，且必须验证全局回归）
- `frontend/src/router/route-meta.ts`（仅在确需调整结果页面包屑定义时，且不得改动其他路径的面包屑）
- 以上文件对应的 Vitest 测试文件（新增/更新）

### 禁止

- 后端、数据库、迁移、`frontend/src/api/*` 契约层；
- `frontend/src/router/index.ts`（路由表本身）、`features.ts`、`AppSidebar.vue`、`AppTopbar.vue`、`package.json`、tokens 全局样式；
- 其他页面（论文研究、文档与知识、推荐阅读等）；
- 任何 `git reset / restore / checkout -- / clean / stash`；
- 提交、push。

### 工作区安全（重要）

以下文件当前在工作区有**其他任务/并行会话的未提交改动**（`git status --short` 为 `M`）：

```text
frontend/src/components/layout/Breadcrumbs.vue
frontend/src/router/route-meta.ts
frontend/src/views/LiteratureSearch/History.vue
frontend/src/views/LiteratureSearch/LiteratureSearchView.vue
frontend/src/views/LiteratureSearch/ResultsView.vue
```

**必须增量修改**：只改与本任务相关的函数/区块，保留他人的语义和格式；禁止整文件重写、禁止格式化他人改动、禁止"顺手清理"。改动前先 `git diff` 查看每个文件的现有未提交改动，避免覆盖。

## 6. 测试要求

为本次修复补齐/更新 Vitest 覆盖，至少：

1. `/literature-search?tab=history` 直接访问时激活"历史记录"Tab（若采用方案 A）；
2. 从历史记录进入结果页后，返回按钮/链接触发回到 `?tab=history`（按实际实现断言路由或组件状态）；
3. 结果页返回入口存在且可点击（有 `aria-label`）；
4. 已有文献检索相关测试全部保持通过（不得删除或弱化既有断言）；
5. 若改 `Breadcrumbs.vue`，补充/更新其测试确认其他页面面包屑无回归。

## 7. 必须真实执行的验证（结束前逐条运行并贴原始输出）

```bash
cd H:\AI_project\rag_medicine\frontend
npm run typecheck
npm test -- --run
npm run build
```

```bash
cd H:\AI_project\rag_medicine
git diff --check
git status --short
git diff --stat -- frontend/src/views/LiteratureSearch frontend/src/components/layout/Breadcrumbs.vue frontend/src/router/route-meta.ts
```

浏览器实测（若前端已运行 `http://localhost:5173`，否则可跳过并说明）：

1. `/literature-search` → 历史记录 Tab → 点"查看结果" → 结果页出现返回入口；
2. 点击返回 → 落在历史记录 Tab（真实 URL 应含 `?tab=history` 或等价状态）；
3. 直接访问 `/literature-search/results/{id}?task={id}` → 返回行为合理；
4. 检查 `/sources`、`/documents`、`/analysis` 面包屑无回归（若改了 Breadcrumbs）。

任何命令失败：贴完整失败原因并停止，不得声称通过。

## 8. 最终报告格式

1. 复现确认（进入结果页时返回入口的现状）
2. 根因核实（与你分析的差异或一致）
3. 采用方案（A/B/组合）与理由
4. 修改文件与每个文件的具体改动
5. 真实数据/边界说明（无伪造）
6. 实际运行命令与原始结果
7. 浏览器实测结果
8. 本轮刻意未触碰的文件
9. 已知限制【未实测】

完成后停止，不提交，不 push，不继续其他页面。
