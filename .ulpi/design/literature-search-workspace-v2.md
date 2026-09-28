---
feature: literature-search-workspace-v2
register: product
aesthetic_direction: technical / utilitarian
design_system: existing Vue semantic primitives bound to .ulpi/design/DESIGN.md
visual_density: 8
motion_intensity: 2
reference_image: C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.2\前端设计1.1\预览图\文献检索\检索中心\文献检索最优的.png
implementation_prompt: C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.2\前端设计1.1\预览图\文献检索\检索中心\检索中心V2_高保真复刻完整提示词.md
target: vue-vite-engineering-task
---

# 检索中心 V2 策略工作台锁定规格

## Design Read

医学检索策略仪器台：将复杂的研究意图、术语证据和 PubMed 执行状态压缩为一张精确、可信、可操作的科研控制面板。

严格绑定 `.ulpi/design/DESIGN.md`。Every screen must read as the same product if placed side by side.

## Signature

复用“证据路径线”：顶部四阶段 Journey 将研究问题、意图、策略和执行连接为一条真实状态路径；路径只编码业务状态，不承担装饰。

## 主流程

```text
入口生成真实策略
→ /literature-search/workspace?strategy_id=:id
→ 加载持久化草稿
→ 检查/编辑依据、术语、MeSH、Query、Limits
→ 自动保存与 revision 冲突处理
→ validate + PubMed count
→ Ready
→ execute
→ /literature-search/results/:resultId
```

刷新、返回、并发编辑、外部服务部分失败、旧响应、离线和执行失败均按融合提示词第26至27章处理。

## 组件职责

- `LiteratureSearchView`：读取路由 strategy_id、组合页面、执行结果跳转；保持薄层。
- `SearchCenterHeader`：真实保存状态与版本菜单；不承载 execute action。
- `SearchJourneyProgress`：计算并呈现真实四阶段状态。
- `StrategyBasisSection`：研究问题与 Intent 摘要、编辑入口。
- `TermsMeshWorkspace`：术语/MeSH 区域编排和局部状态。
- `ConceptGroupRow`：一个真实概念组及术语渐进披露。
- `MeshTermList`：官方验证状态和锁定操作。
- `TermWarningBar`：结构化 Warning 与处理入口。
- `PubMedQueryPreview`：只读预览、复制、验证、编辑模式。
- `SearchLimitsSummary`：限制摘要与修改入口。
- `StrategyReadyPanel`：Ready/Warning/Blocking 聚合。
- `StrategyStickyBar`：真实摘要与页面唯一 execute action。
- `useSearchStrategy` / `useStrategyAutosave`：唯一业务状态来源，不在组件复制领域逻辑。

## 视觉锁定

- 基准视口 1536×1024；Sidebar 约229px；Header 约75px；Main 左内边距约26px。
- 工作台遵循单主操作原则：顶栏不显示“开始检索”，底部 Sticky 是唯一执行入口；Journey 第 4 步仅为状态标签。
- 主区块依次约为：Progress 62px、Basis 196px、Terms 386px、Query 98px、Limits/Ready 80px、Sticky 79px。
- Terms/MeSH 为页面主体，约 1.05:0.95；Limits/Ready 约 1:1。
- 白色表面、轻边框、12px 圆角、极轻阴影；主蓝只用于路径与主操作。
- 不设置参考图背景，不以绝对定位伪造页面。

## 状态与可访问性

所有区域覆盖 loading、empty、error/partial、success、stale。保存状态来自后端；MeSH 失败不清空其他区；Count 必须绑定当前 fingerprint；两个执行按钮共享防重复状态。Dialog 管理焦点和 Escape；锁定使用 aria-pressed；当前 Journey 使用 aria-current；动态状态使用克制 live region；移动端触控目标至少44px。

## Build Handoff

在 `D:\AI_project\rag_medicine` 的现有 Vue 3 + Vite 项目中实施原融合提示词。复用现有 API、类型、组件和锁定 Token，不创建第二套应用壳、API Client、Router 或 UI Framework。先确认后端 AC-STRAT 门禁，再执行 AC-V2-01 至 AC-V2-24。实现必须精确遵循本规格，不得自行重新设计。

## Design Pre-Flight

- Identity：仅使用 `.ulpi/design/DESIGN.md` 的 palette、type、radius、motion 和 icon language。
- Anti-slop：无渐变营销 Hero、玻璃拟态、嵌套卡片、假数字和装饰性状态点。
- State：九个业务区域均有完整状态矩阵和恢复路径。
- Accessibility：键盘、焦点、ARIA、对比度、reduced-motion 和移动触控均为硬门禁。
- Layout：Header、路径、策略依据、双栏术语、Query、双栏状态、Sticky 至少三种布局家族。
- Cognitive load：一个业务主操作；高频检查在首屏，低频编辑渐进披露。
- Self-critique：distinctiveness 3、hierarchy 4、consistency 4、accessibility 4、state coverage 4、copy 4、restraint 4、motion 4；总分31/32，无轴低于3。
