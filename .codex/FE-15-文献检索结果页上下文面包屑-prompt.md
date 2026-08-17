# FE-15：素问｜文献检索结果页的上下文面包屑导航

## 0. 唯一代码执行目录

**`H:\AI_project\rag_medicine`**。先确认 `.git`、`frontend/package.json`、`app/` 存在；执行 `git status --short --branch`；保留全部既有修改，禁止 `reset`、`checkout`、`clean`、`stash`、覆盖不相关变更。不提交、不推送。

## 1. 必读文件（已核实存在，全部读完再动手）

1. `AGENTS.md`
2. `docs/CODE_STANDARDS.md`（V2.0 共 42 条，本任务全部适用）
3. `frontend/src/views/LiteratureSearch/ResultsView.vue`（主修改对象）
4. `frontend/src/views/LiteratureSearch/History.vue`
5. `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
6. `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`
7. `frontend/src/views/LiteratureSearch/LiteratureWorkspaceTabs.vue`
8. `frontend/src/components/layout/Breadcrumbs.vue`（**全局面包屑，需支持动态解析，见 §3**）
9. `frontend/src/router/route-meta.ts`（**面包屑定义，需扩展**）
10. `frontend/src/router/index.ts`（只读）
11. `frontend/src/styles/tokens.css`（视觉 token 唯一来源）
12. 文献检索相关 API 类型与现有 Vitest 测试（`find frontend/src -name '*.test.ts'` 确认，全部读完）

> **注意**：原提示词中的 `vue-best-practices`、`acceptance-testing` 在仓库中**不存在**，已替换为上列真实文件；Vue 工程规范见 `docs/CODE_STANDARDS.md` 与现有组件风格。

## 2. 产品目标

当前从"历史记录"点击"查看结果"后进入独立结果页。该页目前有单独的"← 返回历史记录"按钮（`ResultsView.vue` 现有 `back-button`），且顶部面包屑无法表达页面来源。

保留独立结果页，将返回逻辑统一到面包屑：

1. 从历史记录点击"查看结果"进入结果页时，面包屑为：**文献检索 / 历史记录 / 检索结果**
2. "文献检索"可点击，返回文献检索工作区（`/literature-search`，默认 Tab）
3. "历史记录"可点击，返回历史记录列表（`/literature-search?tab=history`）
4. "检索结果"为当前页文本，不可点击，带 `aria-current="page"`
5. **移除结果页内单独的"← 返回历史记录"按钮**（`ResultsView.vue` 的 `back-button` 及其 `returnToSearchHistory` 逻辑），避免同一返回动作重复
6. 从"检索中心"完成检索后进入、或直接 URL 打开结果页时，**不得伪造"历史记录"来源**，面包屑为：**文献检索 / 结果展示**（"结果展示"为当前页，不可点击）
7. 结果页标题保持"检索结果"；任务编号（如"任务 #11"）不作为大标题核心，若保留仅作低干扰辅助信息，且必须来自真实服务端返回（`resultId`/`taskId` 路由参数）
8. 浏览器后退/前进语义不破坏。URL 直达、刷新、复制链接均稳定：
   - 从历史记录进入时使用最小来源参数 `?from=history`；
   - 参数缺失、无效、被手动修改时，安全降级为"文献检索 / 结果展示"；
   - **不依赖仅存在于内存中的前端状态**判断来源。
9. 不修改 `AppSidebar`、`AppTopbar`、一级导航、导航文案/顺序；不修改后端检索、结果、收藏、已读、全文等业务逻辑；不新增不必要依赖；禁止 `v-html`。

## 3. 实现方案（关键设计决策，先读懂再写码）

### 3.1 面包屑动态化的正确路径

全站面包屑由 `AppTopbar` 内的全局 `Breadcrumbs.vue` 渲染，数据来自 `route-meta.ts` 的静态 `breadcrumbByPath`。**结果页的"来源上下文"（历史记录 vs 结果展示）依赖路由 query，静态表无法表达**，因此必须小范围扩展：

- `route-meta.ts`：面包屑定义支持 **`string[]` 或 `(route) => string[]` 函数**两种形态（向后兼容，其余路由继续用静态数组）：
  - 为 `/literature-search/results` 提供动态解析函数：`route.query.from === "history"` → `["文献检索", "历史记录", "检索结果"]`；否则 → `["文献检索", "结果展示"]`；
  - **禁止**改动其他路径的面包屑文案与顺序。
- `Breadcrumbs.vue`：读取 `route.meta.breadcrumb` 时先判断类型——函数则调用得到数组，数组则直接使用；渲染逻辑不变（前序项可点击、末项 `aria-current="page"`、分隔符、样式 token 均保持）。
- 可选：若你判断局部组件更干净（页面内渲染上下文面包屑并隐藏全局），必须说明如何在不改 `AppTopbar` 的前提下隐藏全局面包屑；**默认采用扩展全局组件方案**（单一来源、无重复渲染）。

### 3.2 来源上下文参数

- `HistoryTableRow.vue` 的"查看结果"`RouterLink` 增加 `&from=history`：
  ```ts
  :to="`/literature-search/results/${task.latest_result_id}?task=${task.id}&from=history`"
  ```
- `ResultsView.vue` 解析来源：只读 `route.query.from`，合法值仅 `"history"`，其余一律视为无来源（降级"结果展示"）；不把内存状态当作来源依据。

### 3.3 移除重复返回按钮

- 删除 `ResultsView.vue` 的 `back-button` 按钮与 `returnToSearchHistory` 函数；
- 返回能力完全由面包屑承担（"文献检索"→ 工作区、"历史记录"→ 历史记录列表）；
- 相关旧测试若断言该按钮存在，**更新断言为新意图**（按钮不存在 + 面包屑行为正确），不删除整个测试。

### 3.4 标题降级

- 大标题保持"检索结果"；任务编号改为辅助信息（如标题下小字"任务 #N"），数据来自真实路由参数 `resultId`/`taskId`，不得硬编码或伪造。

## 4. 组件图与数据流（先在 commentary 输出，再写码）

```text
HistoryTableRow
  └─ RouterLink → /literature-search/results/{resultId}?task={taskId}&from=history
ResultsView
  └─ 读取 route.query: resultId / taskId / from（来源解析放 ResultsView 或专属 composable）
  └─ 页面标题：检索结果 + 辅助任务编号
route-meta.ts
  └─ /literature-search/results 的动态 breadcrumb 函数（from=history → 三段，否则两段）
Breadcrumbs.vue（全局，扩展后）
  └─ 函数式 breadcrumb 解析 → 渲染链接 + aria-current="page"
```

## 5. 代码规范强制约束（docs/CODE_STANDARDS.md 42 条落地为可执行检查项）

1. **类型注解**（第 6/7 条）：新增 props/emits/函数参数返回值显式 TS 类型；禁止隐式 `any`（尤其 breadcrumb 函数类型：`string[] | ((route: RouteLocationNormalized) => string[])`）。
2. **语义命名**（第 5/8 条）：函数动词+宾语（`resolveResultBreadcrumb`、`parseResultOrigin`），布尔 `is/has` 前缀。
3. **抽常量消魔法数字**（第 9 条）：`from` 参数值、面包屑标签等抽具名常量（如 `const ORIGIN_HISTORY = "history"`），不散落字符串。
4. **中文注释讲设计意图**（第 10/11 条）：复杂逻辑写"为什么"（如：为何来源只用 query 不信任内存状态；为何面包屑函数化保持向后兼容）；禁止行为复述。
5. **单文件单职责**（第 1 条）：来源解析在 `ResultsView`（或专属 composable）；面包屑渲染逻辑在 `Breadcrumbs.vue`；定义在 `route-meta.ts`。
6. **禁空捕获**（第 19/21 条）：新增 try/catch 必须指定异常类型并处理。
7. **禁硬编码色值**（frontend-ui-engineering）：新 CSS 一律 `tokens.css` 语义变量；禁止新增 `var(--x, #hex)` fallback 或裸 hex（现有文件 fallback 是历史遗留，不得复制、不得顺手修）。
8. **界面文案与可访问性**（frontend-design / web-design-guidelines）：
   - 面包屑链接键盘可达、可见 `:focus-visible`；
   - 当前项 `aria-current="page"`，非链接纯文本；
   - 不使用 `v-html`；不新增无意义文案。

## 6. 测试要求（测试先行，RED → GREEN）

按验收标准逐条先写失败测试，再实现至通过：

- **AC-1**：Given 历史记录一条真实任务，When 点击"查看结果"，Then 路由携带 `from=history`，结果页面包屑为"文献检索 / 历史记录 / 检索结果"。
- **AC-2**：Given 从历史记录进入结果页，When 点击面包屑"历史记录"，Then 返回历史记录列表（`/literature-search?tab=history`）；And 页面内不存在"← 返回历史记录"重复按钮。
- **AC-3**：Given 从检索中心创建任务后进入结果页，或直达结果 URL，Then 面包屑为"文献检索 / 结果展示"；And 不显示"历史记录"。
- **AC-4**：Given URL 来源参数无效/缺失，Then 安全降级"结果展示"；And 不报错、不生成错误链接。
- **AC-5**：Given 结果页，Then 当前面包屑项不可点击且有 `aria-current="page"`；And 前序面包屑链接可键盘访问。

技术要点：

- 路由跳转/面包屑断言用**真实 router 实例**（`createRouter` + `createMemoryHistory`）+ `flushPromises`；jsdom 下不要用 `wrapper.vm.$router` 假路由；
- 旧测试若断言 `back-button` 存在，更新为新意图（按钮移除 + 面包屑正确），**不删除有效断言**；
- 更新 `route-meta.ts` 后，确认其他路由面包屑相关测试不回归（静态数组行为不变）。

## 7. 文件边界（严格）

### 允许修改（白名单）

- `frontend/src/views/LiteratureSearch/ResultsView.vue`
- `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
- `frontend/src/views/LiteratureSearch/History.vue`（仅在确需时，如来源相关联动）
- `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`（仅在确需时，如 `?tab=history` 深链已存在则不必改）
- `frontend/src/components/layout/Breadcrumbs.vue`（动态 breadcrumb 解析；**不得改动**其他页面渲染行为）
- `frontend/src/router/route-meta.ts`（新增动态面包屑能力；不得改动其他路径文案）
- 以上文件对应的 Vitest 测试文件（新增/更新）

### 禁止

- 后端、数据库、迁移、`frontend/src/api/*` 契约层；
- `frontend/src/router/index.ts`（路由表本身）、`features.ts`、`AppSidebar.vue`、`AppTopbar.vue`、`package.json`、`frontend/src/styles/tokens.css`；
- 其他页面视图文件；任何 `git reset / restore / checkout -- / clean / stash`；提交、push。

### 工作区安全

以下文件当前可能有**其他任务/并行会话的未提交改动**（以 `git status --short` 为准）：`Breadcrumbs.vue`、`route-meta.ts`、`History.vue`、`LiteratureSearchView.vue`、`ResultsView.vue`。**必须增量修改**：只改本任务相关区块，保留他人语义与格式；改动前先 `git diff` 查看现有未提交改动；禁止整文件重写、禁止格式化他人改动、禁止"顺手清理"。

## 8. 必须真实执行的验证（逐条运行并贴原始输出）

```bash
cd H:\AI_project\rag_medicine\frontend
npm run typecheck
npm test -- --run
npm run build
```

```bash
cd H:\AI_project\rag_medicine
git diff --check
git status --short --branch
git diff --stat -- frontend/src/views/LiteratureSearch frontend/src/components/layout/Breadcrumbs.vue frontend/src/router/route-meta.ts
```

**越权核对（必做）**：`git diff --stat HEAD` 确认全部改动在第 7 节白名单内；发现白名单外文件被改，**立即停止并报告**，不得自行回退他人文件（确认是本轮误改且可安全回退时，用 `git checkout HEAD -- <file>` 回退并说明）。

浏览器实测（若前端已运行 `http://localhost:5173`，否则跳过并说明；有 Playwright 则优先）：

1. 历史记录点击"查看结果" → 验证三段面包屑"文献检索 / 历史记录 / 检索结果"；
2. 点击"历史记录" → 返回历史记录列表；
3. 确认结果页**无"← 返回历史记录"重复按钮**；
4. 直达结果 URL（无 `from=history`）→ 两段面包屑"文献检索 / 结果展示"；
5. 手动改 `from=xxx` → 降级"结果展示"不报错；
6. 键盘 Tab 遍历面包屑 → 前序链接可聚焦、当前项不可聚焦；
7. 其他页面（文档详情、论文分析等）面包屑无回归。

若不能浏览器实测，明确标注【未实测】与原因。

## 9. 最终报告格式

1. 改动文件及职责（逐文件）
2. 面包屑动态化设计说明（route-meta 函数形态 + Breadcrumbs 兼容处理）
3. AC-1 至 AC-5 的测试证据（RED→GREEN 过程与最终结果）
4. 实际执行命令与原始输出
5. `git diff --stat` 与 `git status --short --branch`
6. 浏览器实测结果（含降级、键盘可达、无重复按钮）
7. 明确说明未修改：侧栏、顶栏、一级导航、后端检索逻辑
8. 已知限制【未实测】

完成后停止，不提交，不 push，不继续其他页面。
