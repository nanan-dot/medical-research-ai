# 文献检索四级入口与检索中心流程执行提示词

## 1. 任务目标

在真实仓库 `D:\AI_project\rag_medicine` 中，完善现有 Vue 3 左侧导航的“文献检索”一级分组，并建立以下稳定流程：

```text
一级：文献检索（可展开/收起）
├─ 检索中心  → /literature-search（新检索中心入口页）
├─ 检索历史  → /literature-search/history
├─ 检索结果  → /literature-search/results（结果入口/最近结果状态）
└─ 文献推荐  → /recommendations

/literature-search
→ 用户输入研究问题并生成策略
→ parse-query → expand-terms → build-query
→ /literature-search/workspace（原检索中心工作台）
```

“检索中心工作台”不作为第五个二级菜单项。它属于“检索中心”的后续步骤；访问 `/literature-search/workspace` 时，侧边栏仍高亮“检索中心”。

## 2. 强制环境与工作树保护

开始前必须执行并记录：

```powershell
Set-Location -LiteralPath 'D:\AI_project\rag_medicine'
Get-Location
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
```

只有工作目录和 Git 根目录均为 `D:\AI_project\rag_medicine` 才能继续。

- 禁止访问或修改旧 `H:\AI_project\rag_medicine`。
- 所有未提交改动均视为用户重要工作。
- 禁止 `git reset`、`git checkout --`、`git clean`、覆盖、删除或全仓格式化。
- 禁止修改 `app/`、`alembic/`、`data/`、`uploads/`、`.env` 和系统配置。
- 禁止 commit、push、部署。

## 3. 必须阅读的事实源

1. `.ulpi/design/DESIGN.md`
2. `.ulpi/design/literature-search-entry.md`
3. `AGENTS.md`
4. `docs/CODE_STANDARDS.md`
5. `frontend/src/components/layout/AppSidebar.vue`
6. `frontend/src/config/features.ts`
7. `frontend/src/router/index.ts`
8. `frontend/src/router/route-meta.ts`
9. `frontend/src/components/layout/Breadcrumbs.vue`
10. `frontend/src/views/LiteratureSearch/` 下入口、工作台、历史和结果代码及测试
11. `frontend/src/views/Recommendations/RecommendationsView.vue`

本任务绑定现有 `technical / utilitarian` 产品设计语言。Every screen must read as the same product if placed side by side. 不新增第二套颜色、圆角、字体、阴影或图标体系。

## 4. 信息架构与路由语义

### 4.1 固定路由

| 菜单/状态 | 路由 | 页面职责 |
|---|---|---|
| 检索中心 | `/literature-search` | 新入口页，输入自然语言问题、选择模式、生成策略 |
| 检索中心工作台 | `/literature-search/workspace` | 保留原 `LiteratureSearchView`，编辑 PICO/术语/MeSH/布尔式并开始检索 |
| 检索历史 | `/literature-search/history` | 历史任务、恢复、重跑及结果入口 |
| 检索结果入口 | `/literature-search/results` | 无具体结果 ID 时的诚实结果入口状态 |
| 具体检索结果 | `/literature-search/results/:id` | 展示指定真实检索结果 |
| 文献推荐 | `/recommendations` | 现有真实推荐页 |

不得让 `/literature-search` 继续直接渲染原工作台；不得让入口页和工作台共享模糊的 Tab 状态。

### 4.2 检索结果无 ID 状态

当前具体结果页需要 `:id`。二级菜单“检索结果”必须有稳定可访问目标，禁止拼接虚构 ID。

按以下优先级实现：

1. 如果项目已有经过验证的最近结果 ID 来源，则跳转真实最近结果；
2. 否则为 `/literature-search/results` 提供职责独立的结果入口状态，说明“尚未选择检索结果”，并提供“打开检索历史”和“前往检索中心”操作；
3. 不得伪造结果、随机选择任务或把用户静默送到无关页面。

### 4.3 入口到工作台

`SearchEntryView` 只有在真实 `parse-query → expand-terms → build-query` 全部成功并形成类型化 handoff 后，才跳转：

```ts
router.push({
  path: "/literature-search/workspace",
  query: /* 项目真实、可刷新恢复的最小字段 */,
});
```

失败时停留入口页，保留问题和模式并允许重试。不得点击菜单就绕过入口直接进入工作台。

## 5. Sidebar 交互规格

### 5.1 一级分组

“文献检索”必须使用与现有“文档与知识”一致的分组交互模型，但不能复制粘贴第二份相同逻辑。应抽取小型、类型化的导航分组数据或复用现有扩展点。

- 一级行包含图标、文字和独立展开箭头。
- 点击文字区域进入 `/literature-search`。
- 点击箭头只展开/收起二级菜单，不触发路由跳转。
- 初始展开状态：当前路由属于任一文献检索子路由时强制可见；其他页面可使用当前会话内状态。
- 当前在 `/literature-search`、`/literature-search/workspace`、`/literature-search/history`、`/literature-search/results...` 或 `/recommendations` 时，一级“文献检索”显示分组激活态。
- Sidebar 全局收缩时隐藏文字与二级列表，只保留准确 Tooltip/ARIA 名称；恢复后保留合理展开状态。

### 5.2 四个二级项

顺序和可见文案固定：

```text
检索中心
检索历史
检索结果
文献推荐
```

激活规则：

```text
/literature-search                   → 检索中心
/literature-search/workspace         → 检索中心
/literature-search/history           → 检索历史
/literature-search/results           → 检索结果
/literature-search/results/:id       → 检索结果
/recommendations                     → 文献推荐
```

只能有一个二级项显示当前态。当前态必须同时使用背景、文字/图标和 `aria-current="page"`，不能只依赖颜色。

### 5.3 视觉要求

参考用户提供的导航截图：一级分组有浅蓝激活背景和右侧向上/向下箭头；二级区域使用细竖向路径线、缩进图标和紧凑行高。必须复用 `.ulpi/design/DESIGN.md` Token：

- Sidebar 宽度、一级高度、圆角与现有壳一致；
- 二级项左缩进与“文档与知识”一致；
- 图标统一使用项目图标体系，禁止 Unicode 方块、Emoji 或乱码图标；
- Hover、focus-visible、active、collapsed 状态清晰；
- 不新增阴影和渐变；
- 动画只用于 120–220ms 展开/箭头变化，并遵守 `prefers-reduced-motion`。

## 6. 面包屑和返回语义

修正 `route-meta.ts`，不得继续让入口页显示“检索工作区”。固定语义：

```text
/literature-search             → 文献检索 / 检索中心
/literature-search/workspace   → 文献检索 / 检索中心 / 检索工作台
/literature-search/history     → 文献检索 / 检索历史
/literature-search/results     → 文献检索 / 检索结果
/literature-search/results/:id → 文献检索 / 检索结果 / 结果详情（若现有规范需要）
/recommendations               → 文献检索 / 文献推荐
```

面包屑链接目标：

- “文献检索”进入 `/literature-search`；
- “检索中心”进入 `/literature-search`；
- “检索历史”进入 `/literature-search/history`；
- “检索结果”进入 `/literature-search/results`；
- 不再使用旧的 `/literature-search?tab=history` 作为主链接；旧链接必须兼容迁移到 `/literature-search/history`。

## 7. 旧链接兼容

全仓搜索所有 `/literature-search`、`tab=history`、结果返回、重跑、工作台恢复和推荐链接，形成迁移表。

- 旧 `/literature-search?tab=history` 明确 redirect 到 `/literature-search/history`，保留其他安全 query。
- 已有策略恢复、重跑或“修改策略”必须进入 `/literature-search/workspace`，不能丢到空入口页。
- 结果页普通“返回检索”若代表修改策略，应进入工作台；若代表开始新问题，应明确命名并进入入口页。
- 浏览器刷新、前进、后退和直接打开深链均保持语义一致。

## 8. 组件与代码结构

优先采用数据驱动的 Sidebar 分组，不把更多条件分支继续堆入单体模板。允许的最小范围：

```text
frontend/src/
├─ components/layout/
│  ├─ AppSidebar.vue
│  ├─ AppSidebar.test.ts
│  └─ NavigationGroup.vue          # 仅在确有复用价值时新增
├─ config/
│  └─ features.ts
├─ router/
│  ├─ index.ts
│  ├─ route-meta.ts
│  └─ 对应测试
├─ views/LiteratureSearch/
│  ├─ SearchEntryView.vue
│  ├─ LiteratureSearchView.vue
│  ├─ History.vue
│  ├─ ResultsIndexView.vue         # 无 ID 结果入口，若现有组件无法承担
│  └─ 相关测试
└─ components/layout/Breadcrumbs.vue 与测试
```

一个文件一个职责；Props/Emits/导航配置类型化；复杂逻辑添加解释设计原因的中文注释；禁止无意义抽象、重复路由常量和单行压缩 Vue SFC。

## 9. 可访问性

- 一级箭头是原生 `button`，具有 `aria-expanded`、`aria-controls` 和准确中文名称。
- 二级列表使用有意义的 `<nav>`/列表结构并有可访问名称。
- Tab 可遍历一级链接、展开按钮和四个二级链接。
- Enter/Space 激活按钮；链接保持原生 Enter 行为。
- Focus Ring 不得移除。
- 展开收起后焦点不丢失。
- 当前页使用 `aria-current="page"`。
- 移动/触摸目标至少 44×44px；紧凑桌面布局也不能低于项目可访问性标准。

## 10. 状态和边界

必须覆盖：

- 文献检索分组展开、收起、当前路由自动展开；
- 全局 Sidebar 收缩和恢复；
- 直接访问入口、工作台、历史、无 ID 结果、具体结果、推荐；
- 旧 `?tab=history`；
- 无历史、无最近结果、结果 ID 不存在；
- 从入口生成成功进入工作台；
- 生成失败仍停留入口；
- 浏览器刷新、后退、前进；
- 390px 移动视口无横向滚动。

## 11. 验收标准

```text
AC-NAV-01  文献检索一级项展示独立展开按钮
AC-NAV-02  点击一级文字进入 /literature-search 入口页
AC-NAV-03  点击箭头只切换四个子项，不发生路由跳转
AC-NAV-04  二级项严格按检索中心、检索历史、检索结果、文献推荐排序
AC-NAV-05  /literature-search 和 /workspace 均高亮检索中心
AC-NAV-06  /history 高亮检索历史
AC-NAV-07  /results 与 /results/:id 高亮检索结果
AC-NAV-08  /recommendations 高亮文献推荐
AC-NAV-09  当前二级项具有 aria-current=page
AC-NAV-10  收缩 Sidebar 后二级项隐藏，恢复行为正确
AC-NAV-11  /literature-search 渲染 SearchEntryView
AC-NAV-12  入口成功生成后进入 /literature-search/workspace
AC-NAV-13  /workspace 保留原 LiteratureSearchView
AC-NAV-14  /literature-search/results 无 ID 时呈现诚实入口状态
AC-NAV-15  旧 ?tab=history 兼容迁移到 /history
AC-NAV-16  历史恢复和重跑进入工作台而非空入口
AC-NAV-17  面包屑名称与链接符合第 6 节
AC-NAV-18  全流程支持键盘和焦点可见
AC-NAV-19  相关视口无横向溢出或菜单遮挡
AC-NAV-20  无未处理 console.error、pageerror 或路由警告
```

每条 AC 至少对应一个行为测试或真实浏览器验收。测试必须验证用户可观察行为，而非仅检查实现字符串。

## 12. 实施顺序

```text
1. 记录工作树并审计当前路由/链接
2. 建立 AC—测试追踪表
3. 先写导航和路由 RED 测试
4. 实现数据驱动文献检索导航分组
5. 增加无 ID 检索结果入口
6. 修正 route-meta 和 Breadcrumbs
7. 迁移旧 tab=history 与策略恢复链接
8. 验证入口 → 工作台真实流程
9. 运行定向与全量门禁
10. 启动真实前端做桌面与移动浏览器验收
```

## 13. 强制验证

必须实际运行：

```text
导航/路由/入口相关定向测试
npm test
npm run typecheck
本次相关文件 ESLint
npm run build
git diff --check
真实浏览器验收
```

不得运行不存在的脚本后声称通过。不得为清零全仓旧 ESLint 警告批量格式化无关文件。

## 14. 最终报告

最终依次提供：

1. 本次相关目录树；
2. 文件职责；
3. 四个二级菜单与路由映射；
4. 入口到工作台的数据流；
5. 旧链接迁移表；
6. AC—测试—结果追踪表；
7. 实际命令和结果；
8. 桌面/移动截图或浏览器验收证据；
9. `BACKEND_REQUIRED`、风险、`【未实测】` 和 `【未完成】`。

只有四项导航、入口到工作台、无 ID 结果状态、旧链接兼容、面包屑、可访问性和所有真实门禁全部通过后，才可声称本任务完成。
