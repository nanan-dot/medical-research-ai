# 医学文献实时翻译实施级设计

> 状态：Phase 1 已实施并完成自动化门禁；真实模型与医学专家黄金集仍待独立验证。  
> 适用范围：论文阅读页的实时翻译、双语模式与中文模式  
> 非目标：论文结论解释、临床建议、证据分级与复杂表格重排  

共享原文锚点层的详细实现见：[DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md](./DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md)。本文件不重复定义其提取、坐标和重定位算法。

## 1. 设计目标

实时翻译必须同时满足四个条件：

1. **忠实**：不增加原文没有的解释、因果关系、确定性或临床建议。
2. **可追溯**：每段译文能返回固定 PDF 版本中的具体页码与文本位置。
3. **可验证**：数字、单位、统计量、否定、比较方向和关键术语经过显式检查。
4. **可演进**：模型、提示词、术语和提取算法更新后，旧译文不会冒充当前结果。

翻译模块只回答“原文说了什么”。“结果意味着什么”属于 SW Copilot 或论文分析。

## 2. 冻结的领域规则

### 2.1 质量标签的语义

| 标签 | 精确定义 |
|---|---|
| `machine_checked` | 机器译文已通过当前版本的自动检查，不代表医学专家审核 |
| `needs_review` | 可以展示，但必须同时展示具体疑点与原文入口 |
| `blocked` | 存在可能改变科学含义的问题，不能进入普通中文阅读流 |
| `human_reviewed` | 指定译文版本已由人工确认；新版本不得继承该标签 |

禁止使用无法校准的“医学准确率 98%”或把模型自报置信度作为质量结论。

### 2.2 忠实性红线

- `associated with` 不得强化为因果表达。
- `may / might / could / suggest` 等不确定性不得消失。
- 研究组、对照组、终点、时间窗、事件数和效应量不得错配。
- `HR / RR / OR / RD` 保留原统计身份，不相互替换。
- 数字、符号、小数位、区间、单位不得重算、四舍五入或改写。
- 原文未解释 `HR 0.61` 时，翻译不得自行增加“风险降低 39%”。
- 原文明确给出的解释应忠实翻译，不能因系统红线而删去原文内容。

### 2.3 原文优先

翻译使用后端持有的固定文档版本和段落，不接受客户端提交任意文本并声称来自某篇论文。客户端只提交段落 ID 或经后端校验的选区范围。

## 3. 模块边界

原文分段与锚点是批注、翻译、Copilot、研读候选共同依赖的基础，不能由翻译模块私有。建议先新增共享模块：

```text
document_anchor/
├── model.py                   # 共享原文段落与位置片段
├── schema.py                  # 锚点只读契约
├── repository.py             # 段落和片段查询
├── service.py                # 版本校验与重定位
└── segmenter.py              # 从解析结果建立稳定段落
```

再新增 `app/modules/medical_translation/`，每个文件保持单一职责：

```text
medical_translation/
├── router.py                  # HTTP 入站与响应映射
├── schema.py                  # Pydantic 请求/响应契约
├── model.py                   # 翻译、任务与审核持久化模型
├── repository.py              # 仅处理数据库读写
├── service.py                 # 用例编排，不包含供应商细节
├── context_builder.py         # 构建最小翻译上下文
├── terminology_resolver.py    # 术语识别、消歧与优先级合并
├── protection_extractor.py    # 提取数字、单位和统计关系
├── translator.py              # 翻译供应商 Protocol 与适配器
├── validator.py               # 确定性校验与语义风险校验编排
├── cache_key.py               # 纯函数生成内容寻址键
├── state_machine.py           # 纯函数校验状态转换
├── errors.py                  # 领域异常
└── constants.py               # 阈值与领域枚举
```

依赖方向固定为：

```text
router → service → domain components → repository/provider
                         ↓
                  document_anchor
```

翻译供应商通过 `Protocol` 注入。供应商适配器不得直接写数据库，校验器也不得调用 HTTP。

## 4. 数据模型

### 4.1 复用现有文档身份

不重复创建新的论文主表。固定原文身份使用：

```text
document_id + Document.file_hash + extraction_fingerprint
```

其中 `extraction_fingerprint` 由以下内容计算：

```text
parser_name + parser_version + extraction_options + normalized_extraction_hash
```

`file_hash` 相同但解析器变化时，段落边界仍可能变化，因此必须包含提取指纹。

`medical_translation` 只能引用 `document_anchor`，不能反向被锚点模块依赖。

### 4.2 `document_source_segments`

保存可翻译的原文逻辑单元。

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `id` | PK | 段落身份 |
| `document_id` | FK, index | 复用 `documents.id` |
| `file_hash` | char(64), index | PDF 固定版本 |
| `extraction_fingerprint` | char(64), index | 提取版本 |
| `segment_key` | varchar(128) | 当前提取版本内稳定键 |
| `kind` | enum | `heading/paragraph/caption/footnote/table_note` |
| `reading_order` | int | 论文内固定阅读顺序 |
| `section_path_json` | text | 章节层级快照 |
| `raw_text` | text | 未清洗文本，不可覆盖 |
| `normalized_text` | text | 供翻译使用的规范化文本 |
| `text_hash` | char(64) | 规范化文本指纹 |
| `quality_flags_json` | text | OCR、双栏、断句、公式等风险 |
| `created_at` | datetime | 创建时间 |

唯一约束：

```text
(document_id, file_hash, extraction_fingerprint, segment_key)
```

### 4.3 `document_source_fragments`

一个逻辑段落可能跨页或有多个矩形，所以定位片段独立存储。

| 字段 | 说明 |
|---|---|
| `segment_id` | 所属段落 |
| `fragment_order` | 片段顺序 |
| `page_number` | 一基页码 |
| `rectangles_json` | 相对页面尺寸的矩形集合 |
| `source_char_start/end` | 对应原始文本字符范围 |
| `quote/prefix/suffix` | 坐标失效后的文本重定位后备信息 |

`rectangles_json` 延续现有批注使用的归一化坐标规范，避免缩放改变位置。

### 4.4 与现有批注和引用的兼容

现有 `DocumentAnnotation` 已保存 `file_hash + page_number + selection_geometry + selected_text`，迁移时保留这些字段，并新增可空字段：

- `source_segment_id`
- `source_range_json`
- `anchor_resolution_status`

旧批注可继续依靠现有坐标展示；后台逐步重定位到共享段落，不能因迁移失败删除原坐标。新批注优先同时保存共享锚点和几何位置。

现有 `Citation` 可新增可空 `source_segment_id` 与 `source_range_json`。后续翻译、Copilot、批注、疑问、笔记与研读候选统一引用共享段落，但保留各自必要的来源快照，避免段落重建后完全失去证据文本。

### 4.5 `terminology_concepts` 与 `terminology_renderings`

概念和译名分离，禁止退化成简单字符串字典。

`terminology_concepts`：

- `id`
- `semantic_type`：疾病、药物、指标、统计量、终点、试验名等
- `canonical_label`
- `external_system`、`external_id`
- `source_name`、`source_version`、`source_url`
- `license_code`

`terminology_renderings`：

- `concept_id`
- `language`
- `term_text`
- `abbreviation`
- `status`：`verified/user_preferred/model_suggested/unresolved`
- `valid_from/valid_to`

外部来源必须保留来源与版本。MeSH 用于概念识别和同义词归并，不能标记成完整英汉翻译权威；药物活性物质优先对接 WHO INN 等可核查来源。引入 UMLS 或其他词表前必须单独核验许可。

### 4.6 `terminology_overrides`

| 字段 | 说明 |
|---|---|
| `scope_type` | `document/research_context` |
| `scope_id` | 论文或研究项目 ID |
| `concept_id` | 已消歧的概念 |
| `preferred_rendering_id` 或 `custom_text` | 选定译名 |
| `reason` | 用户修订原因，可空 |
| `version` | 乐观并发版本 |

优先级只在概念已确定后应用：

```text
论文级用户确认 > 项目级用户确认 > 系统已审核译名 > 模型候选
```

### 4.7 `terminology_snapshots`

每次翻译冻结实际使用的术语集合。快照包括：

- `id`、`snapshot_hash`
- 文档与可选研究项目
- 每个概念实际使用的译名、来源、覆盖层级和版本

后续修改术语不会悄悄改变历史译文，只会使相关译文变为 `stale`。

### 4.8 `translation_jobs` 与 `translation_job_items`

任务与段落分开，允许当前页部分成功。

`translation_jobs` 关键字段：

- `id`、`document_id`、`file_hash`、`extraction_fingerprint`
- `target_language`、`mode`：`selection/visible/page/prefetch`
- `idempotency_key`、`request_fingerprint`
- `state`、`priority`
- `requested_by_scope`
- `created_at/started_at/finished_at/cancel_requested_at`

`translation_job_items` 关键字段：

- `job_id`、`segment_id`、`state`、`attempt_count`
- `lease_owner`、`lease_expires_at`
- `cache_key`、`translation_revision_id`
- `error_code/error_detail_safe`

同一请求作用域内唯一约束：

```text
(requested_by_scope, idempotency_key)
```

任务领取采用数据库租约；进程崩溃后可重新领取。不能只依赖进程内锁。

### 4.9 `translation_revisions`

译文版本不可变。字段包括：

- 原文身份：`segment_id/file_hash/extraction_fingerprint/source_text_hash`
- 翻译身份：`target_language/context_hash/terminology_snapshot_id`
- 生成身份：`provider/model/model_revision/prompt_version/policy_version`
- 校验身份：`validator_version`
- 内容：`translated_text/alignment_json`
- 状态：`quality_status/freshness_status`
- 来源：`origin=machine/human_correction`
- 链接：`supersedes_revision_id`
- 时间：`created_at`

`alignment_json` 保存源文本范围到译文范围的对应关系，但允许一对多、多对一，不强制逐句对齐。

### 4.10 `translation_validation_reports`

每次校验生成不可变报告：

- `translation_revision_id`
- `checks_run_json`
- `issues_json`
- `highest_severity`
- `deterministic_passed`
- `semantic_review_status`
- `created_at`

单项问题至少包含：

```json
{
  "code": "COMPARATOR_DIRECTION_CHANGED",
  "severity": "blocking",
  "source_span": [120, 138],
  "target_span": [51, 66],
  "message": "治疗组与对照组的比较方向可能发生变化"
}
```

### 4.11 `translation_reviews`

人工审核必须绑定具体译文版本：

- `translation_revision_id`
- `decision=approved/corrected/rejected`
- `corrected_text`
- `reason`
- `reviewer_id`
- `created_at`

修订产生新的 `translation_revision`，旧版本和旧报告保留。

## 5. 翻译上下文与提示契约

翻译模型的输入必须是结构化对象，而非字符串拼接：

```json
{
  "task": "faithful_medical_translation",
  "source_language": "en",
  "target_language": "zh-CN",
  "section_path": ["Results", "Primary Outcome"],
  "target_segment": "...",
  "preceding_context": "...",
  "following_context": "...",
  "resolved_terms": [],
  "protected_expressions": [],
  "required_output_schema_version": "1"
}
```

输出使用严格结构化 Schema：

- `translated_text`
- `alignment`
- `used_terms`
- `unresolved_terms`
- `translator_warnings`

前后文只帮助消歧，输出只能翻译 `target_segment`。上下文长度设上限，优先保留章节标题、本文缩写定义、相邻句和必要脚注。

供应商响应若无法通过 Schema 校验，应记为可分类的执行失败；不得从残缺自由文本中猜测字段并直接展示。

## 6. 数字与语义保护

### 6.1 预处理

翻译前提取并编号：

- 数字、百分比、区间、P 值、效应量、剂量、单位、时间窗。
- 研究组、比较对象、终点及其关系。
- 否定、不确定性、因果/相关表达。

保护不等于简单将数字替换成占位符。还要保存数字与对象的关系，例如：

```text
治疗组 → 197 → 9.2%
对照组 → 312 → 14.5%
效应量 → HR 0.61 → 95% CI 0.51–0.72
```

### 6.2 确定性校验

以下检查应为纯函数，可重复运行：

- 数字、多重集、符号和小数位一致。
- `<、≤、>、≥、±` 一致。
- 单位、剂量频率与时间窗一致。
- 区间上下界及所属统计量一致。
- 受保护占位符不存在丢失、重复或错位。
- 原文目标段落完整覆盖，不混入上下文译文。

### 6.3 语义风险校验

规则和独立复核模型可以发现：

- 组别或比较方向交换。
- 否定、条件和不确定性丢失。
- 相关关系强化为因果。
- 主要/次要终点混淆。
- 增加原文没有的结论或临床建议。

复核模型的意见是风险信号，不是真实准确率。存在争议时降级为 `needs_review`，命中红线时 `blocked`。

### 6.4 质量门禁

| 问题 | 默认结果 |
|---|---|
| 数字丢失或变化 | `blocked` |
| 组别/比较方向疑似交换 | `blocked` |
| 关键否定丢失 | `blocked` |
| 原文提取严重不可靠 | `blocked` |
| 专业译名存在多个合理候选 | `needs_review` |
| 模型无法解析缩写 | 保留缩写并 `needs_review` |
| 自动检查全部通过 | `machine_checked` |

阈值必须通过真实医学语料评测后配置，不硬编码为无依据常数。

## 7. 状态机

### 7.1 Job 状态

```text
queued → preparing → running → validating → completed
   │         │          │           │
   └─────────┴──────────┴──────────→ failed
             └──────────┴──────────→ cancelled
```

规则：

- `completed` 仅表示任务处理结束，不代表每条译文可正常展示。
- 取消只阻止尚未开始的条目；已完成译文仍保留。
- 失败可按错误类型有限重试；验证失败不能无限重译直到碰巧通过。

### 7.2 Item 状态

```text
pending → cache_check → translating → validating → succeeded
                     ↘ failed
pending/cache_check → cancelled
```

`succeeded` 后结合 `quality_status` 决定前端表现。

### 7.3 独立维度

- `quality_status`：`machine_checked/needs_review/blocked/human_reviewed`
- `freshness_status`：`current/stale`
- `source_status`：`ready/review_required/unavailable`

不同维度不得折叠成一个超大枚举，否则无法表达“任务成功但译文被阻断”。

## 8. 缓存和失效

### 8.1 内容寻址缓存键

```text
hash(
  access_scope,
  document_id,
  file_hash,
  extraction_fingerprint,
  segment_id,
  source_text_hash,
  target_language,
  context_hash,
  terminology_snapshot_hash,
  provider_model_revision,
  prompt_version,
  translation_policy_version,
  validator_version
)
```

权限作用域必须参与缓存隔离；缓存命中不能绕过当前访问授权。

### 8.2 缓存层

1. `translation_revisions`：持久化事实来源。
2. 进程内 LRU：可选读取加速，丢失不影响正确性。
3. 前端会话缓存：按文档和译文版本存储。

V1 不强制引入 Redis。未来多进程调度增长后，可将通知和热点读取迁入 Redis，但数据库仍是状态事实来源。

### 8.3 失效矩阵

| 变化 | 影响 |
|---|---|
| PDF `file_hash` 改变 | 当前文档全部旧段落和译文变为 `stale` |
| 提取指纹改变 | 重建段落；旧定位和译文变为 `stale` |
| 某术语覆盖改变 | 精确失效依赖该术语的译文；无法追踪时扩大至当前论文 |
| 项目词库改变 | 仅影响使用该项目上下文生成的译文 |
| 模型/提示词变化 | 旧结果可历史查看，新请求不复用旧键 |
| 校验器变化 | 可重新校验旧译文；报告新建，不覆盖旧报告 |
| 人工修订 | 产生新版本，不被后台自动重译覆盖 |
| 权限撤销 | 立即拒绝访问，不等待缓存 TTL |

### 8.4 调度优先级

```text
用户选中文字 > 当前可视段落 > 当前页其余段落 > 相邻页预取
```

相邻页预取必须受并发、速率和费用预算控制。页面打开不自动翻译全文。

## 9. API 契约

所有写请求需要当前文档版本和幂等键。

### 9.1 Manifest

```http
GET /api/v1/documents/{document_id}/translation-manifest
```

返回：当前 `file_hash`、提取指纹、原文语言、段落状态、支持的目标语言、翻译策略版本。

### 9.2 获取原文段落

```http
GET /api/v1/documents/{document_id}/translation-segments?page=12
GET /api/v1/documents/{document_id}/translation-segments?section=Results
```

返回段落、锚点、阅读顺序和原文质量标记。分页与最大条数必须受限。

### 9.3 创建翻译任务

```http
POST /api/v1/documents/{document_id}/translation-jobs
Idempotency-Key: <uuid>
```

```json
{
  "expected_file_hash": "...",
  "expected_extraction_fingerprint": "...",
  "target_language": "zh-CN",
  "mode": "visible",
  "segment_ids": [1201, 1202],
  "research_context_id": 7
}
```

后端验证段落属于当前文档版本，并解析用户有权使用的项目术语表。前端不能要求跳过质量检查。

缓存全部命中时可返回 `200` 和结果；需要执行任务时返回 `202` 和 `job_id`。

### 9.4 查询和取消任务

```http
GET  /api/v1/translation-jobs/{job_id}
POST /api/v1/translation-jobs/{job_id}/cancel
```

V1 使用带退避的轮询。后续可增加 SSE，只推送状态与已完成质量门禁的段落，不流式展示未经检查的译文正文。

### 9.5 获取译文

```http
GET /api/v1/documents/{document_id}/translations?segment_ids=1201,1202
```

单条译文返回：

```json
{
  "translation_revision_id": 8801,
  "segment_id": 1201,
  "translated_text": "……",
  "quality_status": "machine_checked",
  "freshness_status": "current",
  "source_anchors": [],
  "alignment": [],
  "issues": [],
  "terms": [],
  "provenance": {
    "origin": "machine",
    "model_revision": "...",
    "prompt_version": "...",
    "validator_version": "..."
  }
}
```

### 9.6 术语与审核

```http
GET    /api/v1/documents/{id}/terminology
GET    /api/v1/documents/{id}/terminology/{concept_id}/occurrences
PUT    /api/v1/documents/{id}/terminology/{concept_id}/override
DELETE /api/v1/documents/{id}/terminology/{concept_id}/override
POST   /api/v1/translations/{revision_id}/reviews
```

更新覆盖时提交 `expected_version`，发生并发冲突返回 `409`。

### 9.7 统一错误码

- `DOCUMENT_REVISION_CONFLICT`
- `EXTRACTION_REVISION_CONFLICT`
- `SOURCE_EXTRACTION_UNRELIABLE`
- `SEGMENT_NOT_FOUND`
- `SELECTION_OUT_OF_RANGE`
- `TERMINOLOGY_CONFLICT`
- `TRANSLATION_BLOCKED`
- `PROVIDER_UNAVAILABLE`
- `JOB_LEASE_EXHAUSTED`

错误详情不能泄漏完整论文正文、供应商密钥或内部提示词。

## 10. 前端状态映射

建议新增：

```text
frontend/src/api/medicalTranslation.ts
frontend/src/types/medicalTranslation.ts
frontend/src/composables/useMedicalTranslation.ts
frontend/src/stores/medicalTranslationStore.ts
```

页面组件只消费组合式函数提供的状态，不自行拼装缓存键或推断质量。

### 跟随阅读

- IntersectionObserver 只上报稳定可见的段落集合。
- 150–250ms 合并快速滚动产生的变更。
- 新可视段落提升任务优先级；离开视口不删除缓存。
- 请求返回的文档版本与当前阅读器不一致时丢弃展示结果并刷新 Manifest。

### 三种阅读模式

- 原文：PDF 原始版式，右侧可翻译。
- 双语：按共享锚点展示原文和合格译文。
- 中文：按固定阅读顺序展示译文；`blocked` 段落保留原文及阻断提示。

所有模式使用同一个 `translation_revision_id`，避免右栏、双语和中文模式出现不同译文。

### UI 文案

- `machine_checked`：机器译文 · 已完成自动检查
- `needs_review`：译文存在待核对项
- `blocked`：该段暂不提供译文，请核对原文
- `human_reviewed`：人工已审核，并显示审核时间和版本

“AI 内容仅供参考”不能替代具体问题说明。

## 11. 隐私、安全与审计

- 本地文档发送第三方模型前必须经过模型隐私设置与用户授权检查。
- 供应商请求日志默认不记录全文；仅记录请求 ID、内容哈希、耗时和状态。
- 对外发送内容遵守最小化原则，只发送目标段落和必要上下文。
- 用户术语和人工修订具有访问作用域，不能跨项目泄漏。
- 所有译文保存模型、提示词、术语和校验版本，支持问题追溯。
- 术语数据源接入前审查许可证、署名和再分发条件。

## 12. 验收门禁

### 12.1 必测语料类型

- 否定、双重否定、推测和条件句。
- 随机试验、观察研究、非劣效和诊断准确性表达。
- HR/RR/OR、置信区间、P 值、亚组和交互检验。
- 药物剂量、单位、时间窗、分子/基因/蛋白名称。
- 组别数据、复合终点和多个相似数字。
- 双栏、跨页段落、图注、脚注和 OCR 缺陷。
- 同一缩写的不同含义与用户术语覆盖。

### 12.2 测试层级

1. 纯函数：缓存键、状态机、数字保护、关系校验。
2. Repository：唯一约束、租约抢占、乐观锁和失效查询。
3. Service：缓存命中、部分失败、有限重试、取消和版本冲突。
4. API：权限、幂等、错误码、分页和响应契约。
5. 前端：快速滚动、旧请求保护、模式一致、点击译文回到原文。
6. 医学评测：盲评忠实度、术语准确性、重大错误率及问题召回。

上线门禁以重大语义错误为核心，不以 BLEU 或模型自评分单独决定。具体阈值必须在医学专家审核的基准集上确定并记录依据。

## 13. 分阶段实施

### Phase 0：共享原文身份

- 建立 `document_anchor` 共享模块。
- 生成固定版本的段落、阅读顺序与多片段坐标。
- 为现有批注和会话引用增加可空共享锚点。
- 验证文档更新后的失效与人工重定位策略。

### Phase 1：最小可信闭环

- 英文正文段落。
- 固定原文锚点。
- 论文级术语快照。
- 数字、单位、统计表达和关键语义检查。
- 右侧实时翻译、回到原文、人工修订。

### Phase 2：阅读体验

- 当前页与相邻页受控预取。
- 双语及中文模式。
- 本文术语出现位置。
- 项目级术语继承。

### Phase 3：扩展内容

- 可靠图注、表注与脚注翻译。
- 复杂表格在保留行列身份前提下逐步开放。
- 基于真实评测结果优化语义风险检测。

## 14. 关键设计结论

1. 文档版本、提取版本、术语版本、模型版本和校验版本共同决定译文身份。
2. 任务完成状态与译文质量状态必须分离。
3. 数据保护必须校验“数字属于谁”，不能只比较字符串。
4. 自动检查通过不等于人工医学审核。
5. 人工修订是不可变的新版本，不能被后台重译覆盖。
6. 实时体验来自内容寻址缓存和受控预取，而不是抢先展示未经检查的流式文本。
7. 原文是最终证据源；翻译、术语和 SW Copilot 都必须返回同一原文锚点。

## 15. 规范依据

- NLM MeSH：受控词表用于生物医学信息索引、检索及概念一致性，不直接等同完整英汉翻译词典。  
  https://www.nlm.nih.gov/mesh/intro_preface.html
- WHO INN：药物活性物质的国际通用命名体系。  
  https://www.who.int/teams/health-product-and-policy-standards/inn
- Cochrane Handbook：效应量、置信区间和结果解释需保持对应统计语境。  
  https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
- Cochrane AI 翻译指导：AI 翻译需设置质量流程与人工审阅边界。  
  https://documentation.cochrane.org/spaces/TH/pages/493551784/
- 全国科学技术名词审定委员会：中文科技名词规范来源之一。  
  https://www.cnctst.cn/
- UMLS 许可说明：使用源词表前必须核验具体许可与再分发条件。  
  https://www.nlm.nih.gov/research/umls/new_users/online_learning/OVR_005.html

---

本文件是实施设计，不代表功能已经完成或通过真实医学语料验证。所有运行与质量结果在实现和验收前均标记为【未实测】。
