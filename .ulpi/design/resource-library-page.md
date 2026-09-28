# 资料库页面锁定设计与实现交接规范

> 设计工作包：RESOURCE-LIBRARY-V1  
> 页面路由：保留 `/documents`（产品显示名改为“资料库”）  
> 设计语言：`.ulpi/design/DESIGN.md`  
> 旧规范：`.ulpi/design/document-library-page.md` 仅作为迁移参考，不再作为页面视觉权威  
> 视觉基准：用户提供的“资料库”全页预览与两版左侧来源栏截图

Every screen must read as the same product if placed side by side.

## 1. Design Read

成熟的医学科研资料控制台。以高密度、低噪声的资料表格为中心，用可追溯的来源树和真实处理状态帮助用户快速判断“资料在哪里、是否可用、出了什么问题、下一步做什么”。

### 锁定方向

- register：product
- aesthetic direction：technical / utilitarian
- design system：Vue 3 + Reka UI primitives，沿用项目组件体系
- design variance：5/10
- motion intensity：2/10
- visual density：8/10
- 唯一主操作：`导入资料`
- 页面 Signature：从“资料来源树”延伸到“当前视图”的证据路径线和选中节点

本页不得创建新的颜色、圆角、字体、阴影或动画。所有视觉值绑定 `.ulpi/design/DESIGN.md`。

## 2. 产品决策

### 2.1 文档库升级为资料库

不新建第二套重复业务页。复用现有 `/documents`、文档详情、预览、修复和任务能力，在其上升级信息架构：

1. UI 名称由“文档库”统一改为“资料库”；
2. 面包屑由“文档与知识 / 文档库”改为“研究资源 / 资料库”；
3. 旧数据模型和 API 名称可以继续使用 `Document`，不要为了中文文案做高风险后端重命名；
4. `/documents` 保持兼容，旧链接、收藏和详情路由继续有效；
5. 原文档库的批量操作、任务进度、服务端分页和详情预览继续保留；
6. 新资料库的来源树、最近资料、统一搜索、存储统计和 Zotero 逐步接入真实后端。

### 2.2 左侧栏最终方案

采用“层级来源树”方案，不采用顶部 `全部 / 本地 / Obsidian` 标签页。最终顺序固定为：

1. 全部资料；
2. 搜索资料来源；
3. 最近使用资料；
4. 资料来源树；
5. 管理资料来源；
6. 存储空间（仅在有真实数据时显示）。

原因：本地、Obsidian、Zotero 是来源类型，不是互斥内容视图；层级树可以同时表达类型、库、集合和目录，未来扩展不会继续增加标签页。

## 3. 页面布局

### 3.1 桌面基准

```text
┌──────── 264px 应用侧栏 ────────┬──────────────── 主内容 ────────────────┐
│ 全局导航                       │ 顶部栏 / 面包屑 / 全局搜索             │
│                                ├─────────────────────────────────────────┤
│                                │ 标题、副标题、管理来源、导入资料       │
│                                │ 五项统计状态条                         │
│                                │ ┌── 280px 上下文栏 ─┬── 资料工作区 ─┐ │
│                                │ │ 全部/最近/来源树  │ 搜索筛选与表格 │ │
│                                │ │ 固定管理入口      │ 分页/批量操作  │ │
│                                │ └───────────────────┴────────────────┘ │
└────────────────────────────────┴─────────────────────────────────────────┘
```

- 页面内容最大宽度：不设窄容器，使用可用工作区；左右安全边距 24px。
- 页面标题区：高度约 76px，不使用大面积 Hero。
- 统计条：五列，桌面单行，高度 92–100px。
- 主工作区：`280px minmax(0, 1fr)`，间距 16px。
- 上下文栏和表格区等高，最小可视高度 `calc(100vh - 300px)`。
- 表格是视觉焦点，不使用嵌套卡片。主工作区仅有一层白色 surface 和规则分割线。

### 3.2 响应式

| 宽度 | 行为 |
|---|---|
| ≥1440px | 完整五统计项、280px 来源栏、完整表格列 |
| 1024–1439px | 来源栏 248px；统计条可 3+2 换行；隐藏次要表格描述，不隐藏状态 |
| 768–1023px | 来源栏进入可关闭 Drawer；统计变为横向可滚动条；筛选允许折叠 |
| <768px | 单列；来源树、筛选均为 Drawer；表格变资料列表卡，但保持相同状态与操作语义 |

移动端触控目标至少 44×44px，底部安全区受尊重。

## 4. 页面内容与精确文案

### 4.1 标题区

- H1：`资料库`
- 副标题：`管理进入研究体系的资料，并提供检索、问答与分析能力`
- 次操作：`管理资料来源`
- 主操作：`导入资料`

禁止使用“智能化、强大、无缝、赋能”等营销文案。

### 4.2 五项统计

| 顺序 | 名称 | 主数值 | 辅助说明 | 颜色 |
|---|---|---|---|---|
| 1 | 资料总量 | total | 全部纳入资料 | accent-neutral |
| 2 | 已解析 | processed | 内容提取完成 | success |
| 3 | AI 可使用 | ai_available | 可用于检索、问答 | success / accent-soft |
| 4 | 处理中 | processing | 正在解析或建立索引 | info |
| 5 | 需处理 | needs_attention | 失败、失效或内容已更新 | warning |

规则：

- “已解析”和“AI 可使用”是包含关系，不承诺五项相加等于总量；
- 卡片必须有 Tooltip 解释统计口径；
- 不得根据当前页计算；
- 加载时使用固定尺寸 skeleton，避免 CLS；
- 部分统计失败时显示 `暂不可用`，不得显示 0；
- 点击统计项可追加对应筛选，其中“资料总量”清除状态筛选。

## 5. 左侧资料上下文栏

### 5.1 全部资料入口

- 固定在顶部；高度 40px；图标 + `全部资料` + 去重后的资料总数；
- 选中时使用 accent-soft 背景、accent 文字和 2px 左侧路径线；
- 点击后清除来源、目录节点和最近资料选择，保留用户主动设置的类型/状态筛选；
- 键盘 Enter/Space 激活。

### 5.2 来源搜索

- placeholder：`搜索资料来源或文件夹…`
- 只搜索左侧来源树，不搜索正文或资料名称；
- 输入 150ms 防抖；
- 匹配来源名、库名、集合名和相对目录；
- 匹配时自动展开祖先节点，清除后恢复用户之前的展开状态；
- 无结果：`没有匹配的资料来源`；
- 搜索框旁不再增加来源类型标签页。

### 5.3 最近使用

- 标题：`最近使用`
- 默认显示最近明确打开的 3 份资料，最多 5 份；
- 每项显示文件类型图标、单行文件名；必要时 Tooltip 展示完整名称和来源；
- 点击直接进入资料详情/预览，不改变当前来源筛选；
- 只读加载、筛选或后台同步不得计入最近使用；
- 空状态：`打开资料后会显示在这里`。

### 5.4 资料来源树

- 标题：`资料来源`
- 一级分组固定排序：本地文件、Obsidian、Zotero；未配置的来源分组可显示但使用安静的空状态，不创建假数量；
- 分组节点显示类型图标、名称、去重后的后代资料数；
- 二级节点为本地根目录、Obsidian Vault、Zotero Library/Collection；
- 更深层节点按需展开；默认最多展开到当前选中节点及其祖先；
- 数量分为 `direct_count` 与 `descendant_count`，UI 默认展示后代去重数量；
- 点击箭头只展开/折叠；点击名称筛选右侧资料；
- 当前选中节点使用路径线连接祖先，体现 DESIGN Signature；
- 不可用来源同时显示图标和文字 `不可用`，不能只变红；
- 节点菜单：同步、查看详情、编辑、停用；删除属于危险操作并二次确认。

### 5.5 数量口径

- `全部资料` 与来源树使用“已纳入资料库”的资料口径；
- 同一 Zotero 条目出现在多个集合时，父级汇总按资料去重；
- 不允许出现“全部 328、本地 1280”而没有解释的冲突；
- 若需要表达外部来源总条目，应单独写成 `来源中 1280 项，已纳入 328 项`，不能混在同一计数列。

### 5.6 底部操作

- `管理资料来源` 固定在上下文栏底部；
- 存储统计有真实 API 才显示；未配置配额时显示 `已使用 128 GB`，不显示虚构的 `/ 500 GB`；
- 空间超限使用 warning 图标、文字和解决入口，不仅使用颜色。

## 6. 右侧资料工作区

### 6.1 当前视图标题

- 全部：`当前视图：全部资料`
- 来源：`本地文件 / ILD 核心文献`
- 目录：完整面包屑可横向滚动，最后节点加粗；
- 同行显示当前过滤后的总量，不显示当前页条数冒充总数。

### 6.2 统一搜索

- placeholder：`搜索资料标题、正文内容、路径或来源…`
- 一个输入同时查询标题、正文、路径和来源；
- 300ms 防抖，回车立即搜索；
- 查询进入 URL，刷新和前进后退可恢复；
- 正文命中可在行内显示经过净化的短摘要和定位；
- 超时或正文索引不可用时明确标注降级到标题/路径搜索。

### 6.3 筛选工具条

第一行只保留高频条件：

1. 来源；
2. 类型；
3. 状态；
4. 更新时间；
5. 排序；
6. `筛选`按钮打开完整 Drawer。

规则：

- 每个菜单显示真实 facet 数量；
- 多选后在工具条下方显示可移除筛选标签；
- `清除全部`只在有筛选时出现；
- 所有过滤、排序在服务端分页前完成；
- 筛选变化回到第 1 页；
- URL 使用稳定枚举，不写中文文案。

### 6.4 任务进度横条

- 仅当前视图存在活动任务时出现；
- 文案示例：`正在处理 ILD 临床试验资料 · 12/20 已完成 · 3 个需要处理`；
- 进度来自持久化任务，不使用随机值；
- 右侧动作：`查看进度`；
- 任务完成后保持成功摘要 5 秒后折叠，减少跳动；
- 失败时显示失败数量和 `查看问题`，不得让整页不可用。

### 6.5 批量操作

- 表头复选框支持当前页全选；
- 选中后显示粘性批量工具条：`已选择 N 份`、重新处理、修复、删除；
- 不同状态混选时，只启用对所有选中项都安全的操作；
- 跨页选择除非后端有 selection token，否则不实现；
- 破坏性删除二次确认，并明确“仅移除资料记录”或“同时删除托管文件”的真实语义。

## 7. 资料表格

### 7.1 列结构

| 列 | 宽度 | 内容 |
|---|---:|---|
| 选择 | 44px | checkbox |
| 资料信息 | minmax(360px, 1fr) | 图标、名称、来源路径、类型、大小、可选命中摘要 |
| 状态 | 220–260px | 状态名称、原因、真实进度 |
| 更新时间 | 150px | 本地化日期时间，使用 tabular-nums |
| 操作 | 150px | 主行操作 + More 菜单 |

行高：正常 72px；有正文命中摘要时最多 96px。名称最多两行，路径单行省略。

### 7.2 状态映射

| 状态 | 主文案 | 辅助文案 | 主操作 |
|---|---|---|---|
| available | AI 可使用 | 解析和索引完成 | 查看 |
| parsed | 已解析 | 等待建立索引 | 查看进度/建立索引 |
| processing | 处理中 N% | 当前阶段名称 | 查看进度 |
| parse_failed | 需处理 | 解析失败 | 修复 |
| index_failed | 需处理 | 索引建立失败 | 修复 |
| outdated | 内容已更新 | 需要重新处理 | 重新处理 |
| missing | 异常 | 文件不可访问 | 修复 |
| metadata_only | 仅元数据 | 尚无可处理附件 | 查看来源 |

- 状态必须由图标、文字和语义色共同表达；
- `N%` 仅在后端提供真实 active task 进度时展示；
- 原因优先使用稳定 reason code 映射为用户文案，不直接展示堆栈或绝对路径；
- 每行只能有一个最相关主操作，其余进入 More 菜单。

### 7.3 文件类型

- PDF 红、DOCX 蓝、PPTX 橙、Markdown/TXT 中性蓝灰；
- 文件类型色仅用于图标，不作为业务状态；
- 未知类型显示通用文件图标和真实扩展名；
- 文件名、来源和大小均来自 API，禁止示例数据进入生产路径。

### 7.4 行交互

- 点击名称或“查看”打开详情/预览；
- 点击空白行只选中高亮，不立即跳转，避免与多选冲突；
- 双击不绑定关键操作；
- More 菜单支持键盘、Esc 关闭并恢复焦点；
- 修复提交后行状态立即变为 `正在提交…`，收到任务 ID 后转为持久化进度；
- 失败只更新当前行，不清空整个列表。

## 8. 分页

- 左侧显示 `共 N 份资料`；
- 中间显示紧凑页码，当前页高亮；
- 右侧每页 25/50/100，默认 25；
- 修改每页数量后回到第 1 页；
- 页码、pageSize、筛选、来源、搜索、排序全部写入 URL；
- 请求竞态使用 AbortController 或 request sequence，旧响应不得覆盖新状态。

## 9. 详情与管理交互

### 9.1 查看资料

- 桌面优先打开右侧 Drawer，宽度 520–640px；移动端全屏；
- PDF 使用安全流式预览，DOCX 使用结构化预览；
- PPTX、MD、TXT 只有真实支持时预览，否则显示格式限制和下载/打开来源入口；
- Drawer 打开后焦点进入标题，关闭后恢复到触发行。

### 9.2 管理资料来源

- 进入来源管理页，不在当前页面堆叠完整配置表单；
- 提供本地文件、Obsidian、Zotero 的真实配置状态；
- Zotero 未配置时显示 `尚未连接 Zotero` 和连接入口，不生成示例集合。

### 9.3 导入资料

- 使用 Modal/Drawer，支持真实后端允许的格式；
- 上传前显示目标来源、格式、大小限制；
- 多文件逐项显示结果；单项失败不吞掉成功项；
- 上传成功后进入任务进度，不伪装为立即 AI 可用。

## 10. 状态覆盖

| 状态 | 页面行为 |
|---|---|
| 初始加载 | 保留稳定骨架尺寸；来源栏、统计和表格分别加载 |
| 空资料库 | 显示来源说明与唯一主操作“导入资料” |
| 当前来源为空 | 保留来源树选中状态，提示该来源暂无资料 |
| 搜索无结果 | 显示当前条件、清除搜索和清除筛选入口 |
| 部分失败 | 成功区域继续可用；失败区域内联重试 |
| 全局离线 | 显示持久提示，保留上次成功数据但标注非最新 |
| 401/403 | 保留 return URL 后进入登录或权限页 |
| 404 来源 | 清除失效来源 query，返回全部资料并通知用户 |
| 后台任务失败 | 当前行和任务条显示可恢复操作，列表其余资料可用 |
| Zotero 降级 | 使用旧快照并标注“同步暂不可用”；无快照时显示未连接/失败 |

## 11. URL 状态契约

```ts
interface ResourceLibraryRouteQuery {
  sourceId?: string;
  nodeId?: string;
  q?: string;
  types?: string;       // comma-separated stable enum
  statuses?: string;
  updatedFrom?: string; // YYYY-MM-DD
  updatedTo?: string;
  sort?: string;
  order?: 'asc' | 'desc';
  page?: string;
  pageSize?: '25' | '50' | '100';
  documentId?: string;  // open drawer/deep link
}
```

无效参数使用安全默认值并 replace URL；不得进入请求循环。

## 12. 组件交接

### ResourceLibraryView

- 责任：编排标题、统计、来源上下文和资料工作区；不直接实现 API 细节。
- 状态：loading、partial、ready、fatal-error。
- 文件建议：`frontend/src/views/Documents/DocumentsView.vue` 原地升级。

### ResourceSummaryStrip

- props：summary、loading、error、activeStatus。
- emits：select-status、retry。
- 无障碍：使用有意义的列表结构；可点击项为 button；数值更新用 polite live region。

### ResourceContextRail

- props：tree、recentItems、selectedNodeId、query、loading、storage。
- emits：select-all、search、select-node、toggle-node、open-recent、manage-sources。
- 键盘：树使用 ARIA tree/treeitem；上下键移动，同级左右键展开/折叠，Home/End 跳转。
- 性能：大树使用按需加载或虚拟列表；搜索时不破坏原展开状态。

### ResourceToolbar

- props：query、filters、facets、sort、loading。
- emits：update-query、update-filter、clear、open-filter-drawer。
- 搜索必须有可见或屏幕阅读器 label；清除按钮有明确 aria-label。

### ResourceTaskBanner

- props：activeTask、summary。
- emits：open-task、open-issues。
- progress 使用原生 progress 或正确的 progressbar ARIA；宣布阶段变化但避免每 1% 打扰。

### ResourceTable

- props：items、selection、loading、sort。
- emits：open、select、select-page、repair、reprocess、open-progress、delete、sort。
- 使用语义 table；表头排序提供 `aria-sort`；行操作名称包含文件名。
- 在窄屏切换列表布局，但 DOM 阅读顺序保持“名称→状态→时间→操作”。

### ResourceDetailsDrawer

- 使用 Reka Dialog/Drawer 原语；焦点陷阱、Esc、关闭后恢复焦点必须通过测试。
- 预览内容懒加载；关闭时取消请求；错误不会关闭 Drawer。

### ResourceImportDialog

- 支持拖放和文件选择；必须提供非拖放等价路径。
- 每个文件有独立上传/处理/失败状态；错误可操作且不暴露内部路径。

## 13. 数据与 API 门禁

实现前建立 `LIVE / BACKEND_REQUIRED / DEFERRED` 矩阵。必须来自真实后端：

- 全局汇总；
- 资料统一查询与 facets；
- 来源树与节点计数；
- 最近打开资料；
- 活动任务和文档进度；
- 通用资料导入；
- 存储统计；
- Zotero 状态、集合和同步；
- 预览能力；
- 修复、重处理、删除动作。

后端未完成的能力不得用硬编码、localStorage 或当前页聚合冒充。控件可以显示为明确不可用，并保留验收失败状态。

## 14. 实现顺序

1. 读取 `DESIGN.md`、本规范、现有 Documents 组件和 API；
2. 建立截图区域到现有组件的复用/修改/新增矩阵；
3. 建立 AC→Vitest/Playwright 测试追溯；
4. 先统一路由、文案和数据类型；
5. 完成 Summary、ContextRail、Toolbar、Table；
6. 接入任务条、详情、导入和来源管理；
7. 补齐所有状态和响应式；
8. 运行视觉对照、键盘、屏幕阅读器和回归测试；
9. 不通过门禁不得宣称完美复刻。

## 15. 验收标准 AC-RL-01～20

1. **AC-RL-01** `/documents` 显示名、面包屑、标题和操作统一为资料库语义，旧路由有效。
2. **AC-RL-02** 页面结构在 1536×960 与参考图的主要区域边界偏差不超过 8px。
3. **AC-RL-03** 五项统计全部来自真实全库聚合，口径 Tooltip 正确，失败不显示假 0。
4. **AC-RL-04** 左侧顺序严格为全部、来源搜索、最近使用、资料来源、管理来源、可选存储。
5. **AC-RL-05** 本地、Obsidian、Zotero 树可键盘展开，节点数量采用统一去重口径。
6. **AC-RL-06** 左栏搜索只过滤来源树，并在清除后恢复原展开状态。
7. **AC-RL-07** 最近使用只由明确打开行为更新，点击不改变当前来源筛选。
8. **AC-RL-08** 来源节点选择写入 URL，刷新、后退、前进均恢复。
9. **AC-RL-09** 主搜索统一命中标题、正文、路径和来源，竞态响应不会覆盖新查询。
10. **AC-RL-10** 来源、类型、状态、更新时间、排序和 facets 在服务端分页前生效。
11. **AC-RL-11** 活动任务条和行内进度来自持久化任务，刷新后可恢复。
12. **AC-RL-12** 资料行状态、原因、主操作严格遵守状态映射，不解析错误文本猜状态。
13. **AC-RL-13** 批量选择、修复、重新处理和删除具有真实后端语义和冲突反馈。
14. **AC-RL-14** 分页总数、页码、每页数量准确，所有状态可深链接。
15. **AC-RL-15** PDF/DOCX 预览能力与后端一致；不支持格式诚实降级。
16. **AC-RL-16** 导入多文件逐项反馈，成功项进入处理任务，失败不影响成功项。
17. **AC-RL-17** Zotero 未连接、限流、附件缺失和同步失败均有真实、可恢复状态。
18. **AC-RL-18** 1280/328 等不同口径不能在无解释时同时出现；所有可见数量可追溯。
19. **AC-RL-19** 完整键盘路径、焦点恢复、对比度、live region 和 reduced motion 通过验收。
20. **AC-RL-20** typecheck、Vitest、production build、相关后端测试、Playwright 和视觉差异门禁全部通过。

## 16. 视觉复刻门禁

- 使用用户原始参考图建立 Playwright screenshot 基线；
- 固定测试视口至少包括 1536×960、1280×800、768×1024、390×844；
- 基线数据来自确定性 fixture server，不进入生产代码；
- 允许抗锯齿产生的微小像素误差，禁止通过提高阈值掩盖整体布局偏差；
- 对标题区、统计条、来源栏、工具条、任务条、表格、分页分别做区域截图；
- 空、加载、异常、处理中、Drawer、来源搜索结果均有视觉快照；
- 最终人工对照检查：层级、密度、文字截断、状态色、对齐和滚动行为。

## 17. Design Pre-Flight

### Identity lock

- [x] 仅使用 `.ulpi/design/DESIGN.md` 中的 palette、type、spacing、radius、motion。
- [x] 保持单一 accent、圆角、图标族和字体体系。
- [x] 与检索、推荐、阅读计划页面并排时仍属于同一产品。
- [x] 已先读取现有 DESIGN.md，没有引入视觉漂移。

### Anti-slop

- [x] 无紫蓝渐变、玻璃拟态、嵌套卡片、营销 Hero。
- [x] 无假数字、假来源、假进度和装饰状态点。
- [x] Signature 只用于真实来源路径和选中层级。
- [x] 页面特征来自科研资料溯源和状态诊断，不是通用后台模板。

### State and accessibility

- [x] 已覆盖 loading、empty、partial、error、offline、任务失败和 Zotero 降级。
- [x] 已定义树、菜单、Drawer、表格和 progress 的键盘及 ARIA 行为。
- [x] 沿用 DESIGN.md 中全部 WCAG 对比度和焦点约束。
- [x] 运动均有任务反馈目的，并支持 reduced motion。

### Scored critique

| 轴 | 分数（0–4） | 说明 |
|---|---:|---|
| distinctiveness | 3 | 来源路径线和资料状态诊断形成项目特征 |
| hierarchy & focus | 4 | 表格唯一主角，来源与统计服务于浏览 |
| consistency | 4 | 完全继承锁定设计语言 |
| accessibility | 4 | 关键复杂组件均有语义和键盘规范 |
| state coverage | 4 | 包含正常、异常、离线和外部来源降级 |
| copy quality | 4 | 专业、可诊断，无营销表达 |
| restraint | 4 | 只有真实层级、状态和操作进入页面 |
| motion motivation | 3 | 仅保留任务反馈、Drawer 和折叠过渡 |

总分：30/32，无轴 ≤2。无需引入额外视觉装饰。

## 18. Build Handoff

目标工程代理：Vue 3 / Vite 工程代理，并强制使用 `vue-best-practices`、`ui-design`、`frontend-a11y`、`acceptance-testing` 和 `playwright`。

实现指令：

> Implement exactly this spec. Theme Reka UI primitives with the locked tokens in `.ulpi/design/DESIGN.md`; do not redesign the page or re-implement accessible primitives. Reuse the existing `/documents` page and components where their behavior is correct. Replace product-facing “文档库” copy with “资料库” while preserving compatible routes and domain models. Never hard-code screenshot data. Every visible count, status, progress value, source node and action must come from a real API or an explicit unavailable state. Completion requires AC-RL-01～20 traceability and all validation gates passing.

