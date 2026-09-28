---
project: 素问·科研工作台
register: product
aesthetic_direction: technical / utilitarian
color_strategy: restrained
design_system: Reka UI primitives themed with locked tokens
design_variance: 5
motion_intensity: 2
visual_density: 8
---

# 素问·科研工作台设计语言

## Design Read

临床证据控制台：像可靠的科研仪器一样安静、精确、高密度，用清晰的来源与状态线索替代装饰。

## Identity Lock

Every screen must read as the same product if placed side by side.

本文件是新前端唯一视觉语言来源。任何页面不得自行引入新的主色、圆角体系、字体组合、阴影体系或交互语气。确需变更时先更新本文件，再修改组件。

## Signature

“证据路径线”是全产品唯一标志性元素：在来源、文档、分析、证据和写作之间使用一条克制的蓝色路径线及节点表达当前科研上下文。它只编码真实层级、选中状态或处理阶段，不作为无意义装饰。

## Anti-slop Lock

禁止：

- 紫蓝霓虹渐变和大面积发光；
- 玻璃拟态卡片堆叠；
- 卡片内部再嵌套卡片；
- 营销落地页式巨型标题和大面积空白；
- 无业务意义的状态点、假图表、假精确数字；
- 每个页面使用不同的圆角和阴影；
- 依靠动画制造“高级感”；
- 使用颜色作为状态的唯一表达。

## Design System

使用 Reka UI 作为 Vue 无障碍交互原语，适用于 Dialog、Drawer、Dropdown、Tooltip、Tabs、Select 等复杂控件。通过本文件的 token 主题化，不手写仿制其交互行为。普通按钮、表格、状态标签等简单结构可以使用语义 HTML 和项目基础组件。

如果实施时没有引入 Reka UI 的必要性，允许继续使用原生语义元素，但必须满足相同键盘、焦点和 ARIA 验收要求。

## Color (locked)

| role | OKLCH | hex | use | contrast note |
|---|---|---|---|---|
| background | `oklch(0.982 0.006 250)` | `#F7F9FC` | 应用背景 | 深色正文约17:1 |
| surface | `oklch(1 0 0)` | `#FFFFFF` | 主表面 | 深色正文约17.8:1 |
| elevated | `oklch(0.993 0.004 250)` | `#FBFCFE` | Drawer、浮层 | 深色正文约17.5:1 |
| text | `oklch(0.208 0.042 265)` | `#0F172A` | 标题、正文 | 对白色约17.8:1 |
| muted | `oklch(0.446 0.036 257)` | `#475569` | 辅助文字 | 对白色约7.6:1 |
| subtle | `oklch(0.554 0.029 257)` | `#64748B` | 元数据 | 对白色约4.7:1 |
| border | `oklch(0.916 0.015 250)` | `#E2E8F0` | 分割、边界 | UI边界结合形状表达 |
| accent | `oklch(0.532 0.190 255)` | `#0B5FCC` | 当前路径、主操作 | 对白色约6.1:1 |
| accent-soft | `oklch(0.957 0.028 250)` | `#EAF2FF` | 选中背景 | 配accent文字约5:1 |
| success | `oklch(0.548 0.145 157)` | `#087A55` | 可用、完成 | 对白色约5.4:1 |
| warning | `oklch(0.602 0.166 55)` | `#B54708` | 需处理 | 对白色约5.2:1 |
| danger | `oklch(0.516 0.183 25)` | `#B42318` | 失败、破坏性 | 对白色约6.2:1 |
| info | `oklch(0.546 0.158 244)` | `#0969A8` | 处理中、提示 | 对白色约5.6:1 |

颜色分配遵守60-30-10：背景与白色表面为主体，浅蓝上下文为次级，主蓝只用于操作与路径。

## Type (locked)

| role | family | use | notes |
|---|---|---|---|
| display | `Source Han Sans SC`, `Noto Sans CJK SC`, sans-serif | 页面标题、模块标题 | 600–700，克制使用 |
| body | `Source Han Sans SC`, `Noto Sans CJK SC`, sans-serif | 中文正文和控件 | 400–600，清晰优先 |
| utility | `IBM Plex Mono`, `SFMono-Regular`, monospace | DOI、PMID、数值、时间、技术定位 | 使用 tabular-nums |

不在线下载字体作为首屏硬依赖。使用本地或系统回退，避免字体加载导致布局位移。

## Type Scale

```text
12px / 16px：标签、元数据
13px / 20px：紧凑控件、表格辅助信息
14px / 22px：正文、表格主内容
16px / 24px：组件标题
20px / 28px：页面二级标题
28px / 36px：页面主标题
```

## Scales (locked)

```text
spacing: 0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64
radius: sm 4, md 8, lg 12, xl 16, full 9999
border: 1px solid var(--border)
shadow-sm: 0 1px 2px rgba(15,23,42,.04)
shadow-md: 0 8px 24px rgba(15,23,42,.08)
z-index: base 0, dropdown 20, sticky 30, fixed 40, modalBackdrop 45, modal 50, tooltip 60, toast 70, skipLink 80
breakpoints: sm 640, md 768, lg 1024, xl 1280, 2xl 1536
motion: fast 120ms, base 220ms, emphasis 360ms
easing: cubic-bezier(0.16, 1, 0.3, 1)
```

不使用 bounce 或 elastic。`prefers-reduced-motion: reduce` 时移除非必要位移和淡入。

## Layout Grammar

1. 应用采用稳定左导航、上下文标题区、主工作区三层结构。
2. 数据密集页面优先表格、分割线和窄间距，不使用同尺寸卡片矩阵重复堆叠。
3. 顶部统计采用“状态条带”而非营销卡片墙。
4. 详情使用临时 Drawer，不永久压缩主工作区。
5. 同一页面只允许一个视觉主操作。
6. 复杂选项渐进披露到菜单、Drawer或二级页面。

## Iconography

使用单一线性图标族，统一16/18/20px尺寸和1.75px附近描边。文件类型图标允许使用语义色，但不得形成彩虹式视觉噪声。图标不能替代文字状态。

## Voice

```text
register: 平实、专业、可诊断
action vocabulary: 查看、添加、同步、修复、重试、保存、取消、关闭
success: 描述已发生的结果
error: 说明发生了什么以及用户能做什么
empty: 解释数据从哪里产生并给出下一步
```

禁止营销话术、拟人化道歉、含糊“发生错误”、直接暴露数据库或模型术语。

## Accessibility Lock

- 正文对比度至少4.5:1，大字和UI图形至少3:1；
- 所有操作可通过键盘完成；
- 焦点环使用2px accent并保留2px偏移；
- 状态必须同时包含文字或图标；
- Modal/Drawer打开后管理焦点并在关闭后恢复；
- 触控目标移动端至少44×44px；
- 动态错误和任务结果使用适当 live region；
- 不使用未净化的 `v-html`。

## Cross-session Consistency

后续任何页面设计和实现前必须先读取本文件。变化只能发生在布局组合和数据内容上，不能漂移 palette、type、radius、motion、icon family 和 voice。

