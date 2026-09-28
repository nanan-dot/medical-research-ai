# A1｜医学论文版面、段落、章节与阅读顺序设计

> 状态：实施设计（尚未实现）  
> 输入：A0 固定 Revision 的页面、PDF.js TextItem 与技术质量报告  
> 输出：可解释的行、区域、文本块、段落、章节路径和跨页阅读顺序  
> 非目标：复杂表格结构恢复、医学语义总结、翻译生成

关联设计：

- [A0 TextItem 提取设计](./PDF_TEXTITEM_EXTRACTION_A0_DESIGN.md)
- [共享原文锚点设计](./DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md)

## 1. 设计目标

A1 必须回答五个问题：

1. 哪些 TextItem 属于同一行？
2. 页面有哪些栏和特殊区域？
3. 哪些行属于同一逻辑文本块？
4. 哪些块属于同一段落或标题？
5. 整篇论文的可信阅读顺序和章节路径是什么？

系统追求的是**可解释、可回放、失败时安全降级**，不是对任意 PDF 宣称百分之百还原版面。

## 2. 设计原则

### 2.1 几何先于语义

先根据坐标、字体、行距和栏结构建立候选，再用有限的论文结构词汇辅助分类。不能先让大模型“阅读全文并分段”，再反推原文位置。

### 2.2 不确定性逐层传播

行、区域、块、段落和章节每层都保存：

- 使用的规则版本。
- 关键特征。
- 决策原因。
- 质量标记。
- 是否允许进入普通翻译流。

上游阅读顺序不确定时，下游不能用流畅译文掩盖错误。

### 2.3 原始内容不删除

页眉、页脚、参考文献、表格和脚注可以被分类或排除出正文流，但仍保留在锚点 Revision 中。所谓“排除”只影响特定阅读流，不删除原文。

### 2.4 规则为主，模型为可选候选器

V1 使用确定性的几何和规则流水线。后续若引入版面模型，只能生成候选或特征；输出仍需满足相同契约、版本指纹和质量门禁。

## 3. 处理流水线

```text
A0 TextItems
  ↓ 坐标归一与字符映射
LineCandidate
  ↓ 区域/栏检测
PageRegion + ColumnModel
  ↓ 行分组
TextBlock
  ↓ 块分类与噪声标记
Heading / Paragraph / Caption / Footnote / TableZone / Other
  ↓ 页内阅读顺序
PageReadingFlow
  ↓ 跨页连续性
SourceSegment + SourceFragment[]
  ↓ 标题树
SectionNode + SegmentSectionMembership
```

每一步输出都可单独测试，不把全部逻辑堆进一个 `segment()` 函数。

## 4. 数据模型

A1 中间结果可按调试等级选择持久化。生产至少持久化 Region、Block、Segment、Section 和质量报告；Line 可以保留压缩 JSON 或仅在诊断模式持久化。

### 4.1 `document_page_regions`

- `id`
- `anchor_revision_id/page_id`
- `region_type`：`main/sidebar/header/footer/figure/table/footnote/unknown`
- `region_order`
- `bbox_json`
- `column_index` nullable
- `classification_method`
- `features_json`
- `quality_flags_json`

### 4.2 `document_text_blocks`

- `id`
- `page_id/region_id`
- `block_order_in_page`
- `block_type`：`heading/paragraph/caption/footnote/list_item/reference/table_text/other`
- `first_item_index/last_item_index`
- `text/raw_text/text_hash`
- `bbox_json`
- `line_count`
- `style_signature_json`：字体名、相对尺寸等可观察样式线索，不承诺真实粗体语义
- `classification_method`
- `quality_flags_json`

### 4.3 `document_source_segments`

沿用共享锚点设计，补充：

- `segmentation_revision`
- `segment_type`
- `reading_order`
- `section_node_id` nullable
- `first_page/last_page`
- `source_block_ids_json` 或关联表
- `translation_eligibility`：`eligible/review_required/blocked`
- `decision_trace_json`

### 4.4 `document_section_nodes`

- `id`
- `anchor_revision_id`
- `parent_id` nullable
- `level`
- `literal_title`
- `normalized_title`
- `canonical_role` nullable
- `heading_segment_id`
- `start_reading_order/end_reading_order`
- `first_page/last_page`
- `classification_method`
- `quality_flags_json`

`canonical_role` 只用于辅助导航：

```text
abstract/introduction/methods/results/discussion/conclusion/
references/supplement/other
```

界面显示优先使用论文原始 `literal_title`，不能用 canonical role 篡改作者标题。

### 4.5 A1 Revision 身份

分段结果身份：

```text
segmentation_fingerprint = hash(
  anchor_revision.extraction_fingerprint,
  segmentation_algorithm_version,
  layout_config_hash,
  canonical_heading_dictionary_version,
  output_content_hash
)
```

A1 重跑产生新的分段 Revision。A0 TextItem Revision 不因 A1 算法升级而变化。

## 5. 坐标系统

所有几何计算先转换到统一的“页面自然阅读坐标”：

- 原点左上。
- X 向右，Y 向下。
- 应用 PDF 页旋转后再分析。
- 坐标归一化到页面宽高 `[0,1]`，同时保留 PDF.js 原 transform。

不能直接用浏览器 CSS 像素参与算法，避免缩放和设备像素比影响结果。

TextItem bbox 由 transform、width、height 和字体信息计算。字体 ascent/descent 缺失时使用明确后备规则并产生质量标记。PDF.js 字体名或 family 不可靠等同于“粗体/斜体”语义，样式只能作为相对候选特征。

## 6. TextItem 到行

### 6.1 行候选特征

两个相邻 TextItem 可以进入同一行候选，需综合：

- 基线或垂直中心接近。
- 高度比例合理。
- 文本方向一致。
- 水平间距合理且不跨明显栏边界。
- 不存在显著上下标/公式冲突。

阈值相对于页面尺寸和局部字体中位数定义，禁止仅使用固定像素。

### 6.2 行内顺序

- 左到右文本按 X 排序。
- RTL 和竖排文本单独处理或标记 `review_required`。
- 上下标保留 TextItem 原身份，行文本映射记录其插入位置。
- 行内新增空格属于 synthetic character，并保留映射。

### 6.3 行质量问题

- `AMBIGUOUS_BASELINE`
- `OVERLAPPING_ITEMS`
- `MIXED_DIRECTION`
- `FORMULA_LIKE_LINE`
- `EXTREME_FONT_VARIATION`

公式行默认不进入普通医学段落翻译；周围正文仍可处理。

## 7. 页面区域与栏检测

### 7.1 先区分正文带与边缘带

通过跨页重复、页面位置和字体特征识别页眉页脚候选。候选只分类，不删除。

页眉页脚判定至少考虑：

- 在多页相近归一化位置重复。
- 文本相同或符合页码变化模式。
- 位于页面顶部/底部边缘带。
- 与正文存在明显垂直间距。

只出现一次的章节标题不能因靠近页顶被当作页眉。

### 7.2 栏模型

按正文行的水平占用区间和垂直持续性形成 Column Candidate：

- 单栏。
- 双栏。
- 三栏或侧栏。
- 跨栏标题/摘要/图表。

不能只对 X 中心点做聚类，因为跨栏标题会破坏结果。建议先识别宽块，再在剩余纵向区间检测栏。

### 7.3 分段栏布局

同一页可能上半部单栏、下半部双栏。栏模型必须按 Y 区间分段，不能强迫整页只有一种栏数。

### 7.4 表格和图片区域

V1 以保守方式识别候选区域：

- 行列网格、重复 X 对齐、短文本密集。
- 大面积无文本且有 Caption 邻接时只能标记为可能的非正文区域；若没有页面对象几何，不能断言该区域就是图片。
- `Table/Figure` 标题模式。

表格候选内文本默认 `translation_eligibility=review_required` 或 `blocked`，不能按正文行顺序串成段落。

A0 V1 只提供 TextItem 时，图片边界识别能力有限。如后续加入 PDF operator list 或受控页面对象几何，必须扩展 A0 契约和指纹，不能在 A1 内私自读取另一套未版本化数据。

## 8. 行到文本块

连续行形成同一块需综合：

- 同一区域和栏。
- 行间距接近局部正文间距。
- 左边界、首行缩进和悬挂缩进关系。
- 字体大小、粗细和字体族一致性。
- 前行是否以句末标点结束。
- 后行是否表现为标题、列表或图注起点。

不能仅用句号判断段落，因为医学论文中缩写、数值和引用频繁出现句点。

### 8.1 块类型分类

分类证据：

- 几何：宽度、位置、缩进、行数。
- 样式：相对字号、字体名线索、大小写模式；所谓粗体只能是待校验候选。
- 词法：`Abstract`、`Methods`、`Table 2` 等有限候选。
- 邻接：标题后通常跟正文，图注靠近图表区域。

`classification_method` 记录 `geometry/rule/dictionary/manual/model_candidate`。

## 9. 标题与章节树

### 9.1 标题识别

标题候选优先依赖相对版式：字号、字体样式线索、独立行、上下间距、编号结构。词典只帮助识别 canonical role，不负责决定它一定是标题。

例如 `Results` 出现在句子中不能因此变成章节标题。

### 9.2 标题层级

层级由以下信息推断：

- 编号模式：`2`、`2.1`、`2.1.1`。
- 字号和字重层级。
- 居中/左对齐和缩进。
- 前后标题的结构一致性。

无法确定时使用扁平层级并标记 `HEADING_LEVEL_UNCERTAIN`，不能生成虚假的精细层级。

### 9.3 canonical role

匹配需要版本化同义词表，覆盖常见英文医学论文标题，例如：

- Methods / Materials and Methods / Patients and Methods。
- Results / Findings。
- Discussion / Interpretation。

同义词表只映射角色，保留原始标题。复合标题如 `Results and Discussion` 可以使用 `other` 或复合角色，不强行拆分不存在的章节。

### 9.4 无显式标题论文

如果论文没有可靠标题结构：

- 仍生成段落和阅读顺序。
- `section_node_id` 可以为空。
- 前端显示页码，不伪造 `Results` 等章节。
- Copilot/翻译请求不应声明不存在的章节上下文。

## 10. 页内阅读顺序

### 10.1 图结构

将 TextBlock 构成有向候选图：

- 同栏上方块优先指向下方块。
- 当前栏结束后指向下一栏顶部。
- 跨栏标题在其覆盖的栏内容之前。
- Caption 与对应图表区域形成附属关系，不穿插进正文句子。
- 页眉页脚不进入默认正文流。

对候选图执行拓扑排序。若存在环或多个同等合理顺序，页面标记 `READING_ORDER_AMBIGUOUS`。

### 10.2 决策轨迹

每条关键边保存原因，例如：

```json
{
  "from_block_id": 31,
  "to_block_id": 32,
  "reasons": ["same_column", "nearest_below", "style_continuity"],
  "conflicts": []
}
```

这使双栏串错时可以诊断，而不是只看到错误全文。

## 11. 跨页段落合并

### 11.1 合并条件

前页末块和后页首正文块合并为一个 SourceSegment，需要综合：

- 前块未表现为完整段落结束。
- 后块不是标题、列表起点、Caption、脚注或参考文献。
- 字体和栏宽兼容。
- 句法表面具有连续性。
- 行尾断词可以受控重建。
- 页面边缘不存在明显章节切换。

### 11.2 医学保护条件

包含数字、单位、药物名、基因名或统计表达的断词合并必须保守：

- 原始片段始终保留。
- 合并字符记录为 synthetic mapping。
- 无法确定时不合并，段落进入 `needs_review`。

### 11.3 禁止自动合并

- 前页结束于表格或图注区域。
- 后页从新章节标题开始。
- 栏模型不可靠。
- 两页阅读方向不同。
- OCR/文本层质量不足。

## 12. 参考文献、图注、脚注与补充材料

- References 下的条目保留并分类为 `reference`，默认不进入实时正文翻译预取。
- Caption 单独形成 Segment，可以显式请求翻译。
- Footnote 单独形成 Segment，并与页面/引用块关联；不能插入正文中央。
- Supplement 形成独立章节角色，不与主文 Results 混合。
- 表格内文本在结构恢复完成前不生成普通段落。

## 13. 质量状态与门禁

### 13.1 Segment 质量标记

- `COLUMN_ORDER_UNCERTAIN`
- `CROSS_PAGE_JOIN_UNCERTAIN`
- `HEADING_CLASSIFICATION_UNCERTAIN`
- `TABLE_TEXT_CONTAMINATION`
- `FOOTNOTE_BOUNDARY_UNCERTAIN`
- `FORMULA_CONTENT_PRESENT`
- `OCR_TEXT_UNRELIABLE`
- `TEXT_MAPPING_INCOMPLETE`

### 13.2 翻译资格

| 状态 | 条件 | 下游行为 |
|---|---|---|
| `eligible` | 文本映射完整、阅读顺序可靠、非复杂表格 | 可以进入翻译质量流水线 |
| `review_required` | 文本仍可定位但结构存在疑点 | 翻译需显式提示，默认不预取 |
| `blocked` | 阅读顺序、文本映射或原文质量可能改变含义 | 不生成普通译文 |

A1 的 `eligible` 只表示版面结构达到输入条件，不代表译文或医学内容正确。

## 14. A1 状态机与任务

复用统一 `TaskRecord`：

```text
task_type = document_layout_segmentation
idempotency_key = segment:{anchor_revision_id}:{algorithm_config_hash}
```

状态：

```text
queued → lines → regions → blocks → ordering → sections
       → cross_page → validating → ready/review_required
                                  ↘ failed/cancelled
```

中间阶段不可对普通读取 API 公开。最终发布时使用单事务切换当前 Segmentation Revision。

## 15. API

### 15.1 创建分段任务

```http
POST /api/v1/document-anchor-revisions/{anchor_revision_id}/segmentations
Idempotency-Key: <uuid>
```

返回已有完成版本 `200`，新任务或进行中任务 `202`。

### 15.2 Manifest 与章节

```http
GET /api/v1/documents/{document_id}/segmentation-manifest
GET /api/v1/documents/{document_id}/sections
GET /api/v1/documents/{document_id}/sections/{section_id}/segments
```

章节返回原始标题、canonical role、页码范围、锚点和质量状态。

### 15.3 段落

```http
GET /api/v1/documents/{document_id}/source-segments?page=12
GET /api/v1/source-segments/{segment_id}
```

列表默认不返回完整诊断轨迹；详情可按权限返回受限质量信息。内部诊断接口与普通产品接口分开。

### 15.4 人工修正

V1 可以先提供内部审核接口：

```http
POST /api/v1/document-segmentations/{id}/corrections
```

修正包括块类型、阅读顺序、段落合并/拆分和标题层级。修正产生新 Segmentation Revision 或覆盖层，不修改原算法结果。

## 16. 前端契约

前端章节导航只消费后端发布的 Section/Segment：

- 当前可视 Segment 决定右侧 `Results · 第12页`。
- 多个 Segment 同时可见时，使用可视面积和阅读方向选择 active segment。
- active segment 切换需要短暂稳定窗口，避免滚动边界抖动。
- 点击章节跳到 `heading_segment` 或首个正文 Segment。
- `review_required/blocked` 显示结构质量提示，不伪造章节摘要。

前端不能自行用正则从 PDF TextLayer 重建另一套章节结构。

## 17. 测试与验收

### 17.1 纯函数与属性测试

- 坐标旋转和归一化。
- TextItem 行聚类。
- synthetic 空格与原文映射。
- 同栏顺序和跨栏标题规则。
- 图结构无环与拓扑顺序。
- 跨页合并和禁止条件。
- segmentation fingerprint 确定性。

可使用生成式/属性测试构造随机坐标，但不能替代真实 PDF 验收。

### 17.2 黄金版面集

每个样本保存人工标注：

- 行分组。
- 栏区域。
- 块类型。
- 正文阅读顺序。
- 段落边界。
- 标题层级和章节范围。

验收指标分开报告：

- 行/块边界匹配。
- 阅读顺序错误率。
- 段落边界准确性。
- 标题与章节角色准确性。
- `blocked` 对严重版面错误的召回。

不能用一个综合平均分掩盖“数字所在段落被串到另一栏”的严重错误。

### 17.3 医学论文重点样本

- NEJM 等常见单栏正文。
- Lancet 等复杂双栏及跨栏摘要。
- Results 中包含大量统计值和亚组描述的论文。
- 图表密集、脚注密集、参考文献跨栏的论文。
- 横向页面、补充材料和混合 OCR 文档。

样本必须具有合法测试权限；不提交受版权限制的完整论文。

### 17.4 回归门禁

以下任一回归阻止发布：

- 正文双栏顺序发生严重串列。
- 组别或统计数字因版面顺序进入错误段落。
- 原文字符映射丢失。
- 原先 `blocked` 的危险页面无依据降为 `eligible`。
- 现有人工修正无法迁移或被自动覆盖。

具体阈值必须由标注集基线确定，设计阶段不预设虚假百分比。

## 18. 实施拆分

### A1.1 坐标、行与映射

- 自然阅读坐标。
- 行候选、行文本和 synthetic 字符映射。

### A1.2 区域与栏

- 页眉页脚候选。
- 分段栏模型、宽块、表格/图片候选区域。

### A1.3 文本块与页内阅读顺序

- 块形成和分类。
- 候选图、拓扑排序和决策轨迹。

### A1.4 段落与章节

- 跨页合并。
- 标题层级、canonical role 和章节树。

### A1.5 质量、API和黄金集

- Segment 门禁。
- Section/Segment API。
- 真实论文人工标注与回归门禁。

完成 A1 后，A2 才能让浏览器自由选区准确落入共享 Segment；实时翻译 Phase 1 才能按“当前可视段落”安全请求译文。

---

本文件为设计稿。栏检测、段落边界、章节角色、性能和真实 PDF 准确性均为【未实测】。
