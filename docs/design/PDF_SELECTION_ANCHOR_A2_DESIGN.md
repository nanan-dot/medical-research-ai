# A2｜PDF自由选区、共享锚点创建与业务复用设计

> 状态：实施设计（尚未实现）  
> 输入：A0 TextItem Revision、A1 Segment/Reading Flow、浏览器 DOM Selection  
> 输出：经过后端重建校验的不可变 SourceAnchor  
> 适用：翻译、解释、总结、批注、标记、疑问、笔记、加入研读

关联设计：

- [A0 TextItem提取](./PDF_TEXTITEM_EXTRACTION_A0_DESIGN.md)
- [A1版面与段落](./PDF_LAYOUT_SEGMENTATION_A1_DESIGN.md)
- [共享原文锚点](./DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md)

## 1. 当前问题

当前 `PdfTextSelection` 只有：

```text
pageNumber + rectangles + selectedText
```

当前后端规范化客户端 `selected_text` 后直接写入批注。这只能证明客户端提交了一段文字，不能证明它确实来自当前 PDF 的指定位置。

此外：

- 只支持单页。
- 没有 PDF.js TextItem 与字符偏移。
- 同页重复文字无法唯一识别。
- 选区无法与 A1 Segment 和阅读顺序关联。
- Copilot 消息没有当前页、章节和选择范围。
- AI 回答引用与用户提问上下文没有区分。

## 2. 核心决策

### 2.1 浏览器描述范围，后端决定原文

客户端提交 TextItem 范围、字符偏移、几何矩形和用于冲突提示的 quote。后端必须从固定 Anchor Revision 重建原文，并将重建结果作为唯一事实来源。

客户端 quote：

- 用于发现浏览器和后端文本层不一致。
- 不直接写入 `SourceAnchor.quote`。
- 不一致时返回冲突，而不是“尽量保存”。

### 2.2 选中不等于保存

拖选只产生前端内存中的 `SelectionDraft`。只有用户执行翻译、批注、解释等动作时才创建或复用持久化 SourceAnchor，避免数据库保存大量无业务用途的鼠标选区。

### 2.3 Anchor不可变，业务资产可变

- SourceAnchor 内容、Revision 和 fragments 创建后不可修改。
- 批注内容、颜色、问题状态等业务字段可以修改。
- 原文版本变化通过 Relocation 关系连接新 Anchor，不修改旧 Anchor。

### 2.4 上下文与回答引用分开

Copilot 请求中的选区是 `message_context_anchor`；模型回答检索到的依据是 `citation.source_anchor_id`。二者可能相同，也可能不同，不能混成一个字段。

## 3. 前端模型

### 3.1 `SelectionDraft`

```ts
interface SelectionDraft {
  documentId: number;
  expectedFileHash: string;
  expectedAnchorRevisionId: number;
  expectedSegmentationRevisionId: number;
  browserQuote: string;
  fragments: readonly SelectionFragmentDraft[];
  capturedAt: string;
}
```

### 3.2 `SelectionFragmentDraft`

```ts
interface SelectionFragmentDraft {
  pageNumber: number;
  startItemIndex: number;
  startOffsetUtf16: number;
  endItemIndex: number;
  endOffsetUtf16: number;
  rectangles: readonly NormalizedRect[];
}
```

Fragment 范围采用半开区间：

```text
[start, end)
```

当起止位于同一 TextItem 时，`startOffsetUtf16 < endOffsetUtf16`。跨 TextItem 时首尾偏移分别约束在对应 TextItem 的 UTF-16 长度内。

### 3.3 Draft生命周期

以下情况立即清空：

- 切换文档。
- Anchor/Segmentation Revision 变化。
- PDF重新加载失败。
- 用户取消或选择新的非空范围。
- 后端返回版本冲突。

切换右侧 Tab 不清空；打开批注编辑框时冻结当前 Draft，后续鼠标选择不能悄悄替换正在编辑的关联原文。

## 4. PDF.js DOM捕获

### 4.1 TextLayer标识

每个可选择 Span 必须携带：

```text
data-page-number
data-text-item-index
data-source-array-index
data-anchor-revision-id
```

TextLayer渲染后需要建立 DOM Text node 到 TextItem 的显式映射。不能只靠 `parentElement` 猜测，因为 PDF.js 版本变化可能改变 DOM 包装结构。

如果当前PDF.js TextLayer公开API不能保证“一项一Span”，实现必须在受控渲染适配层中建立映射，并用A0的`source_array_index/item_index/text`核对。Span数量或文本无法对齐时，该页禁用精确选区并报告`TEXT_LAYER_MAPPING_MISMATCH`，不能按DOM顺序勉强编号。

### 4.2 Range端点转换

浏览器 Range 端点可能落在：

- Span 内的 Text node。
- TextLayer 容器边界。
- `<br>` 或浏览器插入结构。

只接受可以解析为明确 TextItem 与 UTF-16 offset 的端点。容器边界通过相邻有效 Text node 规范化；无法唯一规范化时返回前端选区错误，不构造猜测范围。

### 4.3 正反向选择

用户可以从后往前拖选。前端根据 A1 阅读顺序规范化 start/end，而不是依赖 anchor/focus 方向。

若 A1 页面/区域存在 `READING_ORDER_AMBIGUOUS`，跨块选区不能自动规范化；允许用户缩小到单一可靠 Segment。

### 4.4 矩形

- 使用 Range `getClientRects()` 获取可见几何。
- 转换为相对页面宽高的坐标。
- 过滤零面积矩形。
- 合并仅在同一行且相邻的重叠矩形。
- 几何只用于渲染和后备定位，不决定文字内容。

缩放、旋转和 devicePixelRatio 变化不能改变归一化结果。页面 rotation 必须与 A0 Revision 一致。

## 5. 跨页与跨段落选区

### 5.1 Fragment拆分

每个物理页一个或多个 fragment，按 A1 阅读流排序。跨页 Anchor 主表不保存单一 `page_number`，页码来自 fragments。

### 5.2 连续性

后端只接受在 A1 Reading Flow 中连续或属于同一跨页 SourceSegment 的范围。以下情况拒绝：

- 跨过被阻断的表格区域。
- 跨越不确定栏顺序。
- 从正文跳到脚注再回正文。
- 文档页之间缺少连续阅读关系。
- 包含不属于当前 Revision 的 TextItem。

### 5.3 限额

最大字符数、最大页跨度、最大fragment数、最大矩形数全部由后端配置。不同动作可以有不同限额：批注可较短，章节总结不应通过巨大自由选区实现，而应引用 Section。

达到限额时返回具体提示，不截断选区后继续执行。

## 6. 后端请求契约

业务接口共享 `SourceAnchorDescriptor`：

```json
{
  "expected_file_hash": "...",
  "expected_anchor_revision_id": 301,
  "expected_segmentation_revision_id": 88,
  "browser_quote": "A primary composite outcome...",
  "fragments": [
    {
      "page_number": 12,
      "start_item_index": 44,
      "start_offset_utf16": 2,
      "end_item_index": 51,
      "end_offset_utf16": 18,
      "rectangles": []
    }
  ]
}
```

版本字段全部必填，禁止通过“取最新”替客户端补版本，以免页面停留期间文档被更新。

## 7. 后端校验与Quote重建

校验顺序固定：

1. 验证文档访问权限。
2. 验证 `Document.file_hash`。
3. 验证 Anchor与Segmentation Revision属于该文档且当前可用。
4. 验证页码、TextItem、UTF-16 offset和fragment数量。
5. 按A1 Reading Flow排序并验证连续性。
6. 从A0 TextItem重建每个fragment原文。
7. 使用版本化连接规则合成Anchor quote。
8. 对客户端quote执行等价比较。
9. 计算段落归属、前后文快照和内容指纹。
10. 创建或复用不可变Anchor。

任何一步失败都不得创建业务资产。

### 7.1 UTF-16切片

Python不能直接使用普通字符串下标处理浏览器UTF-16 offset。必须使用经过单元测试的转换函数：

```text
utf16_offset → Unicode code point boundary
```

offset落在代理对中间时拒绝。组合字符边界可以允许精确代码单元范围，但UI选择通常应规范化到字素边界；具体策略版本化。

### 7.2 Quote等价

比较两层：

- `exact_browser_equivalent`：仅允许浏览器选择造成的已知空白差异。
- `normalized_equivalent`：应用与Revision一致的版本化规范化。

涉及数字、比较符、希腊字符、上下标映射或药物名时，不能通过宽松模糊匹配放行。

客户端与后端不等价时返回 `QUOTE_MISMATCH`，响应只提供安全的差异摘要和刷新建议，不回显额外未选中的论文正文。

### 7.3 段落归属

- 完全位于一个Segment：绑定该Segment和segment range。
- 连续跨多个Segment：Anchor可关联多个Segment，记录覆盖顺序。
- 与Segment映射不完整：根据动作降级为`review_required`或拒绝。

翻译默认要求单个eligible Segment内的完整段落或明确子范围；Copilot解释可以接受有限的连续多段选区，但必须保留每段边界。

## 8. Anchor数据模型补充

### 8.1 `document_source_anchors`

- `id`
- `anchor_revision_id`
- `anchor_type=segment/text_range/multi_segment`
- `quote`：后端重建原文
- `normalized_quote`
- `quote_hash`
- `prefix/suffix`：受限长度的重定位上下文
- `content_fingerprint`
- `resolution_status=exact`
- `created_at`

### 8.2 `document_anchor_fragments`

- `anchor_id/fragment_order`
- `page_id/page_number`
- `start_item_index/start_offset_utf16`
- `end_item_index/end_offset_utf16`
- `rectangles_json`
- `reconstructed_text_hash`

### 8.3 `document_anchor_segments`

- `anchor_id/segmentation_revision_id/segment_id`
- `coverage_order`
- `segment_char_start/end`
- `coverage_type=full/partial`

Anchor的原文身份只绑定A0 Revision。A1分段归属属于可重新计算的派生关联；分段算法升级时重建`document_anchor_segments`，不会复制或使同一原文Anchor失效。

### 8.4 内容去重

Anchor `content_fingerprint`：

```text
hash(anchor_revision_id, ordered item ranges, quote_hash)
```

同一访问作用域和内容指纹可复用Anchor。不能只按quote去重，因为相同文字可能在论文中出现多次。

## 9. 业务原子操作

不推荐前端先调用“创建Anchor”，再调用“创建批注”；第二步失败会产生无用途Anchor，并增加竞态。

推荐各业务写接口接受：

```text
anchor_id XOR anchor_descriptor
```

- 已有Anchor时提交ID。
- 新选择时提交Descriptor。
- 后端在同一事务中 `resolve_or_create_anchor()`，再创建业务资产。

`XOR`必须由Pydantic校验，不能同时提交或全部缺失。

### 9.1 批注

```http
POST /api/v1/documents/{document_id}/annotations
Idempotency-Key: <uuid>
```

新增 `source_anchor_id`；保留现有 `file_hash/page_number/selection_geometry/selected_text` 兼容快照。跨页批注的旧单页字段保存首片段摘要，完整位置以Anchor为准。

### 9.2 翻译

```http
POST /api/v1/documents/{document_id}/translation-jobs
```

完整段落优先直接引用 `segment_id`；自由选区使用Anchor。翻译结果引用同一 `source_anchor_id`。

### 9.3 Copilot

建议扩展消息请求：

```json
{
  "question": "这段结果应如何理解？",
  "context": {
    "source_anchor_id": 991
  }
}
```

页码和章节由后端根据Anchor及当前A1关联计算并返回，不接收客户端冗余声明。持久化新增消息上下文关系，回答生成的Citation另行保存。

若选择文本发送给外部模型，必须遵守模型隐私授权和最小上下文原则。

### 9.4 总结与笔记

- 临时总结可以只生成，不自动成为科研证据。
- “保存为笔记”创建Reading Artifact并引用Anchor。
- 总结内容保存生成来源、模型版本和是否人工修改。

### 9.5 标记与疑问

- 标记保存分类值和可选自定义标签，引用Anchor。
- 疑问保存问题、状态和Anchor；不能用批注note字段模拟所有类型。

### 9.6 加入研读

创建研读候选：

- `source_anchor_id`
- `candidate_type`
- `remark`
- `status=pending`
- `created_from=reading`

保存候选不自动生成正式Claim或Evidence。“保存并进入研读”是在相同保存成功后由前端路由跳转。

## 10. 幂等与并发

### 10.1 幂等键

业务写入的唯一幂等身份包含：

```text
actor_scope + operation + idempotency_key
```

同键同请求指纹返回原结果；同键不同请求指纹返回 `409 IDEMPOTENCY_KEY_REUSED`。

Anchor get-or-create依赖内容指纹唯一约束，业务幂等依赖业务表或统一幂等记录，二者职责不同。

### 10.2 版本竞态

如果用户拖选后PDF或Segmentation更新：

- 返回Revision Conflict。
- 前端保留用户输入的note/question草稿。
- 清除旧SelectionDraft并重新加载原文。
- 不把旧范围自动映射到新版本后直接提交。

### 10.3 事务

Anchor、fragments、segment coverage与业务资产在一个数据库事务中创建。外部模型调用不能放在数据库事务中：

- 先原子保存Anchor和任务/消息请求。
- 提交事务。
- Worker调用模型。
- 再保存结果。

## 11. 权限与隐私

- 每次使用 `anchor_id` 都重新验证其文档访问权限，不能只验证ID存在。
- API默认不允许跨文档组合Anchor。
- 返回Anchor时只包含当前调用所需原文，不暴露prefix/suffix等重定位上下文给无关接口。
- 日志记录Anchor ID、哈希和范围，不记录完整quote。
- 第三方模型只获得业务动作需要的选区及有限上下文。
- 删除业务资产不立即删除共享Anchor；孤立Anchor按受控保留策略清理，不能破坏审计引用。

## 12. 错误码

- `DOCUMENT_REVISION_CONFLICT`
- `ANCHOR_REVISION_CONFLICT`
- `SEGMENTATION_REVISION_CONFLICT`
- `SELECTION_ENDPOINT_UNRESOLVED`
- `TEXT_LAYER_MAPPING_MISMATCH`
- `TEXT_ITEM_NOT_FOUND`
- `UTF16_OFFSET_INVALID`
- `QUOTE_MISMATCH`
- `SELECTION_READING_ORDER_AMBIGUOUS`
- `SELECTION_CROSSES_BLOCKED_REGION`
- `SELECTION_LIMIT_EXCEEDED`
- `ANCHOR_ACCESS_DENIED`
- `ANCHOR_DOCUMENT_MISMATCH`
- `IDEMPOTENCY_KEY_REUSED`

## 13. 前端交互状态

```text
idle → selecting → selected → action_pending → persisted
                   │                ↓
                   └──────────── error/revision_conflict
```

- `selected`：显示浮动工具条。
- `action_pending`：冻结Draft和相关按钮，允许取消尚未开始的AI任务。
- 普通校验错误：保留Draft并给出可修复提示。
- Revision冲突：保留用户输入草稿，但清除失效选区。
- 成功后是否保留可视高亮由动作决定；持久资产使用Anchor渲染。

键盘用户必须能：

- 使用原生文本选择。
- 将焦点移入工具条而不丢失冻结Draft。
- 关闭工具条并返回原文焦点。
- 获知选区页码、章节与字符数。

## 14. 测试与验收

### 14.1 前端单元测试

- 正向、反向、同Item、跨Item和跨页选择。
- DOM Text node、容器边界与`br`端点。
- 缩放、旋转、重新渲染和文档切换。
- 工具条获焦后Draft保持。
- 旧渲染异步结果不能覆盖新文档。

### 14.2 后端纯函数测试

- UTF-16与Unicode边界转换。
- 代理对、组合字符、希腊字母和上下标。
- fragment排序、连续性和quote重建。
- 数字/符号敏感的等价比较。
- content fingerprint确定性。

### 14.3 API与事务测试

- 客户端伪造quote不能入库。
- Anchor ID不能跨文档或越权复用。
- 同幂等键同请求返回原结果。
- 同幂等键不同请求返回冲突。
- Anchor创建成功但业务验证失败时整体回滚。
- 模型失败时Anchor与任务状态可审计，不能保存伪成功回答。

### 14.4 真实PDF验收

- 同页重复句。
- 双栏跨块拖选。
- 段落跨页。
- 带上下标、希腊字母、连字符断词和统计值的选择。
- TextLayer与Canvas缩放、旋转后的定位。
- 文档版本更新后的冲突和重定位流程。

### 14.5 严重失败门禁

以下情况阻止发布：

- 保存的quote与后端TextItem范围不一致。
- 同页重复句定位到错误位置。
- 双栏选区混入另一栏文本但未阻断。
- 数字、比较符或组别相关文本在quote重建中变化。
- Copilot上下文与回答Citation混淆。
- 业务创建失败却遗留用户可见的半成品资产。

具体长度和页跨度限额需通过真实交互与性能测试确定，当前均为【未实测】。

## 15. 实施拆分

### A2.1 前端SelectionDraft

- TextItem DOM映射。
- Range端点解析、正反向规范化与fragment生成。
- Draft冻结和键盘焦点。

### A2.2 后端Anchor解析器

- Descriptor Schema。
- UTF-16切片、连续性校验、quote重建和指纹。

### A2.3 批注迁移接入

- Annotation新增Anchor引用。
- 保留旧字段和旧批注兼容。

### A2.4 翻译与Copilot接入

- Translation引用Anchor/Segment。
- Message Context与Citation分离。

### A2.5 Reading Artifacts与研读候选

- 标记、疑问、笔记和候选使用共享Anchor。
- 幂等、权限、事务和验收测试。

---

本文件为设计稿。浏览器DOM兼容、跨页选择体验、UTF-16映射与真实PDF定位均为【未实测】。
