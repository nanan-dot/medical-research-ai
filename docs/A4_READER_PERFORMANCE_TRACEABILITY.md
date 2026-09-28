# A4 PDF 阅读性能验收追踪

状态：实施中。性能阈值、真实设备和医学 PDF 样本尚未冻结，不能由合成单测替代。

| ID | Given / When / Then | 验证位置 | 状态 |
|---|---|---|---|
| A4-01 | 多个页任务排队 / 存在导航目标 / 先执行导航、可视页、缓冲页 | `usePageRenderScheduler.test.ts` | 已验证 |
| A4-02 | 旧 document/zoom generation / 失效 / 排队任务丢弃、迟到结果不发布 | `usePageRenderScheduler.test.ts`，`PdfAnnotationReader.test.ts`：映射请求也显式取消 | 已验证 |
| A4-03 | 缩放、换文档或卸载 / Canvas、TextLayer 或 TextItem 映射正在运行 / 显式取消 | `PdfAnnotationReader.test.ts`：切文档取消 Canvas、TextLayer 与映射请求；卸载取消映射请求；浏览器缩放回归 | 已验证 |
| A4-04 | 长 PDF 滚动 / 页离开窗口 / 保留稳定占位并释放 Canvas/TextLayer | `PdfAnnotationReader.test.ts`、`e2e/a4-reader-window.spec.ts`：20 页模拟、24 页合成 PDF 的远页往返 | 合成样本验证；真实长 PDF 待测 |
| A4-05 | 选区冻结或键盘焦点页 / 虚拟化 / 目标页不被释放 | `usePdfPageWindow.test.ts`、`e2e/a2-source-selection.spec.ts` | 部分验证；真实长距离拖选待测 |
| A4-06 | Anchor 远页定位 / 渲染完成 / 精确范围优先、几何和页级提示降级 | `PdfAnnotationReader.vue` 已接入 resolved anchor；A2 精确高亮回归 | 部分验证；跨版本远页及完整降级链待测 |
| A4-07 | 可视段落快速变化 / 稳定窗口 / 只发布带 revision 的阅读上下文 | `activeReadingSegment.test.ts`、`useVisibleSegments.test.ts`、`e2e/a4-reading-context.spec.ts`、`test_reader_version_contract.py` | 基础版本守卫及迟到请求验证；复杂布局稳定性待测 |
| A4-08 | 快速滚动或切文档 / 翻译预取 / 主动请求优先且旧结果不污染 | 待新增 | 待测 |
| A4-09 | 长时间阅读 / 内存与长任务采集 / 指标不含 quote 或笔记 | `e2e/a4-reader-window.spec.ts` 采集 Canvas 数、估算字节和文本节点数 | 仅快照；长任务及长时间内存趋势待测 |
| A4-10 | 键盘焦点、减少动态效果、页级失败 / 操作 / 可达、降级明确且不丢选区 | `PdfAnnotationReader.test.ts`：页级失败并重试恢复；焦点固定、减少动画分支已实现 | 部分验证；完整键盘与屏幕阅读器人工验收待测 |

## 自动化证据（2026-08-31）

- 六个 A4 定向单测文件（Reader、Scheduler、PageWindow、PageVirtualization、VisibleSegments、ActiveReadingSegment）：17 tests passed。
- 后端 `pytest tests/modules/document_layout tests/modules/document_selection tests/modules/document_relocation -q`：52 passed，1 warning。
- `npm run typecheck` 与 `npm run build`：通过；构建保留既有单包大于 500 kB 警告。
- A4 修改文件 ESLint：0 errors，52 warnings（Vue 模板排版）；不能记作零警告。
- 前端全量测试本轮快照：237 passed、2 failed；失败均为 `StrategyWorkspaceV2.test.ts` 的未知分类和空策略提示断言。该页面属于并行修改范围，未越界改动；全量门禁未通过。
- 浏览器三种 viewport/DPI 均为同一主机模拟，不能替代三档物理设备。一次复跑桌面首屏空白超时（3 passed、1 failed），保留该失败事实，不以之前通过覆盖。
- 最终联合复跑 `npm run test:e2e -- e2e/a4-reader-window.spec.ts e2e/a4-reading-context.spec.ts e2e/a2-source-selection.spec.ts --workers=1`：6 passed（16.7 秒），包括原生跨页选区、保存后重开高亮、三种视口远页回收与缩放、错误 revision 拒绝。首次空白原因仍待定位，未提高断言超时或启用重试掩盖失败。
- 后续稳定性复跑 `e2e/a4-reader-window.spec.ts --repeat-each=4`：12 passed（22.8 秒）；此前的一次桌面首屏超时本轮未复现，仍作为历史不稳定信号保留。

## 补充证据（2026-09-01）

- `PdfAnnotationReader.test.ts` 新增活动 TextLayer 取消和页级失败重试恢复；A4 六个定向文件合计 17 tests passed。
- 阅读器相关文件 ESLint、`npm run typecheck`、`npm run build` 均通过；构建仍保留既有的单包大于 500 kB 警告。
- 本轮修改范围仅限 PDF 阅读器、Source Anchor 请求取消参数、A4 测试及本追踪文件；未修改论文库。

## 未完成条件

- A4.4：尚无实时翻译和阅读会话接口；当前只发布包含文档、revision、段落及页码 ID 的阅读上下文，未实现翻译预取或阅读进度持久化。
- A4.1：当前队列并发为 1，Canvas 与 TextLayer 尚未拆成独立并发队列；选区映射请求仍主要依赖 generation 丢弃迟到结果。
- A4.2：加载时仍预读全部页尺寸，尚未验证超长文档首屏耗时及 PDF.js 页代理回收。
- A4.5：人工黄金标注集、真实医学 PDF/OCR 样本、三档设备、长时间性能基线及阈值冻结均未完成。

结论：已实现窗口化阅读和版本固定的可视段落基础能力；A4 整体未通过全部验收，不能声明全部完成。
