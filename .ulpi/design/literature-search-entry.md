---
feature: literature-search-entry
design_language: .ulpi/design/DESIGN.md
reference_image: C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.2\前端设计1.1\预览图\文献检索\检索中心\检索中心询问图.png
implementation_prompt: C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.2\前端设计1.1\预览图\文献检索\检索中心\检索中心入口页提示词.md
target: vue-vite-engineering-task
---

# 检索中心入口页锁定规格

## Design Read

医学检索仪器面板：在现有科研工作台壳层中，用清晰的研究问题入口和可解释的四阶段路径建立可信、克制且高效的首屏。

审美方向锁定为 `technical / utilitarian`。本页不重新设计产品视觉语言，严格绑定 `.ulpi/design/DESIGN.md`。Every screen must read as the same product if placed side by side.

## Signature

复用全产品“证据路径线”，在本页表现为从研究问题到理解意图、构建策略、开始检索的四阶段路径。节点只表达真实状态，不作为装饰。

## 主流程

```text
进入 /literature-search
→ 输入或选择示例研究问题
→ 选择后端真实支持的模式
→ parse-query
→ expand-terms
→ build-query
→ 类型化 handoff
→ /literature-search/workspace
```

刷新、返回、请求失败、重复提交、过期响应和交接失败必须遵循实施提示词第 212、214 章的状态规则。

## 组件边界

- `SearchEntryView`：页面编排与路由衔接。
- `SearchEntryHero`：标题、说明和装饰插画。
- `SearchEntryUtilityLinks`：只呈现真实可达工具入口。
- `SearchProcessIndicator`：可访问的四阶段状态。
- `ResearchQuestionComposer`：问题输入、计数、示例菜单和提交区域组合。
- `SearchModeSelector`：类型化、键盘可操作的模式选择。
- `SearchGeneratingState`：真实请求阶段和错误恢复。
- `QuickStartTemplates`：只预填问题与模式，不自动提交。
- `SearchTrustBar`：可证实的来源与可追溯性说明。
- `useSearchStrategyCreator`：请求顺序、取消、竞态、重试与 handoff。

## 状态覆盖

必须覆盖 idle、输入无效、示例菜单、模式禁用、parse、expand、build、handoff、失败、重试、卸载、刷新边界、窄屏和 reduced-motion。任何网络失败都保留原问题与用户选择。

## 可访问性

一个 `h1`；Textarea 使用可见 Label 和关联说明；模式使用 radio 语义；阶段变化使用克制 `aria-live`；菜单支持 Escape 和焦点恢复；全流程键盘可达；焦点对比满足 WCAG AA；移动端点击目标不少于 44px。

## 视觉验收

1536×1024 以原始参考图为唯一局部视觉事实源，执行提示词第 214 章的坐标阈值和持续 Overlay/Diff 迭代。其他五视口验证响应式，不要求机械缩放桌面版。

## Build Handoff

在 `D:\AI_project\rag_medicine` 的现有 Vue 3 + Vite 项目中实现此规格。复用现有组件体系和锁定 Token，不重新设计、不创建第二套应用壳、不改写后端。每条 `AC-ENTRY-01` 至 `AC-ENTRY-16` 建立测试映射；未通过测试和视觉门禁不得宣称完成。

## Design Pre-Flight

- 身份锁：绑定现有 `DESIGN.md`，无新增主色、圆角、字体或图标族。
- 反模板化：构图来自给定产品参考图，不引入通用营销页模式。
- 状态：完整覆盖成功、错误、恢复与竞态。
- 可访问性：对比、键盘、焦点、ARIA 和 reduced-motion 均为硬门禁。
- 认知负荷：页面只保留一个主 CTA，六种模式作为单一决策组渐进说明。
- 自评：distinctiveness 3、hierarchy 4、consistency 4、accessibility 4、state coverage 4、copy 3、restraint 4、motion 4；总分 30/32，无轴低于 3。
