# Codex 执行提示词：笔记库 V1.2 前端完整复现

## 1. 任务目标

在本机仓库 `D:\AI_project\rag_medicine` 中直接实现“笔记库”前端页面。视觉与信息层级以以下冻结预览图为像素级基准：

- 原始基准：`C:\Users\ADMIN\Desktop\rag医学检索\预览图设计继续\笔记库.png`
- 归档基准：`C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.3\08-研究资源工作区\预览图\笔记库首页前端实施基准_V1.2.png`

目标不是制作静态演示页，而是用真实 `/api/v1/note-library` 契约完成可用、可保存、可恢复、可测试的笔记工作区。笔记列表是页面主体；左侧为笔记导航，右侧为窄阅读预览。同页完成新建、编辑、自动保存、正式保存、冲突处理、历史版本和恢复，不跳转到其他业务页面。

## 2. 必须遵守的工作边界

1. 先完整读取仓库根目录及目标目录内所有 `AGENTS.md`，再读取现有 router、AppShell/AppSidebar、API client、文档/论文库相邻页面、后端 note-library OpenAPI/路由/schema/service 和相关测试，确认当前真实契约后实施。
2. 必须使用并完整遵循以下 skills：`vue`、`vue-best-practices`、`ui-design`、`frontend-a11y`、`playwright`、`acceptance-testing`。Vue 使用 Composition API、`<script setup lang="ts">` 和明确类型；同时读取 vue-best-practices 要求的核心 references。
3. 只修改笔记库 route-specific 页面、组件、composables、样式、API adapter、测试、文档，以及接入该页面必需的最小 router/route-meta/sidebar 条目。不得重构 AppShell，不得改变其他导航样式，不得改其他页面。
4. 不修改后端，不新增或修改数据库迁移，不升级、不降级、不写入正式数据库。若发现契约缺陷，只在最终报告中给出证据，不擅自扩展后端范围。
5. 工作区含大量用户和其他任务未提交内容。禁止 `reset`、`checkout`、`clean`、删除目录或覆盖无关修改。修改目标文件前重读最新内容；出现外部修改时重新读取并最小合并。使用 `apply_patch` 编辑。
6. 生产 UI 必须使用真实 API，禁止硬编码截图中的论文、笔记、计数或商业指标；测试可以使用明确标注的确定性合成 fixture。不得伪造 AI、通知、原文定位或多用户能力。
7. 当前后端是 local actor scope。通过笔记库 API adapter 集中提供稳定的本地 actor scope，不允许用户任意传入，不在界面宣称生产级多租户隔离。
8. 当 capabilities 返回 `ai_suggestions_unavailable` 时，不显示可执行 AI 润色/生成按钮。当 `view_source_location` 不可用或 source 被撤销时，不显示虚假的“已验证定位”；使用真实的降级状态。

## 3. 冻结视觉与交互语言

在现有共享 AppShell 内复现基准图，不在页面内重复全局侧边栏。

- 页面顶部：标题“笔记库”、简短副标题、全局笔记搜索、新建笔记主按钮。通知铃等未实现能力不应为追求截图而伪造。
- 业务区为三列：笔记导航约 250px；中间笔记列表占主要宽度；右侧阅读预览约 400–440px。宽屏下列表必须是视觉主体，禁止卡片墙化。
- 左列：全部笔记、最近编辑、收藏、未关联研究；研究分组、标签分组、归档。数量来自 facets/quick counts。长列表折叠或“查看全部”。
- 中列：标题、筛选结果/总数、真实排序状态、筛选入口；每行采用“标题—摘要—来源/研究/标签—时间”低噪声排版。选中行仅用浅蓝底和左侧蓝线；黄色只用于收藏星标。
- 右列：标题、保存/版本状态、正文、来源、关联研究、继续编辑主按钮和必要次操作。右侧保持阅读预览，不扩大为第二个主体。
- 色彩为蓝白学术工作台，标签低饱和，文字层级清晰；使用项目既有 token 和字体，不创建平行设计系统。
- 1774×887 为主要视觉验收尺寸。空间不足时先将预览收为抽屉，再将笔记导航收为抽屉；移动端使用列表/预览/编辑分层，并保持查询与选中状态。

## 4. 建议实现结构

遵循仓库命名与组织习惯；若现状存在等价结构，应复用而非机械新建。建议边界：

- `frontend/src/views/NoteLibrary/NoteLibraryView.vue`：薄 route view。
- `frontend/src/components/note-library/NoteLibraryWorkspace.vue`
- `NoteLibraryHeader.vue`、`NoteNavigationPanel.vue`
- `NoteListPanel.vue`、`NoteListRow.vue`
- `NotePreviewPanel.vue`、`NoteEditorPanel.vue`
- `NoteSourceList.vue`、`NoteHistoryDrawer.vue`、`NoteConflictDialog.vue`
- `frontend/src/composables/useNoteLibrary.ts`
- `useNoteDraftAutosave.ts`、`useNoteKeyboardNavigation.ts`
- `frontend/src/api/noteLibrary.ts`：真实类型、参数编码和 capability adapter。

避免巨型组件；route view 不承载完整业务。无需为此引入 Pinia，除非仓库已经以 Pinia 管理同类页面状态。

## 5. 数据与状态设计

1. URL query 保存可分享/可恢复状态：`view`、`q`、tags、research contexts、`page`、`page_size`、`note_id`。浏览器前进后退与刷新必须恢复。
2. 搜索防抖，并在新请求开始时取消旧请求或用序列号拒绝过期响应；绝不允许慢响应覆盖新查询。任何筛选变化将页码归一到 1。
3. 列表、facets、详情、draft、history 分开建模。局部来源加载失败不得清空正文或整个预览。
4. 明确展示首次加载、局部加载、空笔记库、筛选无结果、失败可重试、离线/保存失败状态。
5. 新建后立即在本页进入编辑。草稿自动保存约 1 秒防抖，携带 `expected_draft_version`，显示“正在保存 / 草稿已保存 / 保存失败”，保存状态通过 `aria-live` 宣读。
6. 正式保存前校验非空标题和正文；一次逻辑保存重试复用同一 idempotency key。成功后同步详情、列表摘要、时间和版本信息。
7. `409` 必须解析为结构化冲突状态：保留本地内容，提供重新加载服务端版本、复制本地草稿、对比后重试等安全路径；不得静默覆盖。
8. metadata 更新使用真实 CAS/version 字段。收藏、标签、关联研究、归档/取消归档不得隐式创建正文版本，除非后端契约明确如此。
9. 历史列表分页；可查看单个 revision；恢复操作创建新 revision，并刷新当前预览与历史，不能改写历史记录。
10. 来源显示后端 snapshot/状态。仅在现有阅读器确实消费对应 document/anchor 参数且 capability 允许时提供“查看原文定位”；否则显示元数据、撤销或不可定位状态。
11. 未信任文本不得用裸 `v-html`；默认使用 Vue 文本转义。若确需富文本，必须复用仓库已验证 sanitizer。

## 6. 最小共享接入授权

允许且只允许以下共享改动：

- 注册 `/notes` 路由及 lazy-loaded view。
- 在 route meta/breadcrumb 中加入 `研究资源 / 笔记库`。
- 在研究资源二级导航中加入一个“笔记库”入口，并将 `/notes` 纳入该组 active 判定。
- 更新上述改动直接影响的 router/AppSidebar 测试。

不要改变共享侧栏的布局、图标体系、颜色、展开逻辑或其他入口顺序，除非当前项目规范要求最小一致性调整并有测试证据。

## 7. 验收标准与行为测试映射

实施前先把以下 AC 映射为可执行行为测试，并确认关键新测试在实现前失败。完成时每一项必须有真实测试名和通过证据。

- **AC-NLF-01 路由接入**：`/notes` 可直达；侧栏入口和 breadcrumb 正确；其他导航回归通过。
- **AC-NLF-02 版式层级**：1774×887 下三列比例、列表主体、窄预览、选中态与基准一致；无重复全局侧栏。
- **AC-NLF-03 快捷视图**：all/recent/favorite/unlinked_research/archived 使用真实 view 参数并显示真实 counts。
- **AC-NLF-04 搜索一致性**：防抖、取消/拒绝过期响应、换条件回第一页；慢旧响应不能覆盖新结果。
- **AC-NLF-05 筛选**：真实 tags/research contexts facets、组合语义、清除筛选和结果计数正确。
- **AC-NLF-06 分页边界**：20/50/100（仅限后端允许值）、首页/末页/空页稳定，URL 与返回 meta 一致。
- **AC-NLF-07 列表信息**：标题、摘要、来源摘要、研究摘要、标签、收藏和时间均来自 API，不虚构截图数据。
- **AC-NLF-08 选择与深链**：选择行更新预览和 `note_id`；刷新恢复；无效/无权/已归档 note 安全处理。
- **AC-NLF-09 收藏与元数据**：收藏及标签/研究关联使用真实 version/CAS；冲突不覆盖他人更新。
- **AC-NLF-10 同页新建编辑**：新建笔记直接在当前工作区打开编辑，不跳往其他页面。
- **AC-NLF-11 草稿自动保存**：防抖、expected version、保存状态、失败重试和离开页面保护均可验证。
- **AC-NLF-12 正式保存与幂等**：校验、稳定 idempotency key、成功后的版本/列表刷新正确。
- **AC-NLF-13 冲突安全**：409 保留本地草稿，提供结构化解决操作，绝不静默 last-write-wins。
- **AC-NLF-14 历史与恢复**：历史分页、revision 查看、restore 创建新 revision 且当前视图刷新。
- **AC-NLF-15 来源能力降级**：capability 允许时才开放已验证定位；撤销/缺失/不可用状态准确。
- **AC-NLF-16 归档生命周期**：归档从普通视图移除、归档视图可见、取消归档后恢复；选择态安全迁移。
- **AC-NLF-17 加载/空态/错误**：首次空库、无筛选结果、列表失败、详情局部失败和可重试动作均正确。
- **AC-NLF-18 键盘与无障碍**：上下键移动选择、Enter 编辑、Escape 关闭；焦点管理、语义按钮、标签、对比度、触控尺寸和 aria-live 通过。
- **AC-NLF-19 响应式**：预览先折叠、导航后折叠；手机列表/预览/编辑可返回，状态不丢失。
- **AC-NLF-20 端到端闭环**：Playwright 覆盖进入页面→搜索/筛选→选择→新建→自动保存→正式保存→冲突→历史→恢复→归档；另覆盖请求乱序和保存失败。

## 8. 测试与验证门禁

1. 优先写组件/组合函数/API adapter 行为测试，使用确定性 fetch fixture；生产代码不得依赖 mock。
2. 增加 `frontend/e2e/note-library.spec.ts` 或仓库等价位置。视觉 fixture 使用明确合成数据，在 1774×887 截图对比；动态时间等需稳定化或遮罩，不能通过放宽阈值掩盖结构错误。
3. 运行并记录：
   - 仓库实际存在的 frontend lint/format 检查；
   - `npm run typecheck`；
   - 笔记库 targeted Vitest；
   - router、AppSidebar 及相邻研究资源回归；
   - frontend 全量测试；
   - `npm run build`；
   - 笔记库 Playwright E2E 与视觉检查；
   - `git diff --check`。
4. 若浏览器运行时确实不可用，必须先穷尽仓库现有 Playwright 安装方式；仍不可用时明确报告为未通过门禁，不得声称 E2E 完成。
5. 不运行任何正式数据库迁移。所有测试只能使用 mock HTTP、临时测试库或仓库既有隔离测试设施。

## 9. 文档与最终报告

更新或新增笔记库前端 traceability 文档，并只对 `FRONTEND_IMPLEMENTATION_STATUS.md` 中与笔记库直接相关的条目做最小更新。最终报告必须包含：

1. AC-NLF-01～20 的“验收项 → 测试文件/测试名 → 结果”映射。
2. 修改文件清单与每个文件作用。
3. 视觉基准对比结论、关键响应式断点和仍有差异。
4. API/capability 使用清单，以及没有伪造的能力。
5. typecheck、测试、build、Playwright、`git diff --check` 的原始结果摘要。
6. 明确说明：后端是否修改（必须为否）、迁移是否创建（必须为否）、正式数据库是否写入/升级（必须为否）。
7. 仍有的结构性限制，尤其 local actor scope、AI suggestions unavailable 和任何未落地的原文阅读器定位。

只有 AC-NLF-01～20 全部有真实测试映射且门禁通过，才能声明完成。持续执行到实现和验证结束，不停留在阶段性报告；只有无法安全解决的真实并发冲突或缺少必须由用户提供的授权数据时才停止。
