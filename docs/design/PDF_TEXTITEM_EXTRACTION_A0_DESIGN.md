# A0｜受控 PDF.js TextItem 提取与 Anchor Revision 设计

> 状态：实施设计（尚未实现）  
> 上游：`Document`、受控 PDF 原文件  
> 下游：共享原文锚点、实时翻译、批注定位、Copilot 引用  
> 相关设计：[DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md](./DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md)

## 1. A0 交付目标

A0 只负责把固定 PDF 版本转换为确定、可校验的页面和 PDF.js TextItem 清单，并创建 `DocumentAnchorRevision`。它不负责段落语义分类、翻译或 AI 解释。

完成条件：

1. 同一 PDF、同一工具链和同一配置重复执行，产出相同的规范化结果哈希。
2. 后端产出的 `item_index` 与浏览器阅读器使用的 PDF.js TextItem 顺序一致。
3. 每页都有原始 TextItem、页尺寸、旋转信息、质量指标和安全错误。
4. 中断、超时或进程崩溃不会留下冒充 `ready` 的 Revision。
5. 文件、PDF.js、规范化规则或提取配置变化时产生新 Revision，不覆盖旧结果。

## 2. 独立工具包

不能让后端隐式依赖 `frontend/node_modules`。建议增加独立工具包：

```text
tools/pdf_textitem_extractor/
├── package.json
├── package-lock.json
├── tsconfig.json
├── src/
│   ├── cli.ts                 # CLI 入口与退出码
│   ├── contract.ts            # 输入输出类型和 Schema 版本
│   ├── extract-document.ts    # 文档级编排
│   ├── extract-page.ts        # 单页 PDF.js 提取
│   ├── normalize.ts           # 仅 TextItem 层稳定规范化
│   ├── quality.ts             # 页级确定性指标
│   ├── checksum.ts            # 规范序列化和哈希
│   └── errors.ts              # 安全错误分类
└── tests/
```

### 2.1 版本规则

- `pdfjs-dist` 使用精确版本，不使用 `^` 或 `~`。
- 前端阅读器和提取工具的 PDF.js 版本必须由同一版本常量或 CI 检查约束。
- `contract_schema_version`、`normalization_version` 和 `extractor_version` 独立版本化。
- 升级 PDF.js 必须运行黄金 PDF 回归集；不能只依赖 TypeScript 编译通过。

当前前端声明为 `pdfjs-dist ^6.2.108`。实施 A0 时应收敛到精确版本；此设计不直接修改依赖文件。

### 2.2 构建与运行

生产运行只执行已构建的 JavaScript，不在请求处理中即时编译 TypeScript。后端配置显式指定：

```text
PDF_TEXTITEM_EXTRACTOR_COMMAND
PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS
PDF_TEXTITEM_EXTRACTOR_MAX_PAGES
PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE
PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES
```

启动健康检查验证命令存在且版本兼容；能力不可用时返回明确 `UNAVAILABLE`，不能回退到 pypdf 下标并声称精确兼容。

## 3. 子进程安全边界

### 3.1 输入方式

后端已经通过 `DocumentPreviewService` 解析并授权 PDF 路径。提取器接收解析后的绝对路径，但必须满足：

- 路径属于受控文档资产或已授权知识源。
- 文件哈希与 `Document.file_hash` 一致。
- 媒体类型和 PDF 签名已校验。
- 不接受 URL，不执行网络访问。
- 命令参数使用参数数组，禁止 `shell=True`。

### 3.2 输出方式

提取器将 NDJSON 写到 stdout；日志只写 stderr。后端逐行读取并验证，避免整份大型 PDF 输出一次性进入内存。

禁止日志包含完整页面文本。允许记录：文档哈希前缀、页码、TextItem 数、耗时、状态和错误码。

### 3.3 资源限制

- 文件大小沿用项目 PDF 上限，并增加提取专用上限。
- 页数、单页 TextItem 数、单 Item 字符数、总输出字节数均有硬上限。
- 子进程有总超时和无进度超时。
- 超限时终止进程树，并将 Revision 标记为 `failed` 或 `review_required`。
- 不信任 PDF 元数据中的标题、页码和字体名；写入数据库前进行长度限制。
- 禁止提取器动态加载 PDF 内 JavaScript、附件、外部 URL 或执行动作。

Windows 下终止必须覆盖子进程树；具体实现需要在开发时验证，不能假定 `process.kill()` 等同完整清理。

## 4. CLI 契约

### 4.1 命令

```text
node dist/cli.js extract \
  --input <absolute-pdf-path> \
  --expected-sha256 <file-hash> \
  --request-id <uuid> \
  --options-file <absolute-json-path>
```

临时 options 文件由后端创建在受控临时目录，权限最小化，任务结束后回收。正文不通过命令行传递，避免进入进程列表。

### 4.2 输入配置

```json
{
  "contract_schema_version": "1.0",
  "include_marked_content": true,
  "disable_normalization": false,
  "use_system_fonts": false,
  "verbosity": 0,
  "max_pages": 500,
  "max_items_per_page": 50000,
  "max_item_characters": 20000
}
```

只有影响 TextItem 结果的选项进入 `options_hash`。安全限额也保存于任务审计，但不必全部影响内容身份。

### 4.3 退出码

| 退出码 | 错误码 | 含义 |
|---:|---|---|
| 0 | `OK` | 流完整结束，仍需后端校验 trailer |
| 2 | `INVALID_ARGUMENT` | 参数或配置不合法 |
| 3 | `FILE_HASH_MISMATCH` | 文件在执行前发生变化 |
| 4 | `INVALID_PDF` | PDF 无法解析 |
| 5 | `ENCRYPTED_PDF` | 需要密码或权限禁止提取 |
| 6 | `RESOURCE_LIMIT_EXCEEDED` | 页数、Item 或输出超限 |
| 7 | `EXTRACTION_FAILED` | PDF.js 提取失败 |
| 8 | `CONTRACT_WRITE_FAILED` | 无法完整输出协议流 |

后端超时、取消和进程启动失败使用后端自己的错误码，不伪装成工具退出码。

## 5. NDJSON 输出协议

每行都是一个完整 JSON 对象，第一行 Header，随后 Page，最后 Trailer。

### 5.1 Header

```json
{
  "record_type": "header",
  "contract_schema_version": "1.0",
  "request_id": "...",
  "extractor_version": "1.0.0",
  "pdfjs_version": "6.2.108",
  "normalization_version": "textitem-norm-1",
  "file_sha256": "...",
  "options_hash": "...",
  "page_count": 38
}
```

Header 必须是第一条且只出现一次。后端立即核对请求 ID、文件哈希、Schema 和版本。

### 5.2 Page

```json
{
  "record_type": "page",
  "page_number": 12,
  "width": 612.0,
  "height": 792.0,
  "rotation": 0,
  "view_box": [0, 0, 612, 792],
  "items": [
    {
      "item_index": 0,
      "source_array_index": 0,
      "text": "RESULTS",
      "direction": "ltr",
      "transform": [12, 0, 0, 12, 72, 700],
      "width": 48.2,
      "height": 12.0,
      "font_name": "g_d0_f1",
      "has_eol": true
    }
  ],
  "styles": {
    "g_d0_f1": {
      "font_family": "serif",
      "ascent": 0.9,
      "descent": -0.2,
      "vertical": false
    }
  },
  "quality": {},
  "page_content_hash": "..."
}
```

说明：

- `source_array_index` 严格等于该对象在 `getTextContent().items` 原数组中的位置。
- `item_index` 是过滤非 TextItem 后连续的文本项序号，供阅读器 DOM Span 标记。
- 标记内容对象不得伪装成 TextItem；工具需要验证 `source_array_index` 单调递增且 `item_index` 连续。
- `transform` 使用 PDF.js 返回值，不在工具中转成浏览器 CSS 坐标。
- `styles` 只保留分段所需的受限字段。
- NaN、Infinity 和非法 Unicode 必须在工具端拒绝，禁止进入 JSON。

### 5.3 Trailer

```json
{
  "record_type": "trailer",
  "request_id": "...",
  "pages_emitted": 38,
  "items_emitted": 8421,
  "document_content_hash": "...",
  "warnings": [],
  "completed": true
}
```

后端只有在以下条件全部成立后才允许完成 Revision：

- 进程退出码为 0。
- Header 和 Trailer 各一条。
- 页码连续、无重复，数量与 Header 一致。
- 每页和全文哈希重新计算一致。
- Trailer `completed=true`。

缺少 Trailer 的流一律视为不完整，即使进程退出码恰好为 0。

## 6. 规范序列化与内容哈希

为了得到跨运行确定的哈希，不能直接对普通 `JSON.stringify()` 输出取哈希。

规范序列化规则：

- UTF-8，无 BOM。
- 对象字段按契约固定顺序或采用明确的 canonical JSON 规则。
- 数值拒绝 NaN/Infinity；几何浮点使用固定的无损可接受表达策略。
- 数组保持原始顺序。
- 哈希字段自身不参与被哈希内容。
- 文档哈希按页码顺序组合页面内容哈希。

必须用跨 Node/Python 黄金向量测试证明双方计算一致。

`extraction_fingerprint` 建议为：

```text
sha256(
  file_sha256 |
  extractor_version |
  pdfjs_version |
  normalization_version |
  options_hash |
  document_content_hash
)
```

最终 `document_content_hash` 只有完整读取 Trailer 后才能确定。因此任务创建阶段使用独立的 `request_fingerprint`：

```text
sha256(file_sha256 | extractor_version | pdfjs_version |
       normalization_version | options_hash)
```

草稿 Revision 先以 `request_fingerprint` 幂等；校验完成后才写入最终 `extraction_fingerprint`。未完成的草稿不得占用最终内容指纹唯一约束。

## 7. TextItem 规范化边界

A0 不进行段落合并，只生成后续可复现的页规范化文本和字符映射。

### 7.1 保留原始值

TextItem 的 `text` 原样保存。另生成规范化文本时，只允许：

- Unicode NFC。
- 将明确的空字符标记为质量问题。
- 按版本化规则生成空白连接符。

A0 不删除页眉页脚、不合并跨 Item 断词、不猜测栏顺序。这些属于 A1。

### 7.2 页文本连接

页规范化文本不是简单 `items.map(str).join(' ')`。连接符由以下确定性信息决定：

- 前 Item 的 `hasEOL`。
- 两个 Item 的几何间距。
- 原 Item 文本边界空白。
- 方向和旋转。

每个加入的连接字符必须记录为 synthetic mapping，使页文本范围可以映射回相邻 TextItem，而不会伪称它来自 PDF。

## 8. 页级质量报告

### 8.1 确定性指标

每页计算：

- `text_item_count`
- `non_whitespace_character_count`
- `replacement_character_count`
- `control_character_count`
- `invalid_numeric_value_count`
- `overlapping_item_pair_count`
- `out_of_bounds_item_count`
- `rotated_item_count`
- `direction_counts`
- `font_count`
- `empty_item_ratio`
- `duplicate_text_item_ratio`
- `estimated_text_coverage`

指标只陈述可观察事实，不直接声称“医学文本正确”。

### 8.2 质量标记

- `NO_SELECTABLE_TEXT`
- `VERY_LOW_TEXT_COVERAGE`
- `INVALID_CHARACTERS_PRESENT`
- `EXCESSIVE_OVERLAP`
- `OUT_OF_BOUNDS_GEOMETRY`
- `MIXED_ROTATION_COMPLEXITY`
- `TEXTITEM_LIMIT_REACHED`
- `LIKELY_SCANNED_PAGE`
- `MANUAL_REVIEW_RECOMMENDED`

### 8.3 文档级汇总

Revision 汇总：

- 正常页、待复核页、不可用页数量。
- 可选择文本页比例。
- 最大/中位 TextItem 数。
- 警告分布。
- 是否允许进入 A1。

如果部分页无文本但其他页正常，Revision 可以是 `review_required`，而不是整份失败。下游按页和段落质量门禁。

## 9. Revision 创建流程

### 9.1 复用统一任务中心

创建 `TaskRecord`：

```text
task_type = document_anchor_extraction
source_type = document
source_id = document_id
idempotency_key = anchor:{document_id}:{request_fingerprint}
```

复用现有：

- `active_idempotency_key`
- `lease_owner/lease_expires_at`
- `heartbeat_at`
- `progress/completed_units/total_units/current_item`

锚点模块只保存领域 Revision，不重复实现通用任务列表。

### 9.2 原子性

流程：

1. 校验 Document 与 PDF 路径。
2. 创建或复用幂等 Task。
3. 以 `request_fingerprint` 创建或复用 `pending` Revision 草稿，最终提取指纹暂为空。
4. Worker 领取租约并转为 `extracting`。
5. 使用数据库外临时暂存或批量事务写入 Page/TextItem。
6. 完成流校验和质量汇总。
7. 单事务写入最终 `extraction_fingerprint`，将 Revision 转为 `ready/review_required` 并标记旧 Revision `stale`。
8. 完成 Task，清除活动幂等键。

不能边读一页边让未完成 Revision 对下游可见。读取 API 只返回完成质量汇总的 Revision。

### 9.3 中断恢复

- 心跳持续更新租约。
- Worker 崩溃后，过期 Task 可以重新领取。
- 重试前删除或隔离同 Revision 的未完成页面数据，避免重复页。
- 已经拥有同一完整 `extraction_fingerprint` 的 Revision 时直接复用。
- 文件哈希在执行结束前再次校验；变化则失败并重新排队新版本。

### 9.4 进度

- Header 后设置 `total_units=page_count`。
- 每个完整校验并持久化的 Page 增加 `completed_units`。
- `current_item=第 N 页`，不写页面正文。
- 进度最多到 95%，完成 Trailer 和文档级验证后才到 100%。

## 10. 数据存储决策

TextItem 数量可能很大。V1 推荐关系表保存可查询字段，较大的 styles/quality 使用 JSON：

```text
document_anchor_revisions
document_source_pages
document_source_text_items
```

索引：

- Revision：`(document_id, state)`、`(file_hash, extraction_fingerprint)`。
- Page：唯一 `(revision_id, page_number)`。
- TextItem：唯一 `(page_id, item_index)`。

不要为 `text` 建普通 B-tree。段落搜索在 A1 形成 SourceSegment 后处理。

SQLite 写入采用有界批次，避免单条 TextItem 逐次提交；每批大小通过基准确定。任何性能数字在实测前不得写成承诺。

## 11. 后端组件

建议：

```text
app/modules/document_anchor/
├── extractor_contract.py      # NDJSON Pydantic Schema
├── extractor_runner.py        # 受控子进程、超时、流读取
├── extraction_service.py      # Revision 与 Task 编排
├── quality.py                 # 文档级质量汇总纯函数
├── fingerprint.py             # 规范哈希
├── model.py
├── repository.py
├── schema.py
├── router.py
└── errors.py
```

`extractor_runner.py` 仅负责进程协议，不直接写数据库；`extraction_service.py` 消费经过校验的记录并持久化。

## 12. API

### 12.1 创建或复用提取任务

```http
POST /api/v1/documents/{document_id}/anchor-revisions
Idempotency-Key: <uuid>
```

请求：

```json
{
  "expected_file_hash": "...",
  "force_new_toolchain_run": false
}
```

返回：

- 已有相同完整 Revision：`200`。
- 新建/复用进行中任务：`202`，返回 `task_id/revision_id`。
- 文件版本冲突：`409`。
- 提取器不可用：`503`。

`force_new_toolchain_run` 不能绕过同一内容指纹的唯一约束；它只允许重新执行诊断并比较产出。

### 12.2 查询 Revision

```http
GET /api/v1/documents/{document_id}/anchor-manifest
GET /api/v1/document-anchor-revisions/{revision_id}
GET /api/v1/document-anchor-revisions/{revision_id}/pages/{page_number}/quality
```

TextItem 清单默认不对普通页面全量开放。A1 和内部定位服务通过受限查询访问，避免前端一次拉取整篇原始文本层。

## 13. 错误与重试策略

| 错误 | 可重试 | 行为 |
|---|---|---|
| 进程启动失败 | 条件性 | 配置修复前保持失败 |
| 总超时/无进度超时 | 有限 | 指数退避，超过次数人工处理 |
| PDF.js 瞬时崩溃 | 有限 | 保留安全错误摘要 |
| 文件哈希变化 | 否 | 为新版本创建新任务 |
| 加密 PDF | 否 | 提示用户提供可读取版本，不存密码 |
| 资源上限 | 否 | 调整策略需显式审批，不自动放大 |
| 协议 Schema 不兼容 | 否 | 阻断部署或工具版本回滚 |
| Trailer 缺失/哈希失败 | 有限 | 视为输出不完整，禁止发布 Revision |

严禁失败后静默回退到不兼容的 pypdf 字符下标。

## 14. 验收门禁

### 14.1 契约测试

- Header/Page/Trailer 正常流。
- 重复 Header、缺失 Trailer、跳页、重复页、非法浮点和超大行。
- 子进程退出 0 但 Trailer 不完整时必须失败。
- Node 与 Python canonical hash 黄金向量一致。
- 不兼容 Schema 和 PDF.js 版本被拒绝。

### 14.2 确定性测试

- 同一 PDF 连续运行多次，页面和文档内容哈希一致。
- 不同系统环境使用受控工具链时结果一致；若字体依赖导致差异必须进入指纹或禁用该依赖。
- 修改配置、规范化版本或 PDF.js 版本时指纹变化。

### 14.3 安全测试

- 恶意文件名、超长元数据、损坏 PDF、PDF JavaScript、嵌入附件。
- 超页数、超 TextItem、超输出和卡死文件。
- 取消和超时后无遗留进程。
- 日志与 API 错误不泄漏正文、绝对知识源路径和命令细节。

### 14.4 真实 PDF 集

- NEJM、Lancet 等单栏/双栏论文样本。
- 带公式、希腊字母、上下标、脚注和复杂表格的医学论文。
- 扫描页、混合文本层、旋转页、受密码保护和损坏文件。

需要使用授权或可公开使用的测试文档，测试夹具不得提交受版权限制的整篇论文。

## 15. A0 完成后允许与不允许的声明

允许声明：

- 已建立与指定 PDF.js 版本一致的 TextItem 提取清单。
- 已完成确定性契约和页级技术质量检查。
- 当前 Revision 可供 A1 分段或需要人工复核。

不允许声明：

- 已正确识别医学段落或章节。
- 提取文本在语义上完全正确。
- 已支持严谨医学翻译。
- `ready` 等于医学专家审核通过。

---

本文件为设计稿。Node 子进程清理、跨平台确定性、性能上限与真实 PDF 质量均为【未实测】。
