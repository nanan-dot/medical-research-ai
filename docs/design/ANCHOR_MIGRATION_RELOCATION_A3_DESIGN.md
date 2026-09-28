# A3｜旧资产迁移、跨版本重定位与人工确认设计

> 状态：实施设计（尚未实现）  
> 目标：在不破坏既有批注和AI引用的前提下接入共享原文锚点，并安全处理PDF换版  
> 核心原则：历史事实不可改写，自动候选不可冒充人工确认

关联设计：

- [共享原文锚点](./DOCUMENT_ANCHOR_FOUNDATION_DESIGN.md)
- [A2自由选区与共享锚点](./PDF_SELECTION_ANCHOR_A2_DESIGN.md)

## 1. 现有资产的证据强度不同

### 1.1 旧批注

已有字段：

```text
document_id + file_hash + page_number + selection_geometry
+ selected_text + selected_text_hash
```

如果同一`file_hash`的PDF仍能访问，旧批注具备建立精确Anchor的必要信息，但仍需TextItem/Quote/Geometry联合校验。

### 1.2 旧AI Citation

已有字段：

```text
document_id + page + section + evidence_text + citation_text
```

它没有保存：

- 生成时的`file_hash`。
- Anchor/Extraction Revision。
- TextItem范围与几何位置。

因此旧Citation不能证明摘录对应哪个PDF版本。即使当前PDF中找到相同文本，也只能生成重定位候选，不能直接标记为历史精确引用。

### 1.3 历史资产状态

统一使用：

```text
legacy_exact_candidate
legacy_unversioned
anchored_exact
relocation_required
relocated_unverified
relocated_verified
unresolved
```

状态含义必须向用户透明；`legacy_unversioned`不能在UI中显示为“已核验原文”。

## 2. 数据模型

### 2.1 `document_anchor_relocations`

| 字段 | 说明 |
|---|---|
| `id` | PK |
| `source_anchor_id` | 原版本Anchor |
| `target_anchor_revision_id` | 目标A0 Revision |
| `candidate_anchor_id` | 候选新Anchor |
| `method` | 候选方法 |
| `algorithm_version` | 重定位算法版本 |
| `score_breakdown_json` | 各维度原始分数，不只保存总分 |
| `protected_token_status` | 数字/单位/统计表达校验状态 |
| `status` | `proposed/confirmed/rejected/superseded` |
| `decision_source` | `human/system_policy`；V1确认只允许human |
| `reviewer_id/reviewed_at` | 人工确认审计 |
| `decision_note` | 可选说明 |
| `created_at` | 创建时间 |

唯一约束：

```text
(source_anchor_id, target_anchor_revision_id, candidate_anchor_id,
 algorithm_version)
```

同一Source Anchor和目标Revision最多有一个`confirmed`候选。

### 2.2 `asset_anchor_links`

业务资产与原始/当前定位分开：

- `asset_type/asset_id`
- `original_anchor_id`
- `resolved_anchor_id` nullable
- `resolution_status`
- `resolution_version`
- `updated_at`

`original_anchor_id`创建后不可变。确认重定位只更新`resolved_anchor_id`和状态，因此永远能知道资产最初基于哪个原文版本。

对于已有专用FK（如`document_annotations.source_anchor_id`），该FK视为original anchor；可增加`resolved_source_anchor_id`，或者统一通过`asset_anchor_links`查询。实施时选一种，不同时维护两套可漂移真相。

### 2.3 `legacy_anchor_backfill_runs`

- `id/task_id`
- `asset_type`
- `source_schema_version`
- `target_anchor_revision_id`
- `mode=dry_run/apply`
- `cursor`
- `total/scanned/exact/candidate/unresolved/failed`
- `algorithm_version`
- `status`
- `report_json`
- `created_at/finished_at`

迁移任务可恢复、可审计，不在Alembic升级事务中运行全文匹配。

### 2.4 `legacy_anchor_backfill_items`

- `run_id`
- `asset_type/asset_id`
- `legacy_identity_hash`
- `result_status`
- `anchor_id` nullable
- `candidate_count`
- `reason_codes_json`
- `error_code`

唯一约束`(run_id, asset_type, asset_id)`，保证任务重试幂等。

### 2.5 `document_file_revisions`

现有`Document`主要表达当前文件状态，不能单独承担历史PDF版本。建议增加文件版本登记：

- `id/document_id`
- `file_hash/file_size/modified_time_ns`
- `storage_kind=managed/external/snapshot_unavailable`
- `storage_reference`：受控内部引用，不直接对API暴露路径
- `is_current/is_content_available`
- `discovered_at/superseded_at`
- `retention_status=retained/pending_cleanup/metadata_only`

`DocumentAnchorRevision`应关联`document_file_revision_id`。`file_hash`继续冗余保存用于快速冲突校验。

必须区分三件事：

1. 文件版本元数据仍存在。
2. Anchor的quote和位置快照仍存在。
3. 旧PDF字节仍可打开。

三者不能用一个`available`布尔值混淆。

受管上传文件可以按明确保留策略保存旧版本；外部知识源文件被用户替换后，系统不能假定有权或有能力私自复制旧文件。无法保留旧字节时设为`metadata_only/snapshot_unavailable`，UI明确说明旧版原文件不可打开。

## 3. 数据库迁移策略

### 3.1 仅做加法迁移

第一阶段Alembic只执行：

- 创建Anchor、Relocation、Backfill表。
- 为`document_annotations`增加可空Anchor字段或建立统一链接表。
- 为`citations`增加可空`source_anchor_id`和`anchor_status`。
- 必要时增加消息上下文表。

不得在Schema迁移中：

- 遍历全文做匹配。
- 删除旧页码、几何、摘录字段。
- 将历史引用批量标成已验证。
- 因回填失败阻断应用启动。

### 3.2 双读阶段

读取优先级：

```text
confirmed resolved anchor
→ original exact anchor
→ legacy geometry/text snapshot
→ unresolved提示
```

写入新资产必须走A2；旧写接口在兼容窗口内可以继续，但新版本前端不再调用。

### 3.3 回滚

应用回滚时旧字段仍可工作。数据库downgrade可以移除新增链接字段/表，但执行前必须：

- 生成迁移统计与孤立新资产报告。
- 阻止存在仅新Schema可表达的跨页资产时直接降级。
- 提供导出或明确不可逆提示。

不能声称所有包含用户新数据的Schema downgrade都无损。

## 4. 旧批注回填

### 4.1 前置条件

- 找到与`annotation.file_hash`一致的PDF资产。
- 对该文件版本建立A0 Revision。
- 页码有效。
- Annotation未软删除。

如果旧文件版本已经丢失，只保留legacy记录，状态为`unresolved`，不能用当前PDF冒充旧版本。

### 4.2 候选生成顺序

1. 在指定页查找`selected_text`规范化后的精确匹配。
2. 将匹配范围映射到TextItem范围。
3. 计算候选范围的页面几何。
4. 与旧`selection_geometry`比较。
5. 检查`selected_text_hash`、数字和特殊符号。

只有文本唯一匹配、保护字符一致、几何相符且范围可重建时，才创建`anchored_exact`。

多候选时保存候选，不按第一个结果回填。

### 4.3 几何比较

使用矩形集合重叠与中心距离，不要求浮点完全相等，因为PDF.js版本和字体度量可能有细微差异。阈值必须在旧批注样本上校准。

几何严重不一致时，即使文本唯一也进入人工候选，防止页眉、引用或重复摘要误匹配。

### 4.4 软删除

默认不回填`deleted_at`非空批注；若审计要求保留删除资产的Anchor，只在离线审计模式处理，普通UI继续隐藏。

## 5. 旧Citation回填

### 5.1 默认状态

所有缺少历史`file_hash`的Citation初始标记`legacy_unversioned`。

禁止依据以下事实自动提升：

- 当前Document碰巧只有一个PDF。
- Citation创建时间晚于当前文件修改时间。
- 当前页找到相同evidence_text。

这些只能增加候选可信度，不能证明历史版本身份。

### 5.2 候选定位

可以在当前或用户选择的目标Revision中按以下信息生成候选：

- `evidence_text`精确或严格规范化匹配。
- `page`作为辅助，不作为硬事实。
- `section`与A1章节路径相符。
- `citation_text`中的可解析来源线索。
- 数字、单位、统计表达完全一致。

找到唯一候选后状态仍为`relocated_unverified`。用户确认后才是`relocated_verified`。

### 5.3 Citation语义

确认定位只说明“这段摘录位于该PDF位置”，不重新证明旧AI回答正确。回答质量、引用支持关系需要独立审核。

## 6. PDF版本变化检测

当`Document.file_hash`变化：

1. 结束旧`document_file_revision`的current状态，登记新文件版本。
2. 当前A0 Revision变`stale`，但仍保留。
3. 依赖它的业务资产标记`relocation_required`。
4. 创建新A0/A1 Revision。
5. 后台按优先级生成重定位候选。
6. UI继续展示旧资产内容和旧原文快照，但不在新PDF上绘制旧坐标。

文件变化不能直接覆盖`DocumentAnnotation.file_hash`或旧Anchor。

## 7. 重定位候选算法

### 7.1 候选阶段

按成本和证据强度：

1. 完整Quote严格匹配。
2. 规范化Quote严格匹配。
3. Quote加Prefix/Suffix上下文匹配。
4. 章节、相对位置和几何辅助的近似文本匹配。

向量相似度只能作为召回候选的低权重信号，不能单独确认位置。

### 7.2 保护表达

从旧Quote提取：

- 数字、百分比、区间。
- HR/RR/OR/P值等统计表达。
- 单位、剂量、时间窗。
- 试验名、药物名、基因/蛋白候选。
- 否定词和比较方向词。

候选缺失或改变关键保护表达时不得成为高可信候选。

### 7.3 分数维度

```text
quote_exactness
context_similarity
protected_token_match
section_path_match
relative_position_consistency
geometry_consistency
candidate_uniqueness
```

保存所有原始分量和规则版本。总分只用于排序，不作为“已验证”标签。

### 7.4 候选数量

返回有限个排序候选，并明确：

- 为什么匹配。
- 哪些信息不一致。
- 是否存在同分候选。
- 原/新页码和章节。

没有达到最低候选门槛时保持`unresolved`，不强行给用户一个结果。

## 8. 人工确认工作流

### 8.1 UI对比

确认界面至少展示：

- 旧原文快照、旧页码和旧版本标识。
- 新候选原文、新页码和章节。
- 字符级差异。
- 数字/单位/统计表达差异。
- 候选方法和风险提示。

默认不只显示相似度百分比。

### 8.2 决策

- `确认位置`：建立confirmed relocation，更新resolved link。
- `不是此处`：候选标记rejected，返回其他候选。
- `暂不处理`：保持unverified/unresolved。
- `手动重新选择`：通过A2创建新Anchor后确认关系。

### 8.3 并发

提交：

- `expected_resolution_version`
- `candidate_id`
- `decision`

如果另一窗口已经确认不同候选，返回409并重新加载。不得最后写入者静默覆盖。

### 8.4 撤销确认

不删除历史决策。原confirmed记录改为`superseded`，创建新的决策记录，并递增resolution version。

## 9. 资产继承规则

### 9.1 用户批注、笔记和标记

- 内容保持不变。
- 确认重定位后可在新PDF位置展示。
- 显示“原建于旧版本，已重定位”。
- 自动候选未确认前不在新PDF绘制为普通高亮。

### 9.2 疑问

- 问题文本保持。
- 确认新位置后关联resolved anchor。
- 如果原文发生实质变化，问题状态增加`source_changed_review_required`，不能自动保持“已解决”。

### 9.3 机器译文

- 旧译文保留历史。
- 原文Quote有任何变化时标记`stale`并重新翻译。
- 即使Quote相同，术语、模型或校验版本变化仍按翻译缓存规则判断。
- 旧`human_reviewed`标签不自动授予新译文版本。

### 9.4 人工修订译文

人工修订文本保留。若新Quote完全相同，可以作为候选复用，但仍需明确确认其适用于目标版本；不能自动复制`human_reviewed`。

### 9.5 Copilot消息与回答

- 历史问题和回答不可改写。
- 上下文Anchor可显示已确认的新位置。
- 回答Citation的重定位不等于回答重新验证。
- 用户要求针对新版重新解释时创建新消息，不覆盖旧回答。

### 9.6 研读候选

- 原文完全相同且定位确认后保持候选内容，增加版本迁移记录。
- 原文变化时状态改为`source_changed_review_required`。
- 不自动晋升正式科研资产。

### 9.7 Claim与Evidence

如果未来正式Claim/Evidence引用旧Anchor：

- 原文变化或仅近似匹配时必须重新人工核对。
- 在重新确认前标记来源版本已变化。
- 不允许重定位服务自动改写Claim/Evidence正文或确认状态。

## 10. 批量迁移任务

### 10.1 Dry Run优先

首次运行必须先`dry_run`，输出：

- 各资产数量。
- 可精确回填、存在多个候选、旧版本丢失、无法解析数量。
- 预计新增Anchor/候选数量。
- 典型失败原因。

用户确认实施计划后再运行apply。设计文档不能将dry run结果当成已执行结果。

### 10.2 任务身份

复用`TaskRecord`：

```text
task_type = legacy_anchor_backfill
idempotency_key = backfill:{asset_type}:{source_schema_version}:
                  {target_revision_id}:{algorithm_version}:{mode}
```

### 10.3 批次与游标

- 按主键升序分页，不使用易漂移offset。
- 每批独立短事务。
- 持久化最后成功游标。
- 单项失败记录后继续；系统性错误停止任务。
- 重试不会复制Anchor或链接。

### 10.4 速率和资源

迁移优先级低于用户当前选区、翻译和阅读定位。提供暂停/取消，避免批量文本匹配占满SQLite写锁或CPU。

## 11. API

### 11.1 迁移管理

```http
POST /api/v1/document-anchors/backfill-runs
GET  /api/v1/document-anchors/backfill-runs/{run_id}
POST /api/v1/document-anchors/backfill-runs/{run_id}/cancel
GET  /api/v1/document-anchors/backfill-runs/{run_id}/report
```

Apply模式属于管理操作，普通阅读用户不能触发全库迁移。

### 11.2 候选与确认

```http
POST /api/v1/source-anchors/{anchor_id}/relocation-candidates
GET  /api/v1/source-anchors/{anchor_id}/relocation-candidates
POST /api/v1/source-anchors/{anchor_id}/relocations/{id}/decisions
```

### 11.3 待处理列表

```http
GET /api/v1/documents/{document_id}/anchor-resolution-issues
```

支持按资产类型、状态、页码和创建时间筛选；列表默认不返回完整原文。

## 12. 错误码

- `LEGACY_SOURCE_REVISION_MISSING`
- `LEGACY_ASSET_UNVERSIONED`
- `BACKFILL_ALREADY_RUNNING`
- `BACKFILL_SYSTEMIC_FAILURE`
- `RELOCATION_TARGET_REVISION_STALE`
- `RELOCATION_NO_CANDIDATE`
- `RELOCATION_AMBIGUOUS`
- `RELOCATION_PROTECTED_TOKEN_MISMATCH`
- `RESOLUTION_VERSION_CONFLICT`
- `DOWNGRADE_WOULD_LOSE_NEW_ASSETS`

## 13. 安全、隐私与审计

- 迁移报告不包含完整论文正文或用户笔记内容。
- 候选对比只向有权访问该文档和资产的用户展示。
- 不将全文发送给外部模型进行重定位；V1优先本地确定性匹配。
- 每次确认、拒绝和撤销保存操作者、时间、算法版本和候选差异。
- 日志使用资产ID、Anchor ID和哈希，不记录完整quote。
- 清理旧PDF版本前检查是否仍有未迁移资产；不得因节省空间破坏可追溯性。
- 文件保留策略必须考虑存储配额、来源授权和用户删除意图；不能为了可追溯性无限复制外部受版权保护文件。

## 14. 测试与验收

### 14.1 旧批注回填

- 同页唯一文本与几何一致时精确回填。
- 同页重复文本依靠几何消歧。
- 多候选不自动选择第一项。
- 文件哈希对应旧PDF不存在时保持unresolved。
- 软删除批注不进入普通回填。

### 14.2 旧Citation

- 无file_hash引用始终从legacy_unversioned开始。
- 当前PDF唯一匹配也不能自动变成anchored_exact。
- 数字或统计表达变化阻断高可信候选。
- 定位确认不改变原回答内容与质量状态。

### 14.3 版本重定位

- 仅页码变化、正文不变。
- 出版版本增加页眉导致坐标变化。
- 段落改写但语义相似。
- 同一结果在摘要和正文重复。
- 治疗组/对照组数字发生改变。
- 章节移动、拆分或合并。

### 14.4 迁移韧性

- Dry run不写Anchor链接。
- 批次中断后从游标恢复。
- 同一任务重复执行不产生重复数据。
- 单项坏数据不回滚已完成批次。
- 系统性Schema错误停止任务。
- 新Schema资产存在时危险downgrade被阻断或明确警告。

### 14.5 严重门禁

以下任一情况阻止发布：

- 旧Citation无版本信息却被自动标成精确引用。
- 多候选时自动选择错误位置。
- 数字/组别变化后旧Evidence仍显示已确认。
- PDF换版直接覆盖旧Anchor或批注file_hash。
- 回填失败导致旧批注不可查看。
- 撤销确认删除审计历史。
- 迁移任务泄漏论文正文或用户笔记。

## 15. 实施拆分

### A3.1 Additive Schema

- DocumentFileRevision、Relocation、AssetAnchorLink、Backfill Run/Item。
- 旧表可空字段和双读契约。

### A3.2 旧批注回填

- Dry run、精确Text/Geometry匹配和幂等批次。

### A3.3 旧Citation候选

- legacy_unversioned状态、严格候选生成和风险提示。

### A3.4 换版重定位与人工确认

- 候选评分、对比界面契约、乐观锁和撤销。

### A3.5 资产继承与回归

- 翻译、Copilot、研读候选、Claim/Evidence状态传播。
- 回滚保护和真实换版样本验收。

---

本文件为设计稿。历史数据规模、候选准确性、SQLite迁移性能与真实换版行为均为【未实测】。
