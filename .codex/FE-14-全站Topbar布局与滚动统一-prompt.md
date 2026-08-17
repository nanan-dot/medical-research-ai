# FE-14：全站顶部导航栏（Topbar）布局与滚动行为统一修复

## 0. 唯一代码执行目录

**`H:\AI_project\rag_medicine`**（开始前先 `cd H:\AI_project\rag_medicine` 并执行 `git status --short`；不得在其他目录写代码）。

## 1. 任务背景与真实前提（已核查，务必以此为准）

用户要求：全站统一顶部导航栏的布局与滚动行为——滚动时顶栏固定可见、不遮挡内容、背景完全不透明、高度与分隔统一。**全站只有 `AppTopbar.vue` 一个顶栏组件**（挂在 `AppShell.vue`），不存在各页面自建顶栏；修改该组件即全站生效，**不要**去逐页寻找"其他顶栏"。

已核查的真实代码现状（改动前先复核）：

1. `frontend/src/components/layout/AppTopbar.vue`：
   - 已是 `position: sticky; top: 0; z-index: 10`；
   - **背景为半透明 `rgba(255, 255, 255, 0.92)`** ← 用户指出的核心问题：滚动内容会从顶栏下方透出；
   - `min-height: 64px`（硬编码，未用变量）；
   - 无 `border-bottom` 分隔；
   - 功能：面包屑（`Breadcrumbs`）、搜索与跳转（Ctrl+K）、任务铃铛、头像；**没有时钟功能**。
2. `frontend/src/layouts/AppShell.vue`：`.content { min-height: calc(100vh - 65px) }` —— **65px 与顶栏 64px 不一致**（真问题）。
3. `frontend/src/styles/tokens.css`：**无任何 topbar 相关变量**，需新增。
4. z-index 现状与层级关系（**不得打破**）：
   - 顶栏 `z-index: 10`；表格吸顶表头 `z-index: 1~2`（EvidenceMatrixTable、ComparisonMatrix）；
   - 移动端抽屉 `z-index: 30~35`（ContextRail、MobileNavigation）——**顶栏必须低于抽屉**，否则抽屉被顶栏压住；
   - 结论：顶栏 z-index 可提升到 **20**（高于表格吸顶与一般内容、低于抽屉），或维持 10 并说明理由；**禁止提到 1000 类高值**。
5. 其他 `position: fixed` 均为抽屉/弹层/滚动容器，与顶栏无关，不得改动。

## 2. 必读文件（按顺序）

1. `AGENTS.md`
2. `docs/CODE_STANDARDS.md`（V2.0 共 42 条，全部适用）
3. `frontend/src/components/layout/AppTopbar.vue`（主修改对象）
4. `frontend/src/layouts/AppShell.vue`
5. `frontend/src/components/layout/Breadcrumbs.vue`（只读参考）
6. `frontend/src/styles/tokens.css`（视觉 token 唯一来源）
7. `frontend/src/components/layout/MobileNavigation.vue`、`frontend/src/components/layout/ContextRail.vue`（只读，核对 z-index 层级）
8. 以上相关既有测试（`find frontend/src -name '*.test.ts'` 确认）

## 3. 代码规范强制约束（docs/CODE_STANDARDS.md 落地为可执行检查项）

1. **类型注解**（第 6/7 条）：如有新增/修改 TS 代码，显式类型；禁止隐式 `any`。
2. **语义命名**（第 5/8 条）：新增类名/变量名语义化（如 `--topbar-height`），不新增无意义命名。
3. **抽常量消魔法数字**（第 9 条）：64px/65px 等硬编码高度**必须**替换为 `var(--topbar-height)` 引用；不残留散落数值。
4. **中文注释讲设计意图**（第 10/11 条）：如有复杂逻辑（如 z-index 层级为何取 20、为何 sticky 优先于 fixed）写"为什么"注释；简单样式零注释。
5. **单文件单职责**（第 1 条）：变量定义进 `tokens.css`；顶栏样式留在 `AppTopbar.vue`；内容区布局进 `AppShell.vue`；不跨文件复制样式。
6. **禁硬编码色值**（frontend-ui-engineering）：**禁止**新增裸 hex / `var(--x, #hex)` fallback；一律引用既有语义 token：
   - 顶栏背景 → `var(--surface)`（`#ffffff`），**禁止 `rgba` 半透明**；
   - 分隔线 → `var(--border-subtle)`（`#e2e8f0`），**不要新增 `#e6edf5`**；
   - 阴影如需 → 复用 `var(--shadow-card)` 或等价既有 token，不新建阴影值。
7. **界面文案**（frontend-design）：不新增任何文案；不添加"时钟"或任何未存在功能（用户提示词中的"时钟"经核查不存在，属误写）。

## 4. 目标行为

### 4.1 顶栏固定与不遮挡（全局）

1. 保持 `position: sticky; top: 0`（sticky 已在布局流中占位，优于 fixed；**不要改成 fixed**，除非有页面级证据表明 sticky 失效——若有，先报告再定）；
2. **背景改为完全不透明**：`background: var(--surface)`；删除 `rgba(255,255,255,0.92)`；禁止 `transparent`、`opacity`、`backdrop-filter` 半透明组合；
3. **统一高度**：`tokens.css` 新增 `--topbar-height: 64px`，`AppTopbar` 使用 `height: var(--topbar-height)`（或 `min-height` + `box-sizing: border-box`），`AppShell` 的 `calc(100vh - 65px)` 改为 `calc(100vh - var(--topbar-height))`；
4. **z-index 层级**：顶栏提升到 **20**（高于表格吸顶表头 1~2、一般内容，低于抽屉 30~35）；在代码注释说明层级设计意图；
5. **视觉分隔**：`border-bottom: 1px solid var(--border-subtle)`；阴影保持克制（复用 `var(--shadow-card)` 或 `0 2px 8px rgb(15 23 42 / 4%)` 仅当现有 token 不满足时，且以 token 优先）。

### 4.2 全页面一致（验证范围）

改动集中于全局组件，**无需逐页修改**。验证以下页面滚动行为一致：

- 工作台 `/`、文献检索 `/literature-search`（含结果/历史/推荐 Tab）、文档与知识 `/documents` `/sources`、文档详情 `/documents/:id`、论文研究 `/analysis`（三 Tab）、多论文证据 `/comparisons`、证据矩阵 `/evidence-matrix`、研究设计、写作与汇报 `/writing`、后台任务 `/tasks`、设置 `/models`；
- 表格页（文献检索结果、证据矩阵）、长内容页（论文分析）、左右分栏页（文档详情）等；
- 场景：首次加载、路由切换、表格分页、筛选展开、抽屉/弹窗关闭后——均不得出现内容顶到/穿过顶栏。

### 4.3 不得破坏（回归边界）

- 顶栏现有功能：面包屑、搜索与跳转（Ctrl+K）、任务铃铛、头像、移动端菜单按钮；
- 侧边栏 `AppSidebar`（sticky 行为独立，不改）；
- 移动端抽屉/上下文栏的 z-index 层级（顶栏 20 < 抽屉 30~35）；
- 表格吸顶表头功能（其 z-index 1~2 应继续低于顶栏）；
- 不修改任何业务逻辑、路由、表格列、筛选逻辑、按钮功能。

## 5. 文件边界（严格）

### 允许修改（白名单）

- `frontend/src/components/layout/AppTopbar.vue`
- `frontend/src/layouts/AppShell.vue`
- `frontend/src/styles/tokens.css`（仅新增 topbar 相关变量：`--topbar-height` 等，不得改动既有 token 值）
- 以上文件对应的 Vitest 测试（如有，更新/新增）

### 禁止

- 其他任何 `.vue` 页面/组件（文档详情、文献检索、证据矩阵等**即使视觉上受益也不得改**）；
- 后端、路由、`features.ts`、`AppSidebar.vue`、`package.json`；
- 任何 `git reset / restore / checkout -- / clean / stash`；
- 提交、push。

### 工作区安全

`frontend/src/components/layout/AppTopbar.vue`、`frontend/src/layouts/AppShell.vue` 等可能有并行会话的未提交改动（`git status --short` 为 `M` 的文件）。**必须增量修改**：只改与本任务相关的区块，保留他人语义；改动前先 `git diff` 查看现有未提交改动，禁止整文件重写、禁止"顺手清理"。

## 6. 测试要求

- 若新增/修改可测逻辑（如顶栏高度变量、z-index），补充/更新 Vitest 断言；
- 已有相关测试全部保持通过；断言与新行为冲突时按新意图更新并注释理由，不得删除有效断言；
- 若无对应组件测试文件，可在报告中说明并以浏览器实测作为主要验收（不得虚报）。

## 7. 必须真实执行的验证（逐条运行并贴原始输出）

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
git diff --stat -- frontend/src/components/layout/AppTopbar.vue frontend/src/layouts/AppShell.vue frontend/src/styles/tokens.css
```

**越权核对（必做）**：`git diff --stat HEAD` 确认全部改动在第 5 节白名单内；白名单外文件被改 → **立即停止并报告**，不得自行回退他人文件（确认是本轮误改且可安全回退时，用 `git checkout HEAD -- <file>` 回退并说明）。

浏览器实测（若前端已运行 `http://localhost:5173`，否则可跳过并说明）：

1. 任选 3 个以上页面（如文献检索结果页、文档详情、论文分析）滚动到中部 → 顶栏固定可见、内容不透出；
2. 打开移动端菜单/上下文抽屉 → 抽屉盖住顶栏（层级正确）；
3. 表格页（文献检索结果、证据矩阵）滚动 → 吸顶表头低于顶栏，无穿透；
4. 路由切换（含 `?tab=` 变化）→ 顶栏位置与背景无异常；
5. 窄屏（<760px）→ 顶栏高度行为正常，不溢出。

任何命令失败：贴完整失败原因并停止，不得声称通过。

## 8. 最终报告格式

1. 改动前核对（含 z-index 层级、半透明背景确认）
2. 修改文件与每个文件的具体改动（含新增 token 定义）
3. 代码规范符合性说明（第 3 节逐条）
4. 实际运行命令与原始结果
5. `git diff --stat HEAD` 越权核对结果
6. 浏览器实测结果（含全站页面抽样、抽屉层级、表格吸顶）
7. 本轮刻意未触碰的文件
8. 已知限制【未实测】

完成后停止，不提交，不 push，不继续其他页面。
