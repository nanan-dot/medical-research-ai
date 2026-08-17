# FE-17｜文档库桌面工作台：高保真界面重构执行提示词

> **任务性质**：前端视觉与信息层级重构。以用户提供的目标设计图为视觉目标，重构 `/documents` 的「文档库」工作台；**不得伪造业务数据、不得改变知识库/文档库职责边界、不得恢复直接上传入口**。
>
> **真实项目目录唯一**：`H:\AI_project\rag_medicine`
>
> **工作区当前很脏，存在其他并行会话改动。必须增量修改并保留全部现有未提交内容。**

---

## 0. 开始前必做：读取规范与真实现状

在写任何代码前，依次读取：

1. `AGENTS.md`
2. `docs/CODE_STANDARDS.md`（V2.0、42 条，最高规范）
3. `docs/design/知识库与文档库_页面设计说明.md`
4. `docs/design/单篇文档导入_归属知识库_设计说明.md`
5. 当前代码及测试：
   - `frontend/src/views/Documents/DocumentsView.vue`
   - `frontend/src/components/document/DocumentManager.vue`
   - `frontend/src/components/document/DocumentWorkspaceSummary.vue`
   - `frontend/src/components/document/DocumentScopeNav.vue`
   - `frontend/src/components/document/DocumentNavigationPanel.vue`
   - `frontend/src/components/document/DocumentNavigationResults.vue`
   - `frontend/src/components/document/DocumentFilters.vue`
   - `frontend/src/components/document/DocumentTable.vue`
   - `frontend/src/components/document/DocumentInspector.vue`
   - `frontend/src/components/document/DocumentManager.test.ts`
   - `frontend/src/components/document/DocumentScopeNav.test.ts`
   - `frontend/src/components/document/DocumentInspector.test.ts`
   - `frontend/src/api/documents.ts`
   - `frontend/src/api/knowledgeSources.ts`
   - `frontend/src/composables/useDocuments.ts`
   - `frontend/src/composables/useKnowledgeSources.ts`
   - `frontend/src/composables/useDocumentNavigation.ts`
   - `frontend/src/styles/tokens.css`

**Vue 要求**：修改 Vue 文件前，读取并遵循项目可用的 Vue 相关 skill / 参考规范；使用 Vue 3 Composition API、明确 props/emits、单文件单职责、真实状态流。

---

## 1. 目标与不可动的产品边界

### 1.1 产品职责（不可违反）

- **知识库**：管理资料来源/资料文件夹、导入、同步、启停、统计。
- **文档库**：浏览和处理已归属文件夹的具体文档；支持筛选、解析、索引、失败重试、详情、预览、AI 资料导航。
- 文档必须保留并显示：**所属知识源 + 相对路径**。
- 文档库**不得**出现：`上传 PDF`、直接上传文档、自动创建「上传文档 / 临时文件 / 未知来源」等隐式来源的入口。
- 目标图中的“文件总数 12 / 已解析 8 / 已索引 6 / 待处理 4 / 异常 1”、文档名称、路径、页数、段落数、日期均仅为**视觉参考**；**绝不能硬编码为运行时数据或假设真实状态**。

### 1.2 接口与路由边界

- 保留现有 `sourceId` URL 筛选逻辑：`/documents?sourceId=<id>`。
- 知识库点击“查看文档”后，文档库仍需准确限定到对应知识源。
- 复用现有 API/composable；**不新增 mock，不伪造解析/索引/AI 检索结果**。
- 不改后端、数据库、迁移、API 契约。
- 不改全局路由、`features.ts`、`AppSidebar.vue`、`AppTopbar.vue`、`AppShell.vue`、`Breadcrumbs.vue`。
- 不恢复 `DocumentUploadPanel` 或 `useDocumentUpload` 到 `DocumentManager`。

---

## 2. 现有页面与目标图的关键差异（必须解决）

### 当前页问题

当前 `/documents` 内容区：
- 顶部只显示“全部文档/文件总数 16”的简化摘要；缺少工作台式多维处理统计。
- 中部是较松散的「AI 资料定位 + 文件名筛选 + 下拉筛选」组合，层级不够清楚。
- 左栏把“管理资料”作为文字链接，资料范围和文件夹树的视觉层级较弱。
- 文档表格不够紧凑，文件类型、路径、解析、索引、更新时间和操作的扫描关系弱。
- 右侧当前为“文档检查器”空态，缺少目标图的文件详情信息层级；选择文档时需要更清晰的来源路径、文件元数据、处理状态、错误/提示。
- 多处 CSS 仍使用单行压缩写法，需**仅在触及文件内**按项目现有样式适度整理，不能进行全项目格式化。

### 目标图的核心语言（不是照抄假数据）

目标桌面工作台（宽屏）应体现：

```
[页面既有全局壳保持不变]

[处理统计带：文件总数 | 已解析 | 已索引 | 待处理 | 异常]

┌────────资料范围────────┬──────────────主工作区───────────────┬──────文档详情──────┐
│ 全部文档 + 总数         │ AI 在当前资料中定位内容… [Ctrl+K]     │ 已选文件：类型图标   │
│ 知识文件夹标题 + 新增符号 │ [解析状态] [索引状态] [证据就绪] [重置] │ 来源路径 + 复制       │
│ 可见知识源 + 文件数徽标   │ 紧凑、可扫描、行选中态的文档表格         │ 文件信息               │
│                          │ 分页/每页条数                            │ 处理状态/错误与提示    │
└────────────────────────┴────────────────────────────────────┴─────────────────────┘
```

视觉气质：**浅灰蓝画布、白色工作面、深海军蓝文本、学术蓝主强调、克制边线、约 8px 圆角、弱阴影或无阴影**。不得加入紫色渐变、玻璃拟态、营销 Hero、假图表、过度 Card 堆叠。

---

## 3. 具体实施要求

### A. 页面容器与统计带

优先改造 `DocumentWorkspaceSummary.vue`（如该组件的职责不适合，可新增一个专用展示组件，但不要把所有逻辑塞回 `DocumentManager.vue`）：

1. 在主三栏工作区**上方**增加一条紧凑的「文档处理统计带」。
2. 仅用真实可获得数据：
   - 文件总数：当前范围统计/当前列表 total；
   - 已解析、已索引、待处理、异常：优先使用现有 `KnowledgeSource.stats` 的真实字段；
   - 如果“全部文档”范围没有现有后端聚合字段能够准确给出某项：
     - 不计算或猜测；
     - 可以显示 `—` 并加不误导的说明，或只呈现接口真实可得的统计；
     - 不得从当前分页列表推断“全库准确总数”。
3. 使用文本标签 + 数字 + 可访问的状态文字；绿/蓝/红状态不得只依靠颜色。
4. 宽屏横向排列；小屏可换行或降为 2 列，但不得压坏布局。
5. 保持页面只存在一个 `h1`（全局页标题由现有结构负责时，不额外制造重复 h1）。

### B. 左侧“资料范围”

改造 `DocumentScopeNav.vue`：

1. 保留真实的“全部文档”与 `sources` 知识源列表，显示每个知识源真实文件数量徽标。
2. 将其布局调整为目标图所示的清晰层级：
   - `资料范围` 标题；
   - 高亮当前“全部文档”或当前选中知识源；
   - `知识文件夹`/`知识库文件夹`分组标题；
   - 文件夹图标、来源名称、数量徽标。
3. 若有“管理资料”/“添加资料”跳转，保留为低强调的辅助操作，不得把导入/上传功能塞回文档库。
4. `sourceId` 选择行为必须保持：点击来源更新 URL，列表与统计切换到正确范围。
5. 目标图中有“+”图标仅代表进入知识库管理/导入资料的导航入口；若实现该入口，必须跳转既有知识库页面，**不能在文档库创建来源**。

### C. 主工作区：AI 资料定位与筛选

保持现有 `DocumentNavigationPanel` / `DocumentNavigationResults` 的真实调用链，不新增平行假搜索流程。

1. 将 AI 资料导航做成目标图第一行的“上下文定位条”：
   - 左侧 `AI` 小标识；
   - placeholder 使用真实语义：`在当前资料中定位内容…`；
   - 当前范围由已有 sourceId 控制；
   - 右侧可显示仅为键盘提示的 `Ctrl + K` 胶囊，但**只有当快捷键确实已实现时才能绑定行为**；未实现时仅视觉提示也必须不宣称可用。优先不实现全局快捷键，避免超范围。
2. 保持真实 AI 导航结果区域。无结果、接口失败、加载中必须有真实状态；不得伪造命中文摘/页码。
3. `DocumentFilters.vue` 调整为紧凑、一行可扫描的筛选栏：
   - 解析状态；
   - 索引状态；
   - 现有“仅显示可用于证据问答”；
   - 明确的重置/清除筛选动作（只清现有 filter 状态）。
4. 文件名筛选应保持现有真实 API 参数；若需要将输入框视觉放到第一行或第二行，按真实调用节流/提交语义实现，不要在每个输入字符创建不受控请求。

### D. 文档表格：目标图密度与真实状态表达

改造 `DocumentTable.vue`，只调整呈现层，保留现有解析/索引/重试/详情/选中事件。

1. 列顺序与目标语义对齐：勾选｜文档｜解析｜索引｜更新时间｜操作。
2. 文档列：
   - 文件类型使用现有真实文件名后缀判断展示图标/标签；不伪称文件预览能力；
   - 第一行文件名，第二行显示 `所属知识源 / 相对路径`；
   - 所属知识源名称来自真实 `sourceNames`。
3. 解析列：显示真实 `parse_status`；若已有页数/进度等真实字段才显示，否则不要渲染目标图中的“128 页”“42%”。
4. 索引列：显示真实 `index_status`；若无真实段落/切片数，不展示“15,432 段”等假指标。
5. 状态应有文字与图标/圆点：
   - 成功/已索引：成功语义；
   - 等待/待索引：中性；
   - 处理中：进行中；
   - 失败/索引过期：警示并保留错误处理入口。
6. 当前选中行要有克制的浅蓝背景/左侧状态，不可只靠 checkbox 表示选中。
7. “更多操作”可保留为无障碍 button 或现有明确操作；不能用不可键盘操作的纯 `div` / `…` 装饰。
8. 桌面宽度不够时，表格允许横向滚动或隐藏低优先级元信息；不能挤压文本到不可读。

### E. 右侧文档详情面板

改造 `DocumentInspector.vue`：

1. 宽屏下常驻右栏；1024px 以下改为可展开/收起区或现有响应式模式。
2. **未选中文档**：展示“文档详情”+ 当前范围摘要/选择提示，不显示伪造文档元数据。
3. **选中文档**：参照目标图的真实信息层级：
   - 文件类型图标与真实文件名；
   - 来源路径（知识源名称 + 相对路径）；
   - 文件信息：真实可得的类型、大小、更新时间；没有的字段显示 `—`，不可造页数/创建时间；
   - 处理状态：真实 parse/index 状态、真实 error_message（如有）；
   - 错误与提示：失败时给当前真实错误原因与既有重试路径；无错误时只显示真实的状态正常说明。
4. 如果已有文档详情路由，保留“查看详情/打开文档详情”真实链接；不可新增空操作。
5. 不要把本地绝对路径暴露到不该显示的区域；来源展示使用知识源名/相对路径，遵循已有产品边界。

### F. 布局与响应式

1. 目标桌面断点建议 `>= 1200px`：左栏约 220–240px，中部自适应，右栏约 300–330px。
2. 1024–1199px：可将右栏折叠为可展开区；保留左栏与中部阅读体验。
3. `<1024px`：单列有序堆叠，资料范围 → 主区 → 详情；不得出现内容重叠或横向页面溢出。
4. 320px / 768px / 1024px / 1440px 都需检查。
5. 使用 `tokens.css` 现有语义 token；新 token 只有在多个组件复用且现有 token 无法表达时才允许新增，并说明原因。

---

## 4. 文件范围与变更纪律

### 优先白名单

仅在确有必要时修改以下前端文件：

- `frontend/src/views/Documents/DocumentsView.vue`
- `frontend/src/components/document/DocumentManager.vue`
- `frontend/src/components/document/DocumentWorkspaceSummary.vue`
- `frontend/src/components/document/DocumentScopeNav.vue`
- `frontend/src/components/document/DocumentNavigationPanel.vue`
- `frontend/src/components/document/DocumentNavigationResults.vue`
- `frontend/src/components/document/DocumentFilters.vue`
- `frontend/src/components/document/DocumentTable.vue`
- `frontend/src/components/document/DocumentInspector.vue`
- 与以上对应的 `*.test.ts`
- `frontend/src/styles/tokens.css`（仅确有可复用 token 缺口时）

### 禁止修改

- 所有后端 `app/`、`tests/`、`alembic/`；
- `frontend/src/router/**`；
- `frontend/src/config/features.ts`；
- `frontend/src/components/layout/AppSidebar.vue`；
- `frontend/src/components/layout/AppTopbar.vue`；
- `frontend/src/layouts/AppShell.vue`；
- `frontend/src/components/knowledge-source/**`；
- 上传相关的 `DocumentUploadPanel.vue` / `useDocumentUpload.ts` / `documentUploads.ts`；
- 不相关的 LiteratureSearch、Home、Topbar、Breadcrumbs 文件。

### Git 保护

- 执行前先运行：`git status --short`、`git diff --stat`；
- 工作区已有大量其他会话的未提交改动，**一律保留**；
- 严禁：`git reset`、`git checkout -- .`、`git clean -fd`、`git stash`；
- 不提交、不 push、不改 git 配置；
- 不使用 `git add -A`。

---

## 5. 测试与验证（必须真实执行）

### 5.1 最小新增/更新测试

新增或更新与本次重构相关的 Vitest 测试，至少覆盖：

1. 文档库没有任何直接上传入口（维持已有契约）；
2. `sourceId` 下资料范围选择更新 URL/筛选（复用现有测试可只补缺口）；
3. 文档表格对真实成功/等待/失败/过期状态显示正确文字；
4. 未选中与选中文档时，右侧详情展示的是不同的真实状态；
5. AI 定位区存在、筛选区仍调用真实 filters 事件（不需要伪造结果）。

避免为视觉截图写脆弱的全量 DOM 快照；测试真实可观察的用户契约。

### 5.2 必须运行

```bash
cd /h/AI_project/rag_medicine/frontend
npm run typecheck
npm run test
npm run build
```

还必须至少跑本模块定向测试：

```bash
npx vitest run \
  src/components/document/DocumentManager.test.ts \
  src/components/document/DocumentScopeNav.test.ts \
  src/components/document/DocumentInspector.test.ts
```

并检查：

```bash
# 文档库不得重新引入上传入口（目标文件无输出才通过）
grep -n "DocumentUploadPanel\|useDocumentUpload\|uploadPdf" src/components/document/DocumentManager.vue

# 检查空白错误
git diff --check
```

如某命令失败，修复根因后重跑并报告真实结果；未运行不能声称通过。

---

## 6. 手动视觉验收（必须完成）

启动/使用现有本地前端后，打开：`http://localhost:5173/documents`

至少检查：

1. 桌面宽度（约 1440px）：顶部统计带 + 左中右三栏工作台清晰，无内容挤压；
2. 点击一个有真实数据的文件：右侧详情改为真实文件信息，行处于浅蓝选中态；
3. 切换“全部文档 / 一个知识源”：URL 与可见范围同步；
4. 设置解析/索引筛选后，真实列表刷新；
5. 小屏断点下不横向溢出；
6. 文档库没有上传入口；
7. 不出现目标图里的假数字、假路径、假文档、假页数或假段落数。

如使用截图验证，请在最终报告中说明实际检查 URL 与可见状态；不要把设计参考图误报成运行截图。

---

## 7. 最终报告格式

1. **实际修改文件**（只列实际修改）；
2. **目标图对齐说明**：统计带、资料范围、AI 定位、筛选、表格、右侧详情、响应式分别说明；
3. **真实数据边界**：哪些指标来自 API，哪些因无后端聚合能力显示 `—` 或未显示；
4. **未恢复上传入口**的代码证据；
5. **测试命令与真实结果**；
6. **视觉验收**：实际打开 URL、检查到的状态；
7. 已知限制与未做项。

不提交、不 push。
