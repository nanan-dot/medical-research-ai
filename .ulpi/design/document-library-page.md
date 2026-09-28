# 文档库页面完整实现提示词

> 工作包：FE-R2 / 文档与知识 / 文档库  
> 页面路由：`/documents`  
> 视觉参考：`C:\Users\ADMIN\AppData\Local\Temp\codex-clipboard-3133e484-6422-4b67-aa87-fb68d1150b92.png`  
> 设计语言：`H:\AI_project\rag_medicine\.ulpi\design\DESIGN.md`  
> 仓库：`H:\AI_project\rag_medicine`

## 0. 执行声明

在真实仓库中完整实现图片所示的文档库页面。该任务不是静态HTML、Demo、截图临摹或纯视觉稿。

图片只定义视觉层级、密度、布局关系和交互入口，不代表真实数据。图片中的328、301、8、19、128、文件名、用户名、时间和进度均为示例，不得硬编码。

Every screen must read as the same product if placed side by side.

实现前必须完整读取：

```text
AGENTS.md
docs/CODE_STANDARDS.md
.ulpi/design/DESIGN.md
.ulpi/design/frontend-rebuild-execution.md
```

必须使用：

- Vue 3 Composition API；
- `<script setup lang="ts">`；
- Vue Router；
- 项目现有API客户端；
- `vue-best-practices`；
- `frontend-design` / `ui-design`；
- `acceptance-testing`；
- 复杂Drawer、Menu、Select优先使用已选定的Reka UI原语或等价原生无障碍实现。

本任务先建立AC测试映射，新行为测试确认RED后再实现。没有通过测试不得宣称完成。

---

## 1. 页面目标

帮助医学科研用户在一个高密度工作区内完成四件事：

1. 确认当前知识来源；
2. 搜索和筛选文档；
3. 判断文档能否用于证据问答；
4. 对异常文档执行真实修复。

页面主角是文档表格。来源导航、统计和详情都必须为文档浏览服务，不能抢占主区域。

---

## 2. 范围和边界

### 必须实现

- 与参考图一致的应用壳层衔接；
- 面包屑、标题、副标题；
- 四项真实统计；
- 全部文档和来源浏览；
- 来源分组与来源切换；
- 当前来源上下文；
- 文档搜索；
- 搜索模式选择；
- 类型、状态、排序筛选；
- 文档表格；
- 用户级状态；
- 查看文档；
- 统一修复入口；
- More菜单；
- 批量选择和真实可用的批量操作；
- 分页和每页条数；
- 文档详情Drawer；
- Loading、空状态、错误和部分失败；
- URL状态恢复；
- 桌面、平板和移动端；
- 键盘、焦点和屏幕阅读器支持。

### 明确禁止

- 在文档库添加知识来源或上传文档；
- 永久右侧详情栏；
- 解析状态和索引状态各占一列；
- 用Mock填补接口失败；
- 根据当前页计算全库统计；
- 浏览器加载全量后伪造服务端分页、筛选和排序；
- 使用随机进度；
- 删除用户源文件；
- 在未清洗内容上使用 `v-html`；
- 为了贴图硬编码示例数据。

---

## 3. 后端前置能力门禁

完整页面依赖以下真实能力。实施前逐项检查代码和OpenAPI，建立 `LIVE / BACKEND_REQUIRED / DEFERRED` 矩阵。

### 3.1 文档汇总

目标：

```http
GET /api/v1/documents/summary
```

响应：

```ts
interface DocumentLibrarySummary {
  total: number;
  available: number;
  processing: number;
  needs_attention: number;
}
```

必须是数据库全量聚合，不受分页影响。

如果后端已有等价知识库Summary，可以复用，但字段定义必须一致，不允许拼当前页。

### 3.2 文档分页查询

目标参数：

```text
q: string|null，最大200
search_mode: document|content
knowledge_source_id: int|null
file_type: pdf|pptx|docx|markdown|txt|other|null
health_status: available|processing|needs_attention|null
sort_by: updated_at|name|file_size
sort_order: asc|desc
offset: int>=0
limit: 10|25|50|100，默认25
```

响应：

```ts
interface DocumentPage {
  items: DocumentListItem[];
  total: number;
  offset: number;
  limit: number;
}
```

全部过滤和排序必须在数据库分页之前执行，稳定排序必须最终使用Document.id作为tie-breaker。

### 3.3 列表项契约

```ts
type DocumentHealthStatus = "available" | "processing" | "needs_attention";

type DocumentIssueType =
  | "parse_failed"
  | "index_failed"
  | "index_outdated"
  | "source_file_missing"
  | "source_unavailable"
  | "unsupported_format"
  | "other";

interface DocumentListItem {
  id: number;
  knowledge_source_id: number;
  source_name: string;
  file_name: string;
  file_path: string;
  file_type: "pdf" | "pptx" | "docx" | "markdown" | "txt" | "other";
  media_type: string | null;
  file_size: number;
  modified_time: string;
  health_status: DocumentHealthStatus;
  health_reason: string;
  issue_type: DocumentIssueType | null;
  progress: number | null;
  available_actions: Array<
    "view" | "repair" | "retry_parse" | "rebuild_index" | "view_source"
  >;
  parse_status?: string;
  index_status?: string;
}
```

后端暂未返回统一状态时，只能在单一纯函数中集中映射旧字段；统计、表格和Drawer必须共用同一映射。

### 3.4 修复

推荐：

```http
POST /api/v1/documents/{id}/repair
```

响应返回更新后的文档或持久化任务信息。相同文档已有活动修复时不得重复产生副作用。

若后端只提供 `retry-parse` 与 `retry-index`，前端可以根据结构化 `issue_type` 调用对应接口，但映射必须集中，不得解析错误消息猜测。

### 3.5 详情与正文定位

详情Drawer至少依赖：

```http
GET /api/v1/documents/{id}
GET /api/v1/documents/{id}/content-summary
```

正文搜索如需要定位，响应必须包含真实页码、幻灯片或章节定位；没有定位字段时不显示虚假定位。

### 3.6 缺失能力处理

如果核心后端能力缺失：

1. 不得用前端本地数据冒充；
2. 在报告中标记 `BACKEND_REQUIRED`；
3. 若本工作包禁止后端修改，隐藏对应控件或显示明确不可用状态；
4. 不能同时声称“完整功能实现”；
5. 视觉页面可以完成，但功能验收保持未通过。

---

## 4. 桌面布局精确规格

参考图按约1000×674比例展示，实际实现需要流式适配。

### 4.1 应用总体

```text
viewport
├─ 主导航侧栏：148～160px（实际项目可锁160px）
└─ 内容区：剩余宽度
```

在1440px视口推荐：

```text
主导航：220px
内容左右内边距：24px
内容最大宽度：无固定窄容器，使用可用工作区
```

不得使用居中1200px窄容器导致右侧浪费。数据工作台应尽量使用可用宽度。

### 4.2 顶部全局栏

高度：52～56px。

内容：

- 左侧面包屑“文档与知识 / 文档库”；
- 右侧全局搜索，宽度约320px；
- `Ctrl K` 快捷键提示；
- 通知按钮；
- 用户头像和菜单。

全局搜索不是文档列表搜索，两者视觉权重必须区分：全局搜索更窄、更淡；文档搜索位于主工作区并承担本页查询。

### 4.3 页面标题

```text
文档库
查看知识来源同步产生的科研文档，支持文档检索、正文定位、状态确认与问题修复。
```

标题：28px/36px，700。  
副标题：13～14px，muted。  
标题区下边距：16px。

### 4.4 状态条带

四列等宽，间距12px，高度78～88px。

每项结构：

```text
[语义图标圆形底]
主要数字
标签
可选次级操作
```

状态：

- 全部文档：accent；
- 可用于问答：success；
- 处理中：info；
- 需处理：warning，并可显示“查看详情”。

不是营销卡片，不使用大阴影。边框+白色表面+轻微shadow-sm。

点击状态条带：

- “全部文档”清空状态筛选；
- 其他三项设置health_status；
- 当前选中项有2px路径线或accent-soft背景；
- 更新URL并回到第1页。

### 4.5 主体双栏

```text
┌───────────────┬────────────────────────────────────────────┐
│ 来源导航      │ 文档工作区                                 │
│ 200～220px    │ minmax(0,1fr)                              │
└───────────────┴────────────────────────────────────────────┘
```

列间距：16px。  
顶部与状态条带间距：16px。  
两栏表面高度随内容，不强制与视口完全等高，但桌面端至少覆盖当前表格。

---

## 5. 主导航侧栏

主导航属于全局AppShell，不在文档库feature内重复实现。

结构顺序：

```text
品牌
工作台
文献检索（可展开）
文档与知识（展开）
  知识库
  文档库（当前）
检索中心
检索结果
文献推荐
检索历史
分割线
论文研究
多论文证据
研究设计
写作与汇报
分割线
后台任务
设置
底部用户区
```

要求：

- 当前文档库用accent-soft背景和accent文字；
- 父组“文档与知识”保持展开；
- 图标统一16～18px线性风格；
- 导航文本13～14px；
- 行高40～44px；
- 支持键盘、aria-current和折叠状态；
- 不能因页面内容滚动而丢失底部用户入口；
- 移动端变为Drawer。

---

## 6. 来源导航组件

组件：`KnowledgeSourceSidebar.vue`

宽度：200～220px。背景surface。圆角lg。边框border。禁止强阴影。

### 6.1 顶部

```text
知识来源                       «
```

- 标题16px/24px，600；
- 收起按钮有aria-label；
- 收起后主工作区扩展；
- 收起状态可保存在localStorage，但URL不必记录。

### 6.2 最近使用

最多1～3项：

```text
最近使用
★ ILD 核心文献                     128
```

只有后端存在真实最近使用字段时展示；否则整段隐藏。

### 6.3 来源分组

```text
知识来源
▼ 本地文件夹 (5)
   ILD 核心文献                     128
   IPF 临床试验资料                  47
   肺癌 Biomarker 研究               89
   CTD-ILD Guidelines                32
   临床病例记录                      64

▼ Obsidian Vault (3)
   ILD Research Vault               236
   IPF Notes Vault                  112
   ILD 影像资料库                    28
```

数字含义：分组括号是来源数量，来源末尾是文档数量。

选中来源：

- 左侧2px accent路径线；
- accent-soft背景；
- accent文字；
- 数字保持可读；
- 设置 `aria-current="page"` 或等价状态。

来源项长名称使用单行省略，并通过title或Tooltip提供完整名称。

### 6.4 底部

```text
⚙ 管理知识来源
```

跳转知识库，不在文档库直接编辑来源。

### 6.5 状态

- loading：固定宽度骨架行；
- empty：提示先前往知识库添加来源；
- error：只影响来源栏，提供重试；
- unavailable source：仍允许显示，但使用“不可访问”辅助状态；
- source deleted：从URL回退全部文档并通知。

---

## 7. 文档工作区

组件：`DocumentLibraryPanel.vue`

背景surface，圆角lg，边框border，overflow hidden。

### 7.1 当前来源栏

高度52～56px，左右16px。

```text
[文件夹图标] ILD 核心文献 · 128篇               查看知识来源 ↗
```

- 左侧来源名称16px，600；
- 数量13px muted；
- 右侧为文字链接，不是主按钮；
- 全部文档模式显示“全部文档 · N篇”，右侧可不显示来源链接；
- 不展示路径、可用度或大插画。

### 7.2 搜索行

上边距16px，左右16px。

```text
[搜索图标] 搜索文档标题、正文内容、文件路径…   [搜索方式：文档 ▼]
```

搜索输入占剩余宽度，模式Select宽128～144px，间距12px，高度40px。

交互：

- 输入防抖300ms；
- Enter立即搜索；
- Esc清空建议或关闭弹层，不直接清空已提交查询；
- 清除按钮只在有内容时出现；
- 超长查询前端限制200字符，后端仍需校验；
- 搜索请求支持AbortController或请求序号；
- 文档模式placeholder根据范围变化；
- 正文模式明确“搜索解析后的正文内容”。

### 7.3 筛选行

位于搜索下方12px：

```text
类型：[全部类型 ▼]  状态：[全部状态 ▼]  排序：[最近更新 ▼]
```

控件高度34～36px，标签12～13px，Select最小104px。

选项：

```text
类型：全部、PDF、PPTX、DOCX、Markdown、TXT、其他
状态：全部、可用于问答、处理中、需处理
排序：最近更新、最早更新、文件名A-Z、文件名Z-A、文件大小从大到小、文件大小从小到大
```

不支持的选项不得显示为可用。

---

## 8. 文档表格

组件拆分：

```text
DocumentTable.vue
└─ DocumentRow.vue
```

表格位于筛选区下方16px。表头背景使用轻微tinted neutral，不使用深色表头。

列：

```text
40px选择框
minmax(320px,1fr)文档信息
190px状态
150px更新时间
120px操作
```

在较窄桌面按比例收缩，但文档信息不得小于主可读宽度。

### 8.1 表头

- 复选框有“选择当前页全部文档”标签；
- 文档信息、状态、更新时间、操作；
- 表头12px muted，600；
- 高度40～44px。

### 8.2 行

桌面行高72～80px，左右12～16px。用底边分割，不把每行做成卡片。

文档单元格：

```text
[文件类型图标 36×36]
文件名：14px/20px，600，text
来源：12px/18px，muted
类型 · 格式化大小：12px/18px，subtle
```

文件类型图标：

- PDF可使用克制红色；
- DOCX/PPTX可使用不同深浅蓝；
- 其他类型使用中性灰；
- 图标背景为极浅语义色；
- 图标仅辅助，文件类型仍以文本显示。

### 8.3 状态单元格

可用于问答：

```text
✓ 可用于问答
内容处理已完成
```

处理中：

```text
● 处理中
建立问答索引
[真实progress存在时] 65% + 80px进度条
```

需处理：

```text
! 需处理
索引建立失败 / 解析失败 / 来源文件不可访问
```

要求：

- 状态文字13px，600；
- 原因12px muted；
- 进度条高度4px；
- progress必须0～100且来自后端；
- 未返回progress则不显示百分比或进度条；
- 状态同时有图标与文字，不能只用颜色。

### 8.4 更新时间

- 使用Intl.DateTimeFormat统一格式；
- 显示用户本地时区；
- 数字使用utility字体或tabular-nums；
- 完整ISO时间放在可访问title/Tooltip；
- 空时间显示“尚未同步”，不显示假日期。

### 8.5 操作

正常文档：`查看文档`。  
异常文档：`修复`。  
处理中：通常只显示More菜单。

按钮使用outline/small，不使用实心大蓝按钮。More为图标按钮，aria-label包含文件名。

More菜单根据真实可用动作显示：

```text
查看详情
查看知识来源
重新处理
重新建立索引
从问答资产中排除（仅后端真实支持时）
```

没有真实删除源文件设计时，不显示“删除文档”。

### 8.6 选择

- 点击复选框不打开详情；
- 表头全选只选当前页；
- 筛选、来源、搜索、排序变化时清空选择；
- 默认翻页清空选择；
- 选中后在表格上方显示批量工具栏；
- 批量工具栏不改变表格宽度。

---

## 9. 分页

底部高度52～56px，左右16px。

```text
共128篇文档              ‹ 1 2 3 4 5 … 9 ›              25条/页
```

规则：

- 页码从1开始；
- 后端使用offset时正确转换；
- 默认25；
- 可选10、25、50、100；
- 页数多时使用省略号；
- 当前页accent实心，其他页透明；
- 首尾页禁用相应箭头；
- 改每页条数回到第1页；
- total变化导致越界时回到最后有效页；
- 每个按钮有明确aria-label；
- 更新URL。

---

## 10. 文档详情Drawer

点击文档名、查看文档或查看详情打开临时Drawer，不使用永久Inspector。

桌面宽度440～480px；小于640px时全宽。

内容：

```text
文档详情                                ×
[类型图标] 文件名
来源名称 + 查看知识来源

当前状态
状态标签 + 解释

处理流程
原文件可访问
内容解析
问答索引
可用于问答

问题原因（异常时）
安全错误摘要
[修复问题]

文件信息
类型、大小、更新时间、相对路径

[打开完整文档详情]
```

焦点与键盘：

- 打开时保存触发元素并将焦点移入；
- Tab/Shift+Tab限制在Drawer；
- Esc关闭；
- 关闭后焦点返回触发按钮；
- 背景不可交互；
- body滚动锁定并正确恢复；
- `role=dialog`、`aria-modal=true`、关联标题；
- reduced motion关闭位移动画。

详情加载失败只影响Drawer，主表格保持。

---

## 11. URL状态

```text
/documents
?view=source
&sourceId=1
&mode=document
&q=
&type=all
&status=all
&sort=updated_desc
&page=1
&pageSize=25
&documentId=42
```

规则：

- URL是可分享查询状态；
- 初始化从URL读取；
- 浏览器前进后退恢复；
- 无效参数归一化；
- `documentId`存在时打开Drawer；
- 关闭Drawer移除documentId但保留列表状态；
- 输入防抖期间不为每个字符push历史；
- 筛选使用replace；
- 主动切换来源可push；
- 防止URL watcher和内部watch循环触发重复请求。

---

## 12. Vue组件结构

```text
frontend/src/features/document-library/
├─ api/
│  └─ documentLibraryApi.ts
├─ components/
│  ├─ DocumentLibraryHeader.vue
│  ├─ DocumentSummaryStrip.vue
│  ├─ KnowledgeSourceSidebar.vue
│  ├─ ResponsiveSourceSelector.vue
│  ├─ DocumentLibraryPanel.vue
│  ├─ DocumentSearchBar.vue
│  ├─ DocumentFilterBar.vue
│  ├─ DocumentBulkToolbar.vue
│  ├─ DocumentTable.vue
│  ├─ DocumentRow.vue
│  ├─ DocumentStatus.vue
│  ├─ DocumentPagination.vue
│  ├─ DocumentDetailDrawer.vue
│  └─ DocumentTableSkeleton.vue
├─ composables/
│  ├─ useDocumentLibraryQuery.ts
│  ├─ useDocumentSelection.ts
│  ├─ useDocumentRepair.ts
│  ├─ useDocumentStatusPolling.ts
│  └─ useKnowledgeSourceNavigation.ts
├─ model/
│  ├─ documentLibraryTypes.ts
│  ├─ documentHealth.ts
│  └─ documentLibraryQuery.ts
└─ views/
   └─ DocumentLibraryView.vue
```

职责：

- View只组合；
- Query composable管理URL、分页、请求取消和列表状态；
- Selection composable管理选择生命周期；
- Repair composable只负责修复命令与刷新；
- Polling composable只在可见processing项存在时工作；
- 纯状态映射放model，不包装成composable；
- state只通过显式action修改；
- composable向外返回readonly状态；
- 大数组替换使用合适ref/shallowRef；
- computed保持纯函数；
- watcher只承担副作用并清理旧异步任务；
- Props Down / Events Up；
- 所有props、emits和API返回完整类型；
- 禁止 `any` 和大面积 `as unknown as`。

---

## 13. Loading、空状态和错误

### 首次加载

- 保留标题、搜索和主体骨架结构；
- 统计条带使用固定高度Skeleton；
- 来源栏使用6～8条Skeleton；
- 表格使用6条Skeleton row；
- 不显示全屏Spinner。

### 刷新

- 保留旧数据；
- 显示轻量refreshing状态；
- 禁止整个页面闪白。

### 整个文档库为空

```text
还没有可浏览的科研文档
请先在知识库中添加并同步知识来源。
[前往知识库]
```

### 当前来源为空

```text
当前知识来源暂无文档
文档由知识来源同步产生。
[查看知识来源]
```

### 搜索无结果

```text
没有找到匹配文档
尝试修改关键词、搜索方式或筛选条件。
[清除搜索和筛选]
```

### 没有异常

```text
当前没有需要处理的文档
所有文档状态正常。
```

### 错误

```text
文档列表暂时无法加载
[重新加载]
```

错误不能包含绝对路径、数据库堆栈、密钥或敏感医学内容。错误区域使用 `role=alert`。

---

## 14. 状态轮询

当前页存在processing文档时：

1. 优先查询真实任务状态；
2. 没有推送机制时每5～10秒有界轮询；
3. 页面隐藏时暂停或降频；
4. 所有当前项进入终态后停止；
5. 网络失败指数退避；
6. 组件卸载清理timer和请求；
7. 不重置选择、页码、筛选和滚动位置；
8. 不使用轮询伪造progress增长。

---

## 15. 响应式

### ≥1280px

- 完整主导航；
- 四列统计条带；
- 200～220px来源栏；
- 完整表格列。

### 1024～1279px

- 主导航按AppShell策略缩窄；
- 来源栏约190px；
- 更新时间列可压缩；
- 搜索模式保持独立Select。

### 768～1023px

- 来源栏隐藏，顶部使用来源选择器；
- 统计2×2；
- 更新时间列隐藏；
- 文档、状态、操作保留；
- 搜索和模式选择器可换行。

### <768px

- 主导航使用Drawer；
- 统计2×2或水平滚动状态条，但不得截断数字；
- 表格转换成语义化文档行卡片；
- 文档信息、状态、操作纵向排列；
- 来源选择器全宽；
- Drawer全屏；
- 分页简化为上一页、当前页、下一页和page size；
- 所有触控目标至少44px；
- 页面整体无横向滚动。

必须截图验证：1440×900、1024×768、768×1024、390×844。

---

## 16. 无障碍

- 页面一个h1；
- 表格使用真实table、thead、th scope或移动端等价语义；
- 输入和Select都有可见或可关联label；
- 图标按钮有aria-label；
- 当前来源和当前页不只靠颜色；
- 状态含图标+文本；
- 键盘可完成来源切换、搜索、筛选、表格选择、操作菜单、分页和Drawer；
- 焦点环使用DESIGN.md token；
- 动态结果数量使用 `aria-live=polite`；
- 紧急错误使用 `role=alert`；
- Decorative icon使用aria-hidden；
- 文档标题截断时仍可访问完整名称；
- Drawer符合焦点管理要求；
- reduced motion有效；
- 不使用positive tabindex；
- 不在div上模拟button。

---

## 17. 验收标准

每项必须映射自动化测试。新增测试先RED后GREEN。

### AC-01 视觉骨架

Given 1440px视口；When页面加载完成；Then存在主导航、标题、四项统计、来源栏、搜索筛选、文档表格和分页，主工作区无明显空洞。

### AC-02 真实统计

Given总文档超过一页；When查看统计；Then数字来自全库聚合而非当前页。

### AC-03 来源筛选

Given URL有有效sourceId；When页面打开；Then来源选中且文档请求包含knowledge_source_id。

### AC-04 来源切换

Given用户切换来源；Then页码归1、选择清空、旧请求不能覆盖新来源结果。

### AC-05 搜索竞争

Given连续输入A和B；WhenA晚于B返回；Then界面仍显示B结果。

### AC-06 服务端文件类型筛选

Given选择PDF；Then请求带file_type=pdf，total来自完整筛选集。

### AC-07 用户状态筛选

Given选择需处理；Then只显示needs_attention文档且统计和列表语义一致。

### AC-08 稳定排序

Given多项更新时间相同；When连续翻页；Then无重复、无遗漏。

### AC-09 URL恢复

Given完整query URL；When刷新；Then来源、搜索、筛选、排序、页码、pageSize和Drawer恢复。

### AC-10 浏览器历史

Given切换来源和筛选；When前进/后退；Then状态恢复且不产生请求循环。

### AC-11 可用于问答

Givenparse和index成功；Then显示可用于问答与查看文档。

### AC-12 处理中真实性

Givenprocessing但后端无progress；Then不显示虚假百分比；有progress时显示真实值。

### AC-13 需处理映射

Givenparse_failed、index_failed、index_outdated和source missing；Then统一显示需处理及正确原因。

### AC-14 修复幂等

Given连续点击修复；When首请求未完成；Then按钮禁用且没有第二次副作用。

### AC-15 修复更新

Given修复成功；Then行、统计和Drawer同步更新；失败则保留问题状态。

### AC-16 当前页选择

Given表头全选；Then只选当前页；切换筛选或来源后选择清空。

### AC-17 分页

Given修改pageSize；Then回到第1页，URL和请求limit一致。

### AC-18 空状态

Given空库、空来源、无搜索结果和无异常；Then分别显示四种正确文案。

### AC-19 错误真实性

GivenAPI失败；Then显示错误和重试，不出现Mock文档。

### AC-20 Drawer焦点

Given键盘打开详情；Then焦点进入、Tab不逃逸、Esc关闭、焦点返回。

### AC-21 More菜单

Given键盘打开菜单；Then可选择真实可用操作并用Esc关闭。

### AC-22 响应式

Given1440、1024、768、390视口；Then核心操作可达且页面无整体横向溢出。

### AC-23 安全渲染

Given文件名或搜索片段含HTML字符；Then按纯文本显示，不执行脚本。

### AC-24 路由兼容

Given旧 `/documents`、`/documents/:id` 和其他模块跳转；Then继续可用或有明确兼容重定向。

### AC-25 离线测试

Given默认测试；Then不访问真实网络、云模型、Ollama和用户医学目录。

---

## 18. 测试文件建议

```text
frontend/src/features/document-library/views/DocumentLibraryView.test.ts
frontend/src/features/document-library/components/DocumentSummaryStrip.test.ts
frontend/src/features/document-library/components/KnowledgeSourceSidebar.test.ts
frontend/src/features/document-library/components/DocumentSearchBar.test.ts
frontend/src/features/document-library/components/DocumentTable.test.ts
frontend/src/features/document-library/components/DocumentStatus.test.ts
frontend/src/features/document-library/components/DocumentPagination.test.ts
frontend/src/features/document-library/components/DocumentDetailDrawer.test.ts
frontend/src/features/document-library/composables/useDocumentLibraryQuery.test.ts
frontend/src/features/document-library/composables/useDocumentRepair.test.ts
frontend/src/features/document-library/model/documentHealth.test.ts
frontend/src/app/router.test.ts
```

如项目已有对应测试位置，优先延续现有目录约定，避免无意义迁移。

---

## 19. 实施顺序

1. 读取DESIGN.md和代码规范；
2. 检查视觉参考；
3. 审计旧页面、API、路由和测试；
4. 输出能力矩阵；
5. 输出组件图和URL模型；
6. 建立AC-01～AC-25追踪表；
7. 写失败测试并记录RED；
8. 建立类型、API和状态纯函数；
9. 实现Query composable；
10. 实现页面骨架与统计；
11. 实现来源栏；
12. 实现搜索、筛选和分页；
13. 实现表格、状态和选择；
14. 实现修复与轮询；
15. 实现Drawer和More菜单；
16. 实现全部状态和响应式；
17. 做键盘和焦点检查；
18. 截图比较参考图；
19. 修复视觉偏差；
20. 运行全部门禁并输出报告。

---

## 20. 验证命令

```powershell
Set-Location H:\AI_project\rag_medicine\frontend
npm test
npm run typecheck
npm run build
```

如 `package.json` 有lint：

```powershell
npm run lint
```

如果本次获准补后端前置能力：

```powershell
Set-Location H:\AI_project\rag_medicine
$env:PYTHONPATH = ""
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m pytest
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m ruff check app tests alembic
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m mypy app
```

未执行的命令不得声称通过。

---

## 21. Design Pre-Flight

- [x] 页面绑定唯一DESIGN.md；
- [x] 技术/实用主义方向与医学科研工作台一致；
- [x] 使用一个accent和证据路径线Signature；
- [x] 禁止渐变发光、玻璃拟态、嵌套卡片和假数据；
- [x] 文档表格是唯一视觉主角；
- [x] Loading、empty、partial、error、success均有定义；
- [x] 键盘、焦点、ARIA和reduced motion完整；
- [x] 桌面、平板和移动端行为明确；
- [x] 所有核心交互均有验收标准；
- [x] 复杂信息使用Drawer和Menu渐进披露。

自评：distinctiveness 3、hierarchy 4、consistency 4、accessibility 4、state coverage 4、copy 3、restraint 4、motion 4，总分30/32，无维度低于3。

---

## 22. Build Handoff

目标：Vue 3 / Vite高级前端工程代理；如获准补接口，再由FastAPI工程代理完成BACKEND_REQUIRED项。

执行指令：

> Implement exactly this spec. Theme Reka UI or native semantic primitives with the locked tokens in `.ulpi/design/DESIGN.md`; do not redesign, do not hardcode screenshot data, and do not simulate missing backend behavior. Prove each new acceptance test RED then GREEN. The page is complete only when AC-01 through AC-25 and all repository gates pass.

最终报告必须包含：

```markdown
# 文档库页面实施结果
## 能力矩阵
## 修改文件
## 组件结构
## API与URL
## 状态映射
## Acceptance Traceability
## 测试与构建结果
## 四视口截图
## BACKEND_REQUIRED
## DEFERRED
## 已知限制与未实测项
```
