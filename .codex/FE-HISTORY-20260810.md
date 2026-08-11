# 素问·文献检索「历史记录」页面设计执行提示词（FE-历史记录）

> 本提示词由 Hermes 生成，供 Codex 执行。执行前必须先读仓库规范与现状，再动手。

## 一、任务总览

重构 `frontend/src/views/LiteratureSearch/History.vue`（及必要子组件），使其成为符合「素问」产品视觉的检索历史管理页。**同时执行一次代码清理**：删除无用的注释代码、死代码、未使用 import/变量，保持代码活力与健壮性（遵守 `docs/CODE_STANDARDS.md` 全部 42 条）。

## 二、必读文件（执行前按序阅读）

1. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范，必须服从）
2. `frontend/src/views/LiteratureSearch/History.vue` — 当前实现（199 行，有 embedded 模式与真实 API）
3. `frontend/src/views/LiteratureSearch/History.test.ts` — 现有测试契约（**必须保持通过**：检索历史/已完成/重跑/新增 2 条/rerunSucceeded emit）
4. `frontend/src/api/literatureSearch.ts` — 真实 API（listTasks/rerunTask）
5. `frontend/src/styles/tokens.css` — 设计 tokens（--surface/--color-primary/--radius 等）
6. `frontend/src/views/LiteratureSearch/LiteratureWorkspaceTabs.vue` — 局部导航（History 以 embedded 模式嵌入，tab 高亮由父级控制）

## 三、设计目标（参照预览图，非逐像素硬抄）

预览图两张：`素问_文献检索_历史记录_研究主题_20260810.png`（灰条为预览图隐私占位，**不是**要实现的内容——实现用真实数据）。设计方向：

### 1. 页面标题区
- 标题「历史记录」，副标题：管理您的检索历史。旧的快照将保留，重跑将生成新版本。（预览图原文）
- 不使用英文大写 eyebrow（如 SEARCH HISTORY · LIVE），保持简洁中文。

### 2. 主表格（核心内容）
7 列对齐预览图：
| 研究主题 | 检索式 | 结果版本 | 结果数 | 状态 | 最后运行 | 操作 |

- **研究主题**：`task.original_query`（真实数据）
- **检索式**：`task.search_string` 单行省略号（monospace），title 悬停显示全文
- **结果版本**：`v{versions.length}`，有变化时显示 `+N 条`（新增绿色）/ `-M 条`（减少橙色）
- **结果数**：`task.result_count`
- **状态**：胶囊 badge——已完成（绿）/ 失败（红）/ 执行中·待执行（蓝）
- **最后运行**：`task.searched_at` 本地化时间；未检索过显示「未检索」
- **操作**：「查看结果」（有 latest_result_id 时，链接到 `/literature-search/results/{id}?task={taskId}`，描边按钮）+「重跑」（实心蓝按钮，running 时禁用）

行样式：白底、细蓝灰分隔线、hover 淡蓝、约 8px 圆角容器、克制阴影。行内可展开的失败原因（`error_message` 红色小字）与版本变化摘要（新增/减少 PMID 列表，可折叠）。

### 3. 工具栏与分页
- 工具栏：刷新按钮（描边）+「共 N 次检索」计数（灰字）
- 分页：上一页 / 第 X / Y 页 / 下一页（描边按钮，边界禁用）；每页 10 条
- 空态：虚线框「暂无保存的检索任务…」提示

### 4. 响应式
- 桌面 >=1280px：完整 7 列表格
- 窄屏（<=900px）：隐藏表头，改为卡片式列表（主题+检索式占整行，其余字段两列布局）

## 四、代码规范（CODE_STANDARDS.md 关键条，必须服从）

1. **单文件单职责**：History.vue 是页面组合；表格行、状态徽标、分页可拆为同目录子组件（如 `HistoryTableRow.vue`），禁止 300+ 行单文件。
2. **命名语义化**：`handleXxx` 事件、`is_/has_` 布尔、无 `tmp/data2`。
3. **注释写设计意图**：复杂逻辑（版本变化计算、重跑后替换）写「为什么」，不复述行为；简单代码零注释。
4. **类型完整**：props/emit 显式类型；禁止隐式 any。
5. **删除死代码**：本次重点——未使用的 import、`_unused` 变量、注释掉的代码块、冗余样板全部删除。
6. **禁止空 except**：错误路径必须处理。
7. **真实数据**：只用 `literatureSearchApi.listTasks/rerunTask`，不伪造任务/结果/时间。
8. **诚实标注**：任何未实测的功能在交付说明中标注【未实测】。

## 五、验收标准（必须全部真实执行）

```bash
cd frontend
npm run typecheck   # 0 错误
npm run test        # 全部通过（含 History.test.ts 现有 2 个测试）
npm run build       # 构建成功
```

- History.test.ts 现有断言**不允许破坏**（检索历史/已完成/search-intent-v1/重跑/新增 2 条/减少 0 条/39000401/rerunSucceeded）
- 不修改：`AppSidebar.vue`、`AppTopbar.vue`、`features.ts`、`router/index.ts`、`LiteratureWorkspaceTabs.vue`
- 不修改后端任何文件（工作区有其他会话的未提交后端改动，**一律不碰**）

## 六、工作区注意（重要）

- 仓库当前有 **84 个未提交改动**（其他会话进行中，涉及 app/modules/conversation、evidence_matrix、literature_search、writing_project 等）——**你只允许修改**：
  - `frontend/src/views/LiteratureSearch/History.vue`
  - `frontend/src/views/LiteratureSearch/` 下新增的子组件（如 HistoryTableRow.vue）
  - `frontend/src/views/LiteratureSearch/History.test.ts`（仅当测试契约需要适配新 DOM 时，且不得删除现有断言语义）
- **其他文件一律不得触碰**（含 git add 时只 add 上述文件）
- 命令统一前缀：`env PYTHONPATH=""`（后端 python 用 `/f/software/programme/Anaconda/envs/med-research-ai/python.exe`，本次仅前端，npm 命令即可）

## 七、交付说明（完成后输出）

1. 修改/新增文件清单
2. 复用了哪些现有功能/API
3. 删除了哪些死代码/注释代码（清单）
4. typecheck/test/build 真实命令输出
5. 未改动的受保护文件确认
6. 已知限制与【未实测】项
