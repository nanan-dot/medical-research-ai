# 论文原文共享锚点层实施设计

> 状态：Phase 0 设计冻结候选稿（尚未实现）  
> 服务对象：实时翻译、批注、疑问、笔记、SW Copilot 引用、研读候选与 Evidence 追溯  
> 设计前提：原始 PDF 是最终证据源，所有派生内容必须能够返回固定文档版本

A0 TextItem 提取协议、任务编排与质量报告详见：[PDF_TEXTITEM_EXTRACTION_A0_DESIGN.md](./PDF_TEXTITEM_EXTRACTION_A0_DESIGN.md)。

A1 行、栏、文本块、段落、章节与阅读顺序详见：[PDF_LAYOUT_SEGMENTATION_A1_DESIGN.md](./PDF_LAYOUT_SEGMENTATION_A1_DESIGN.md)。

A2 浏览器自由选区、后端Quote重建与多业务共享锚点详见：[PDF_SELECTION_ANCHOR_A2_DESIGN.md](./PDF_SELECTION_ANCHOR_A2_DESIGN.md)。

A3旧资产回填、PDF换版重定位、人工确认与继承规则详见：[ANCHOR_MIGRATION_RELOCATION_A3_DESIGN.md](./ANCHOR_MIGRATION_RELOCATION_A3_DESIGN.md)。

A4长PDF窗口化、可视段落同步、定位调度与性能验收详见：[PDF_READER_PERFORMANCE_A4_DESIGN.md](./PDF_READER_PERFORMANCE_A4_DESIGN.md)。

## 1. 当前实现与缺口

现有能力：

- `Document.file_hash` 已能区分 PDF 文件版本。
- `PDFParser` 使用 `pypdf` 生成页级纯文本。
- `PdfAnnotationReader.vue` 使用 PDF.js 文本层捕获单页选区、归一化矩形与选中文字。
- `DocumentAnnotation` 保存文件哈希、页码、几何选区和原文快照。

关键断点：

1. pypdf 页级文本与 PDF.js 文本层不是同一文本流，不能直接使用字符下标互相定位。
2. 当前选区没有 PDF.js `TextItem` 身份和字符范围，文本相同处可能误定位。
3. 当前批注限制在单页；真实论文段落与用户选区可能跨页。
4. PDF 解析没有版面块、段落、章节起止页和稳定阅读顺序。
5. 翻译、会话引用与批注没有共享原文身份。
6. 当前阅读器顺序渲染全部页面，不适合长篇 PDF 的实时段落同步。

## 2. 核心不变量

### 2.1 锚点不是一个坐标

共享锚点必须同时保存四种证据：

```text
版本身份 + 逻辑文本范围 + PDF 文本层范围 + 页面几何范围
```

任何单一方式都有失效场景：

- 只有页码和矩形：换版或裁边后失效。
- 只有文本：重复句无法消歧。
- 只有字符下标：清洗或解析器更新后失效。
- 只有段落 ID：段落重建后失效。

### 2.2 精确定位与重定位分开

- 同一 `file_hash + extraction_fingerprint`：使用精确定位，不运行模糊匹配。
- 文档或提取版本变化：旧锚点先标记失效，再运行受控重定位。
- 模糊匹配结果不能冒充原始精确锚点，必须保存方法、分数和人工确认状态。

### 2.3 派生资产保留原文快照

批注、译文、AI 引用、研读候选除引用共享锚点外，还要保留创建时的最小原文快照及哈希。锚点失效时仍能向用户说明资产原来基于什么内容。

## 3. 身份层级

```text
Document
└── DocumentAnchorRevision
    ├── SourcePage
    │   └── SourceTextItem
    ├── SourceSegment
    │   └── SourceFragment[]
    └── SourceAnchor
        └── AnchorFragment[]
```

### 3.1 `document_anchor_revisions`

每次文件或锚点提取策略改变都会产生一个不可变 Revision。

Revision应关联A3定义的`document_file_revision_id`；不能只依赖当前`Document.file_path`寻找历史文件。旧PDF字节不可用时，Anchor元数据和quote仍可保留，但必须标记原文件不可重新打开。

| 字段 | 约束与含义 |
|---|---|
| `id` | PK |
| `document_id` | FK，索引 |
| `file_hash` | 当前 PDF 内容哈希 |
| `extractor_name/version` | 后端版面提取实现版本 |
| `pdfjs_version` | 前端 PDF.js 文本层版本 |
| `normalization_version` | 文本规范化规则版本 |
| `options_hash` | 影响结果的配置哈希 |
| `extraction_fingerprint` | 上述输入和结果摘要形成的唯一指纹 |
| `state` | `pending/extracting/validating/ready/review_required/failed/stale` |
| `quality_summary_json` | 页级与文档级质量统计 |
| `created_at/finished_at` | 时间 |

唯一约束：

```text
(document_id, file_hash, extraction_fingerprint)
```

一个文档只能有一个 `ready/review_required` 的当前 Revision；旧 Revision 保留并标记 `stale`。

### 3.2 `document_source_pages`

- `anchor_revision_id`
- `page_number`：PDF 物理页，一基
- `pdf_label`：如正文印刷页码，可空，不能取代物理页
- `width/height/rotation`
- `raw_text`、`normalized_text`、`text_hash`
- `text_item_count`
- `quality_flags_json`

物理页码与论文印刷页码必须区分。所有 API 定位默认使用物理页码。

### 3.3 `document_source_text_items`

这是 PDF.js 文本层与后端的共同最小定位单元。

- `page_id`
- `item_index`：该页 PDF.js `getTextContent()` 顺序
- `text`
- `normalized_text`
- `transform_json`
- `width/height`
- `has_eol`
- `direction/font_name`
- `normalized_char_start/end`：在页规范化文本中的范围

为避免后端与浏览器 PDF.js 版本差异，锚点 Revision 显式记录 PDF.js 版本。V1 推荐使用一个受控的 Node/PDF.js 提取脚本生成文本项清单，Python 服务消费其结构化结果；不要试图用 pypdf 字符下标映射浏览器 PDF.js。

pypdf 仍可用于现有索引与文本可用性判断，但共享锚点的页面文本和文本项必须来自同一受控提取管线。

### 3.4 `document_source_segments`

- `anchor_revision_id`
- `segment_key`
- `kind`：`heading/paragraph/caption/footnote/table_note/list_item/unknown`
- `reading_order`
- `section_path_json`
- `normalized_text`
- `text_hash`
- `first_page/last_page`
- `quality_flags_json`

`segment_key` 不使用数据库自增 ID 之外的语义承诺。建议计算：

```text
hash(anchor_revision_id + reading_order + normalized_text_hash + fragment_signature)
```

跨 Revision 不承诺 key 不变；跨版本关联由重定位记录表达。

### 3.5 `document_source_fragments`

一个段落由一个或多个页面片段组成：

- `segment_id`
- `fragment_order`
- `page_id`
- `start_item_index/end_item_index`
- `start_offset/end_offset`
- `rectangles_json`
- `segment_char_start/end`

`offset` 表示首尾 TextItem 内的 UTF-16 代码单元偏移，和浏览器 DOM Range 口径一致。后端同时保存经规范化后的 Unicode 字符映射，不能假设 Python code point 下标等于浏览器 UTF-16 下标。

### 3.6 `document_source_anchors`

`SourceSegment` 是论文解析产生的逻辑单元；`SourceAnchor` 是用户或系统引用的具体范围。

- `id`
- `anchor_revision_id`
- `anchor_type`：`segment/text_range/area/page`
- `quote`、`normalized_quote`、`quote_hash`
- `prefix/suffix`
- `resolution_status`：`exact/relocated_unverified/relocated_verified/unresolved`
- `created_at`

Anchor不直接绑定某个分段算法版本。与SourceSegment的归属通过带`segmentation_revision_id`的关联表保存，使A1升级不会改变相同A0 TextItem范围的原文身份。

### 3.7 `document_anchor_fragments`

与选区相关的每页片段：

- `anchor_id`
- `fragment_order`
- `page_number`
- `start_item_index/end_item_index`
- `start_offset/end_offset`
- `rectangles_json`

支持跨页选区，不再把页码放在 Anchor 主表。

## 4. 文本规范化与映射

### 4.1 两份文本同时保留

- `raw_text`：保持提取器结果，用于审计和回放。
- `normalized_text`：用于搜索、分段、翻译和重定位。

规范化操作必须版本化，并生成双向映射：

```text
raw_range ↔ normalized_range
```

允许的 V1 规范化：

- Unicode NFC。
- 合并可解释的空白。
- 清除 NUL 等无效控制字符。
- 在可信条件下合并行尾断词。
- 标记而不是删除页眉、页脚候选。

禁止静默修改：

- 负号、减号、连字符之间的含义。
- 上下标、希腊字母、比较符。
- 数字、小数点和单位。
- 无法确定的 OCR 字符。

### 4.2 断词合并

`interven-` 换行接 `tion` 可以候选合并，但需满足：

- 同一栏或可信连续阅读流。
- 前项以词内连字符候选结尾。
- 后项满足词形条件。
- 原始字符映射仍可恢复。

药物名、基因名、化学名称等高风险表达只标记候选，不依赖通用规则强行合并。

## 5. 版面和阅读顺序

### 5.1 V1 策略

V1 只承诺正文段落、标题、图注和脚注候选，不承诺复杂表格单元格重构。

分段步骤：

1. 按文本项坐标形成行。
2. 根据 X 区间聚类识别栏。
3. 结合纵向间距、缩进、字号和 `hasEOL` 形成块。
4. 根据栏内顺序形成阅读流。
5. 基于标题特征建立章节路径。
6. 使用页间延续特征合并跨页段落。
7. 生成质量标记并执行结构校验。

### 5.2 不可靠条件

以下情况设置 `review_required`，对应段落不得直接进入普通翻译流：

- 文本覆盖率过低或字符编码异常。
- 两栏阅读顺序无法确定。
- 大量文本项重叠或旋转异常。
- 表格内容被错误串成正文的风险高。
- OCR 置信度过低。
- 公式或统计符号丢失。

质量规则使用可配置指标，但阈值必须经真实论文集校准。

## 6. 前端选择契约

### 6.1 PDF.js 文本项标识

渲染 TextLayer 后，每个文本 Span 需要携带：

```text
data-page-number
data-text-item-index
data-anchor-revision-id
```

前端捕获选择时提交：

```json
{
  "expected_file_hash": "...",
  "expected_anchor_revision_id": 301,
  "quote": "A primary composite outcome...",
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

后端从固定 Revision 重建 quote 并进行等价校验。客户端 quote 只用于冲突诊断，不能作为事实来源。

### 6.2 跨页选择

新版阅读器允许跨页选择，但需：

- 每页生成独立 fragment。
- 确保所有 fragment 属于同一 Revision。
- 限制最大页跨度与最大字符数。
- 阅读顺序不确定时拒绝自动创建并提示分段选择。

### 6.3 点击译文回原文

后端返回 Anchor fragments。前端：

1. 先虚拟滚动到首个物理页。
2. 确保目标页完成 Canvas 和 TextLayer 渲染。
3. 按文本项与字符范围建立临时强化层。
4. 无法精确渲染时退化为几何矩形。
5. 只有 `unresolved` 才退化到页级提示，不能假装定位到段落。

## 7. 渲染性能设计

当前 `PdfAnnotationReader` 顺序渲染全部页，需要改为窗口化：

- 初始只渲染当前页及前后各一页。
- 使用 IntersectionObserver 驱动可视页加载。
- Canvas 和 TextLayer 分开管理生命周期。
- 离屏页面可释放 Canvas 像素，但保留尺寸占位和轻量定位元数据。
- 定位目标页时提高该页任务优先级。
- 页面渲染使用 generation token，文档切换或缩放后丢弃旧结果。

原文锚点用归一化坐标和 TextItem 范围，不受显示缩放影响。

## 8. 锚点创建状态机

### 8.1 Revision

```text
pending → extracting → segmenting → validating → ready
                                  ↘ review_required
            ↘ failed
ready/review_required → stale
```

`review_required` 表示部分内容仍可使用，但调用方必须检查段落级质量。`failed` 表示不能建立可信锚点层。

### 8.2 Anchor

```text
exact
  ↓ 文档/提取版本变化
unresolved
  ↓ 自动候选达到门槛
relocated_unverified
  ↓ 人工确认
relocated_verified
```

自动重定位永远不能直接进入 `relocated_verified`。

## 9. 文档更新后的重定位

### 9.1 候选生成

按以下顺序生成候选：

1. 完整 quote 的唯一精确匹配。
2. quote + prefix/suffix 的上下文匹配。
3. 规范化 quote 的近似匹配。
4. 章节路径、相对页位和几何关系辅助排序。

禁止只用向量相似度自动确定精确位置。语义相似段落可能表达不同结果。

### 9.2 评分维度

- quote 文本相似度。
- prefix/suffix 一致性。
- 章节路径一致性。
- 页码相对位移合理性。
- 文档中候选是否唯一。
- 数字、单位和专有名词是否完全一致。

只要原文包含数字、效应量、剂量等保护表达，候选对应内容必须完全一致，否则不得自动建议为高可信候选。

### 9.3 `document_anchor_relocations`

- `old_anchor_id/new_anchor_id`
- `old_revision_id/new_revision_id`
- `method`
- `score_breakdown_json`
- `status=proposed/confirmed/rejected`
- `reviewed_by/reviewed_at`

重定位不修改旧 Anchor；确认后建立关系并让派生资产选择最新已确认位置。

## 10. 现有数据迁移

### 10.1 数据库迁移

先新增锚点表，再对现有表增加可空字段：

`document_annotations`：

- `source_anchor_id` nullable FK
- `anchor_resolution_status` nullable

`citations`：

- `source_anchor_id` nullable FK

保持原有 `page_number/selection_geometry/selected_text`，不得删除。

### 10.2 后台回填

1. 为已有成功解析 PDF 建立 Anchor Revision。
2. 使用 `file_hash + page_number + selected_text + geometry` 寻找候选。
3. 唯一且精确匹配时创建 `exact` Anchor。
4. 多候选或不匹配时保持旧数据，并标记 `unresolved`。
5. 回填过程可重复执行且幂等。

旧批注在未回填前仍按现有几何位置工作。不能因为新锚点系统尚未准备好而破坏既有功能。

## 11. API

### 11.1 Manifest

```http
GET /api/v1/documents/{document_id}/anchor-manifest
```

返回 Revision、文件哈希、状态、页数、支持的锚点类型和质量摘要。

### 11.2 段落查询

```http
GET /api/v1/documents/{document_id}/source-segments?page=12
GET /api/v1/documents/{document_id}/source-segments?section_path=Results
GET /api/v1/source-segments/{segment_id}
```

响应包含 Revision 身份、段落文本、片段、章节路径、阅读顺序和质量标记。

### 11.3 创建自由选区锚点

```http
POST /api/v1/documents/{document_id}/source-anchors
```

后端校验：

- 文档与 Revision 当前有效。
- TextItem 和偏移范围存在。
- fragments 按阅读顺序连续。
- 后端重建 quote 与请求 quote 等价。
- 字符数和页跨度未超限。

### 11.4 定位和重定位

```http
GET  /api/v1/source-anchors/{anchor_id}
POST /api/v1/source-anchors/{anchor_id}/relocation-candidates
POST /api/v1/source-anchors/{anchor_id}/relocations/{relocation_id}/confirm
POST /api/v1/source-anchors/{anchor_id}/relocations/{relocation_id}/reject
```

人工确认接口必须有乐观并发版本，避免同时确认不同位置。

## 12. 错误码

- `ANCHOR_REVISION_NOT_READY`
- `ANCHOR_REVISION_CONFLICT`
- `TEXT_ITEM_NOT_FOUND`
- `TEXT_RANGE_INVALID`
- `QUOTE_MISMATCH`
- `READING_ORDER_UNCERTAIN`
- `SELECTION_TOO_LARGE`
- `ANCHOR_UNRESOLVED`
- `RELOCATION_AMBIGUOUS`
- `RELOCATION_VERSION_CONFLICT`

## 13. 验收标准

### 13.1 确定性测试

- UTF-16 offset 与 Python 字符映射覆盖 BMP、emoji、组合字符和希腊字母。
- 缩放、设备像素比和旋转后坐标仍能定位。
- 同页重复句通过 TextItem 范围区分。
- 跨页段落形成多个 fragment 且顺序正确。
- 双栏论文不会按左右交替错误串行。
- 数字、负号、比较符和上/下标不因规范化改变。

### 13.2 集成测试

- PDF.js 提取清单与浏览器 TextLayer 使用相同版本和 TextItem 顺序。
- 从选择创建 Anchor，再重新加载并精确定位。
- 文档切换过程中旧请求不会写入新文档。
- 批注、译文和 Copilot 引用共享同一 Anchor。
- 旧批注回填失败时仍保留原几何显示。

### 13.3 真实 PDF 验收集

至少覆盖：

- 单栏、双栏和三栏排版。
- 跨页段落、页眉页脚和连字符断词。
- 图注、脚注、表注、公式和统计符号。
- 纯扫描、混合 OCR 和含旋转页 PDF。
- 英文为主且包含希腊字符、上下标和特殊单位的医学论文。

具体准确率和阈值需在人工标注集上确定；设计阶段均为【未实测】。

## 14. 开发拆分

### A0：提取契约

- 固定 PDF.js 版本与结构化 TextItem Schema。
- 生成 Anchor Revision 和页级质量报告。

### A1：段落与定位

- 行、栏、块、段落和阅读顺序。
- SourceSegment/Fragment API。
- 前端文本项标识与点击定位。

### A2：自由选区

- 单页及跨页 SourceAnchor。
- 后端 quote 重建校验。
- 批注接入共享 Anchor。

### A3：迁移与重定位

- 旧批注/引用回填。
- 版本变化后的候选生成和人工确认。

### A4：性能与验收

- PDF 页面窗口化渲染。
- 长文性能、并发、旧请求保护和真实 PDF 验收。

完成 A0–A3 后，实时翻译 Phase 1 才能建立在稳定原文身份上。

---

本文件是实施设计，不代表功能已经完成。算法阈值、浏览器兼容性与真实 PDF 准确性均为【未实测】。
