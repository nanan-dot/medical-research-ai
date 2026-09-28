# A4｜长PDF窗口化、可视段落同步与端到端验收设计

> 状态：实施设计（尚未实现）  
> 目标：在长篇医学PDF中稳定完成渲染、定位、选区、实时翻译同步和资源回收  
> 前置：A0 TextItem、A1 Segment、A2 Anchor、A3版本重定位

## 1. 当前性能断点

现有`PdfAnnotationReader.vue`加载后顺序渲染全部页面的Canvas和TextLayer。论文页数增加、缩放或切换文档时，会同时放大CPU、内存、DOM和旧请求覆盖风险。

A4不以“滚动看起来流畅”为唯一目标，还必须保证：

- 可视段落身份正确。
- 定位请求不会跳到错误文档或旧Revision。
- 翻译预取不会挤占用户主动操作。
- 离屏释放资源后仍能恢复锚点。
- 辅助技术和键盘导航仍可用。

## 2. 组件边界

```text
PaperReadingView.vue                 # 薄路由组合层
└── PaperReaderWorkspace.vue         # 三栏布局和上下文注入
    ├── ReadingHistoryPanel.vue
    ├── PdfReaderViewport.vue        # 滚动容器与页占位
    │   ├── PdfPageShell.vue         # 单页生命周期
    │   ├── PdfCanvasLayer.vue
    │   ├── PdfTextLayer.vue
    │   ├── PdfAnchorLayer.vue
    │   └── PdfSelectionToolbar.vue
    └── ReadingAssistantPanel.vue
        ├── ReadingRecordStrip.vue
        ├── RealtimeTranslationPanel.vue
        └── CopilotPanel.vue
```

组合式逻辑按职责拆分：

```text
usePdfDocument.ts            # PDF加载与Revision守卫
usePageVirtualization.ts     # 页窗口和尺寸占位
usePageRenderScheduler.ts    # Canvas/TextLayer调度
useVisibleSegments.ts        # 可视段落与active segment
useAnchorNavigation.ts       # Anchor定位和临时强化
usePdfSelection.ts           # A2 SelectionDraft
useTranslationPrefetch.ts    # 翻译优先队列
useReaderSession.ts          # 当前页/位置/进度保存
```

大型PDF对象和页面代理使用`shallowRef`，不进入深层Vue响应式代理。派生状态使用纯`computed`，网络与渲染副作用使用可清理watch。

## 3. 页面窗口化

### 3.1 页面状态

```text
placeholder → metadata_ready → render_queued → rendering → rendered
                                      ↓             ↓
                                  cancelled       error
rendered → parked → released → render_queued
```

- `placeholder`保留估算尺寸，避免布局跳动。
- `parked`保留TextItem/Anchor轻量元数据，可释放Canvas像素。
- `released`只保留页尺寸和状态，重新进入窗口时重建。

### 3.2 窗口策略

- 当前可视页为核心窗口。
- 前后缓冲页数量按滚动方向、设备内存和渲染耗时动态调整。
- 定位目标页拥有最高渲染优先级。
- 缓冲参数是配置和实测结果，不在设计阶段硬写页数承诺。

### 3.3 尺寸稳定

A0提供页面宽高与旋转。缩放后先计算占位尺寸，再异步渲染Canvas/TextLayer，避免CLS。页面旋转或适合宽度模式变化时统一更新generation并重算占位。

## 4. 渲染调度

### 4.1 优先级

```text
用户定位目标页
> 当前可视页TextLayer
> 当前可视页Canvas
> 滚动方向缓冲页
> 相反方向缓冲页
> 缩略图/后台预热
```

选区和锚点定位依赖TextLayer，因此目标页TextLayer优先于非关键Canvas细化。

### 4.2 并发与取消

- Canvas和TextLayer任务有独立受限并发队列。
- 每个任务绑定`document_generation + anchor_revision_id + page_number + zoom_generation`。
- 文档、Revision或缩放变化时取消旧任务并丢弃迟到结果。
- PDF.js RenderTask显式cancel；不能只忽略Promise结果。
- 队列不得无限累积滚动经过的旧页。

### 4.3 主线程预算

长任务分片并在浏览器有空闲时处理非关键工作；用户输入、滚动和选区优先。是否使用Worker、OffscreenCanvas或`requestIdleCallback`根据浏览器支持渐进增强，不作为正确性的前提。

## 5. Canvas、TextLayer与AnchorLayer生命周期

- Canvas离屏后可将宽高归零释放像素内存，但页壳尺寸保持。
- TextLayer在邻近窗口保留，远离窗口后释放DOM。
- AnchorLayer的数据来自共享Anchor，不复制业务状态。
- 页面重新渲染后按TextItem范围优先恢复高亮，几何矩形作为后备。
- 选区冻结期间，相关页面不得释放TextLayer。
- 正在编辑批注或打开定位对比时，目标页被pin住。

## 6. 可视段落同步

### 6.1 观测对象

每个A1 Segment在TextLayer上具有`data-segment-id`范围或轻量观测元素。IntersectionObserver只产生候选，active segment由纯函数决策。

### 6.2 Active Segment决策

综合：

- 可视面积比例。
- Segment中心与阅读焦点线距离。
- 滚动方向。
- 当前用户选区或键盘焦点。
- A1阅读顺序。

标题短暂越过视口时不能反复抢占正文。决策使用进入/退出滞后和短稳定窗口，具体时间通过交互测试确定。

### 6.3 事件契约

```ts
interface VisibleReadingContext {
  documentId: number;
  anchorRevisionId: number;
  segmentationRevisionId: number;
  primarySegmentId: number | null;
  visibleSegmentIds: readonly number[];
  pageNumbers: readonly number[];
  reason: "scroll" | "selection" | "navigation" | "keyboard";
}
```

右侧翻译只接受带Revision的上下文；旧上下文响应不得写入当前面板。

## 7. Anchor定位调度

定位过程是状态机：

```text
requested → validating → page_scrolling → page_rendering
→ anchor_resolving → highlighted → completed
                         ↘ degraded/unresolved/failed
```

步骤：

1. 验证Anchor文档和Revision。
2. 选择已确认resolved anchor或original anchor。
3. 滚动到首片段页面占位。
4. 提升目标页渲染优先级。
5. TextLayer就绪后按TextItem范围定位。
6. 失败时尝试保存的几何矩形。
7. 仅在两者都不可用时退化为页级提示。

新的定位请求取消旧请求。临时强调不只依赖颜色，还应有轮廓/状态提示，并尊重`prefers-reduced-motion`。

## 8. 实时翻译调度

### 8.1 请求层级

```text
用户主动翻译选区 P0
当前active segment P1
同屏其他eligible segments P2
滚动方向相邻页 P3
反向相邻页 P4
```

`review_required`默认不预取，`blocked`不进入普通翻译队列。

### 8.2 去抖与取消

- 快速滚动只提交稳定后的可视上下文。
- 已发出的持久化翻译任务不因离开视口删除；前端停止等待低优先任务即可。
- 新active segment提升已有相同cache key任务优先级，而不是复制任务。
- 文档切换立即清空展示队列，持久缓存仍按版本隔离。

### 8.3 展示一致性

右侧、双语和中文模式共同引用`translation_revision_id`。任何模式不得私自重新请求不同配置的译文。质量状态变化通过统一Store替换不可变结果。

## 9. 阅读状态与进度

A4只负责采集可信视口事件，阅读会话后端另行持久化。建议事件包含：

- 文档/文件/Anchor Revision。
- 当前页和active segment。
- 可视页集合。
- 会话ID与客户端序号。
- 事件时间和幂等键。

“已阅读页”不能因页面预渲染而计入；需满足真实可视、最小停留和前台活动条件。具体门槛经用户测试确定。

状态上报合并、限频，在`visibilitychange/pagehide`时尽力flush；后端使用单调客户端序号和服务端时间防止旧事件覆盖新进度。

## 10. 内存与缓存预算

分别测量：

- Canvas像素内存。
- TextLayer DOM节点数。
- PDF.js页面代理和字体资源。
- Segment/Anchor前端缓存。
- 翻译结果缓存。

预算按设备能力分档。超预算时按以下顺序回收：

1. 最远离视口且未pin的Canvas。
2. 最远离视口的TextLayer。
3. 非当前文档会话缓存。
4. 低优先级预取结果的内存副本。

持久化翻译和Anchor不能因前端内存回收而丢失。

## 11. 可访问性

- 工具栏和页码导航完整键盘可达。
- 虚拟化不能使当前键盘焦点所在页面突然卸载。
- 页面加载、定位完成、定位降级和翻译状态使用适度`aria-live`。
- 图标按钮具备可访问名称和可见焦点。
- 缩放后不阻断浏览器文字选择。
- 减少动态效果模式下使用即时滚动或短暂静态强调。
- 中文/双语正文使用语义文本节点，不以Canvas绘制译文。

## 12. 错误恢复

- 单页渲染失败不使整篇PDF崩溃，提供页级重试。
- TextLayer失败时Canvas仍可看，但选区和精确定位标记不可用。
- Canvas失败而TextLayer可用时不得展示错位透明文本；页面进入明确错误态。
- 网络Range失败可按受控策略重试或提示重新加载。
- 内存压力导致回收属于正常状态，不显示为错误。

## 13. 性能观测

仅记录技术指标，不记录正文：

- PDF首个可视页Canvas/TextLayer就绪时间。
- 滚动到页面可交互时间。
- Anchor定位总耗时与降级率。
- 渲染队列长度、取消数和迟到结果数。
- 峰值Canvas数量、TextLayer节点数和估算内存。
- Active Segment抖动次数。
- 翻译缓存命中、任务等待与可展示时间。

指标按匿名技术会话聚合，禁止记录quote或用户笔记。

## 14. 性能验收场景

必须在至少三类设备档位和不同页数PDF上实测：

- 普通文本论文。
- 双栏、图表密集论文。
- OCR或TextItem密集论文。

场景：

1. 首次打开并定位上次阅读页。
2. 连续快速滚动多个页面。
3. 输入页码跳转远页。
4. 从全部记录定位Anchor。
5. 缩放后继续选择和定位。
6. 快速切换两篇论文。
7. active segment连续变化并触发翻译。
8. 长时间阅读后的内存稳定性。

## 15. 功能与性能双门禁

性能优化不能破坏：

- TextItem与Anchor身份。
- 阅读顺序和active segment。
- SelectionDraft。
- 批注高亮。
- 翻译质量状态。
- 键盘焦点和屏幕阅读器状态。

验收指标包括但不限于：首屏时间、定位时延、滚动长任务、内存峰值、定位正确率和旧请求污染数。具体阈值必须在目标设备实测后冻结；设计阶段不虚构数值。

严重门禁：

- 文档切换后展示上一论文译文或高亮。
- 虚拟化后Anchor定位到错误页/段落。
- 离屏回收导致未保存SelectionDraft丢失。
- 快速滚动产生无限渲染或翻译队列。
- 预渲染页面被错误计为已阅读。
- 键盘焦点所在页面被卸载。

## 16. 自动化测试

- Vitest：调度纯函数、窗口计算、active segment、优先队列和generation守卫。
- Vue组件测试：页壳生命周期、pin、错误降级、焦点保持。
- Playwright：滚动、远页定位、缩放、选区、切文档、双语切换。
- 浏览器性能测试：收集PerformanceObserver长任务与自定义标记。
- 真实PDF人工验收：锚点与译文双向定位。

性能测试必须保存设备、浏览器、PDF特征和构建版本；不同环境数据不能直接混为同一基线。

## 17. 实施顺序

### A4.1 组件拆分与generation守卫

先保持行为一致，拆分现有单体阅读器，建立文档/缩放/Revision代际。

### A4.2 页面窗口化

页占位、可视窗口、Canvas/TextLayer生命周期与pin机制。

### A4.3 定位与可视段落

Anchor调度、Segment Observer、active segment稳定策略。

### A4.4 翻译和阅读进度调度

优先队列、缓存复用、状态上报和旧请求保护。

### A4.5 端到端与性能基线

多设备、多PDF类型、无障碍和长时间稳定性验收。

---

本文件为设计稿。窗口大小、并发数、内存预算和性能阈值均为【未实测】。
