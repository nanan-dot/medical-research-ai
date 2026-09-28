---
feature: literature-search-navigation
register: product
aesthetic_direction: technical / utilitarian
design_system: existing Vue primitives bound to .ulpi/design/DESIGN.md
visual_density: 8
motion_intensity: 2
---

# 文献检索导航锁定规格

## Design Read

科研路径索引：用一条紧凑、可追踪的二级导航把“提出问题、回看历史、查看结果、获得推荐”组织为稳定工作流。

Every screen must read as the same product if placed side by side.

## Signature

复用现有“证据路径线”：二级导航左侧细竖线只表达所属层级，选中态节点表达当前位置，不增加装饰性图形。

## Flow

```text
文献检索 / 检索中心入口
→ 生成真实策略
→ 检索中心工作台
→ 执行检索
→ 检索结果
→ 历史回看或文献推荐
```

## Component Brief

`AppSidebar` 只负责组合导航数据；文献检索分组提供一级链接、独立展开按钮和四个二级链接。当前路由决定唯一激活项。复杂的路径匹配集中为纯函数或类型化配置，不散落在模板条件中。

状态：default、hover、focus-visible、group-active、page-active、expanded、collapsed。展开动画采用锁定 motion Token；reduced-motion 下即时切换。

## Accessibility

展开按钮具备 `aria-expanded` 和 `aria-controls`；当前页具备 `aria-current=page`；键盘焦点顺序与视觉顺序一致；收缩与恢复不丢失焦点；二级目标在移动端不少于 44px。

## Build Handoff

在 `D:\AI_project\rag_medicine` 的现有 Vue 3 项目中严格执行 `docs/frontend/LITERATURE_SEARCH_NAVIGATION_EXECUTION_PROMPT.md`。复用锁定 Token 和现有应用壳，不重新设计组件体系。完成前必须让 AC-NAV-01 至 AC-NAV-20 全部有真实测试证据。

## Pre-Flight

- Identity lock：沿用现有颜色、字体、圆角、图标和路径线。
- Anti-slop：无新渐变、阴影、卡片或装饰状态点。
- States：展开、收起、当前态、空结果、深链和兼容路径完整。
- Accessibility：键盘、焦点、ARIA、触摸目标均为硬门禁。
- Cognitive load：一个一级分组、四个稳定子项，无第五个工作台菜单。
- Self-critique：distinctiveness 3、hierarchy 4、consistency 4、accessibility 4、state coverage 4、copy 4、restraint 4、motion 4，总分 31/32，无轴低于 3。
