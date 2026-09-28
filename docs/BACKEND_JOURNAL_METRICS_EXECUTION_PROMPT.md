# 后端执行总提示词：PubMed 近 15 年检索 × 近 10 年期刊指标

> 使用方式：将本文件全文交给 Codex 执行。本提示词只授权后端、数据库迁移、后端测试和后端文档修改；不得修改 `frontend/`。

## 1. 你的角色与最终目标

你是本仓库的高级 FastAPI、SQLAlchemy 2.0、Alembic、Pydantic v2 和异步 Python 工程师。请在现有架构内完整实现以下后端能力：

1. 所有 PubMed 检索默认并强制限制在滚动最近 15 个自然年内。
2. 从 PubMed EFetch XML 真实解析并保存 `ISSN`、`eISSN`、`ISSN-L` 和期刊缩写。
3. 支持用户将合法获得的期刊指标 CSV 导入本地 SQLite。
4. 保存和查询最近 10 个指标年度。
5. 按 `ISSN-L → ISSN → eISSN → 标准化期刊名` 匹配论文与期刊指标。
6. 在论文分页 API 中返回最新可用的 IF、IF 年份、JCR 最佳 Q 区、JCR 年份、SCIE/SSCI/ESCI/AHCI、WoS 年份、中科院分区和中科院年份。
7. 提供单篇论文对应期刊的最近 10 年指标详情接口。
8. 提供导入预览、正式提交、批次列表、激活和归档接口。
9. 保持旧 `items_json` 快照、现有检索历史、BibTeX、排序、评分、去重和收藏功能兼容。

只有全部验收条件均有对应测试且所有验证命令真实通过，才可声明后端完成。

## 2. 开始前必须执行

先完整阅读：

- `AGENTS.md`
- `docs/CODE_STANDARDS.md`
- `app/integrations/pubmed/schemas.py`
- `app/integrations/pubmed/client.py`
- `app/modules/literature_search/query_model.py`
- `app/modules/literature_search/query_builder.py`
- `app/modules/literature_search/pubmed_executor.py`
- `app/modules/literature_search/model.py`
- `app/modules/literature_search/schema.py`
- `app/modules/literature_search/repository.py`
- `app/modules/literature_search/service.py`
- `app/modules/literature_search/router.py`
- `app/modules/literature_search/commercial_metrics.py`
- `app/core/models.py`
- `app/api/v1/__init__.py`
- `alembic/versions/a4b5c6d7e8f9_add_commercial_journal_metric_contract.py`
- 与上述模块有关的全部现有测试。

然后执行只读检查：

```powershell
git status --short
git branch --show-current
$env:PYTHONPATH = ""
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m alembic heads
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m alembic current
```

仓库当前可能存在大量用户未提交修改。它们全部属于用户：

- 不得重置、覆盖、清理或格式化无关文件。
- 不得使用 `git reset --hard`、`git checkout --` 或等价操作。
- 若目标文件已被修改，必须先阅读差异并在其基础上增量实现。
- 新迁移必须在执行时重新确认真实 Alembic head，禁止仅凭本提示词硬编码错误的 `down_revision`。
- 默认创建后续迁移，不得假定现有迁移从未在任何数据库执行。

先输出一份简短实施计划和“验收条件 → 测试文件”映射，然后再写测试和代码。不要向用户重复询问本提示词已经确定的产品选择。

## 3. 不可变产品决策

以下决策不得在实现中擅自改变：

### 3.1 论文范围

- “最近 15 年”是 PubMed 检索时间范围，不是本地镜像范围。
- 当前年份记为 `Y`，有效窗口为 `Y - 14` 到 `Y`，包含首尾年份。
- 未指定日期时使用完整 15 年窗口。
- 用户指定更窄范围时保留其范围。
- 用户范围部分超出窗口时，取交集并返回结构化 warning。
- 用户范围与窗口完全无交集时返回可识别的 422 领域错误。
- 最终执行层必须再次施加产品日期边界，不能只依靠解析器或前端。
- 保留现有单次最多 500 条限制。响应必须继续区分 PubMed `total_count` 与本地实际加载条数；不得声称所有命中均已加载。

### 3.2 指标范围

- 普通查询仅返回最近 10 个激活指标年度。
- 第 11 年及更早批次默认归档，不自动物理删除。
- 卡片摘要按字段返回“最新可用值 + 该字段自己的年份”。
- 详情接口返回最近 10 个年度快照。
- 若存在论文发表年度的精确指标则返回；否则明确返回 `null` 和原因，禁止用相邻年份冒充。
- JCR 字段名称必须为“最佳 Q 区”，后端字段使用 `jcr_best_quartile`。
- 期刊指标只能作为期刊参考信息，不得写入或改变论文相关性、证据等级、文章影响力评分及排序算法。

### 3.3 数据来源

- 不把真实 JCR、IF 或中科院数据加入仓库、fixture、种子数据或安装包。
- 只提供格式模板和明显虚构的 `Example Journal` 测试数据。
- 用户通过本地 CSV 导入自己有权使用的数据。
- 保存来源、版本、文件 SHA-256 和授权来源说明。
- 不记录CSV全文、论文摘要、密钥或敏感路径到日志。

### 3.4 快照兼容

- `LiteratureSearchResult.items_json` 继续作为不可变检索快照。
- 新字段加入 `CitationItem` 时必须有安全默认值，使旧JSON继续通过 Pydantic 校验。
- 不把期刊指标复制进 `items_json`。
- 指标在读取结果页时动态装配，因此年度更新后历史论文可看到新的指标。
- 不批量回写旧结果快照。

## 4. 推荐文件边界

保持现有项目分层，建议新增或调整以下文件；如果仓库已有等价职责，复用而不是创建平行实现：

```text
app/
├── integrations/pubmed/
│   ├── schemas.py                 # PubMedRecord 新增期刊标识
│   └── client.py                  # EFetch XML 解析
├── modules/literature_search/
│   ├── query_model.py             # 15 年窗口纯函数和常量
│   ├── schema.py                  # 论文与指标 API 契约
│   ├── model.py                   # 导入批次与年度指标 ORM
│   ├── journal_metric_normalization.py
│   ├── journal_metric_import.py   # CSV 解析、校验、预览
│   ├── journal_metric_matching.py # 纯匹配逻辑
│   ├── journal_metric_repository.py
│   ├── journal_metric_service.py
│   ├── journal_metric_router.py
│   ├── repository.py              # 仅必要的现有结果读取
│   ├── service.py                 # 分页响应动态装配
│   └── pubmed_executor.py         # 映射新增字段
├── core/models.py
└── api/v1/__init__.py

alembic/versions/<new_revision>_add_journal_metric_imports.py

tests/modules/literature_search/
├── test_pubmed_journal_identifiers.py
├── test_search_window_policy.py
├── test_journal_metric_normalization.py
├── test_journal_metric_import.py
├── test_journal_metric_matching.py
└── test_journal_metric_api.py
```

不要把所有逻辑继续堆进已经很大的 `service.py`。纯函数、导入流程、匹配和指标查询必须拆开。

现有 `commercial_metrics.py` 中的 `CommercialJournalMetric`、`CommercialMetricsProvider` 和未配置provider也必须同步扩展到最终字段与状态，不能留下只允许 `sci/scie`、单一 `quartile` 的旧协议。项目中只能保留一个有效的期刊指标领域契约。

## 5. PubMed 字段实现要求

### 5.1 Pydantic 契约

给 `PubMedRecord` 和 `CitationItem` 增加：

```python
issn: str | None = None
eissn: str | None = None
issn_l: str | None = None
journal_abbreviation: str | None = None
```

所有字段必须有长度限制。旧JSON缺少字段时必须正常加载。

### 5.2 XML解析

从 PubMed EFetch XML 的真实节点解析：

- `Article/Journal/ISSN`，根据 `IssnType` 区分 `Print` 与 `Electronic`。
- `MedlineJournalInfo/ISSNLinking` 作为 `issn_l`。
- `MedlineJournalInfo/MedlineTA` 作为期刊缩写。

要求：

- 支持命名空间无关解析，沿用当前客户端的本地标签辅助函数。
- 缺节点返回 `None`，不得抛出无意义异常。
- ISSN规范化后输出 `NNNN-NNNN`，校验位 `X` 大写。
- 无效ISSN保留为 `None`，不要把非法值用于匹配。
- 不因ISSN缺失影响论文其他字段解析。
- ESummary仍可只提供现有简要字段；最终可靠标识来自EFetch。

### 5.3 ISSN校验

实现无副作用纯函数：

```python
normalize_issn(value: str | None) -> str | None
is_valid_issn(value: str) -> bool
```

必须覆盖：连字符、无连字符、空格、小写 `x`、错误长度、非法字符、错误校验位和空值。

## 6. 最近15年检索策略

定义具名常量：

```python
DEFAULT_PUBLICATION_WINDOW_YEARS = 15
```

不要在多个文件散落数字15。

实现纯函数，允许注入当前年份以便确定性测试：

```python
publication_window(current_year: int) -> DateRange
constrain_date_range(requested: DateRange | None, current_year: int) -> ConstrainedDateRange
```

`ConstrainedDateRange` 至少包含：

```text
effective_range
was_defaulted
was_clipped
warnings
```

最终 `SearchExecuteRequest` 或任务创建契约必须携带结构化有效日期范围。即使用户手工编辑 `boolean_query`，执行服务仍需将产品时间过滤器作为额外AND条件加入最终PubMed查询。

要求：

- 不重复改变更窄的用户日期条件；额外15年边界与用户条件取交集即可。
- 持久化 `search_string` 必须是实际发送给PubMed的最终字符串。
- `strategy_fingerprint` 和 `history_fingerprint` 必须基于最终有效查询，避免不同时间边界错误复用同一任务。
- 重跑任务复用原任务保存的有效日期快照，不因跨年重跑静默改变历史策略；如果产品需要“按当前15年窗口重新搜索”，必须作为显式新任务，而不是重跑旧任务。

## 7. 数据库模型

### 7.1 导入批次

新增 `JournalMetricImportBatch`：

```text
id: int PK
edition_year: int NOT NULL
provider: varchar(100) NOT NULL
provider_version: varchar(100) NOT NULL
source_filename: varchar(255) NOT NULL
source_file_hash: varchar(64) NOT NULL
license_provenance: text NOT NULL
record_count: int NOT NULL default 0
status: varchar(30) NOT NULL
is_active: bool NOT NULL default false
error_summary: text nullable
created_at: datetime NOT NULL
activated_at: datetime nullable
```

约束：

- SHA-256必须为64位小写十六进制。
- `edition_year` 使用合理范围校验。
- `record_count >= 0`。
- 同一 `provider + edition_year + provider_version` 唯一。
- 同一来源同一年度同时只能有一个active批次；SQLite无法方便建立条件唯一约束时，必须在事务内查询、停用旧批次、激活新批次，并用测试覆盖。

### 7.2 年度指标

扩展现有 `LiteratureCommercialJournalMetric`，不要创建含义重复的第二张指标表。至少支持：

```text
import_batch_id FK
journal_key
journal_name
normalized_journal_name
issn
eissn
issn_l
metric_year
impact_factor
impact_factor_year
jcr_best_quartile
jcr_year
wos_indexes_json
wos_year
cas_quartile
cas_year
cas_category
is_cas_top
warning_status
provider
provider_version
license_provenance
status
reason
observed_at
created_at
```

约束：

- `impact_factor >= 0` 或 `NULL`。
- `jcr_best_quartile ∈ Q1,Q2,Q3,Q4` 或 `NULL`。
- 中科院分区为 `1区`—`4区` 或 `NULL`。
- WoS值只允许 `SCIE, SSCI, ESCI, AHCI`，Pydantic层严格校验并以JSON数组持久化。
- 一条记录至少包含一个有效期刊身份和一个指标字段。
- 每条记录的 `metric_year` 必须与所属导入批次的 `edition_year` 相同；不允许一个批次混入多个主年度。
- `import_batch_id + journal_key` 唯一。
- 对ISSN-L、ISSN、eISSN、标准化期刊名、指标年份和批次建立查询索引。

### 7.3 迁移

- 创建一个新的后续迁移，执行前重新读取真实head。
- 升级必须兼容已有表和已有行。
- 对现有列只做安全增量，不进行破坏性重建，除非SQLite约束确实要求且已写完整数据迁移测试。
- 新外键删除策略必须明确；归档批次不能级联删除指标。
- `downgrade` 必须可执行，并只撤销本次迁移内容。
- 在临时SQLite数据库真实验证 `upgrade head → downgrade到前一版本 → upgrade head`。

## 8. CSV导入

### 8.1 标准字段

支持UTF-8 CSV，第一版不新增Excel依赖。必需/可选字段：

```text
journal_name              必需
issn                      可选
eissn                     可选
issn_l                    可选
metric_year               必需
impact_factor             可选
impact_factor_year        可选
jcr_best_quartile         可选
jcr_year                  可选
wos_indexes               可选，使用逗号或分号分隔
wos_year                  可选
cas_quartile              可选
cas_year                  可选
cas_category              可选
is_cas_top                可选
warning_status            可选
```

不要为了XLSX引入新依赖。若未来需要XLSX，另开任务。

定义可配置但有安全默认值的文件上限，建议 `JOURNAL_METRIC_IMPORT_MAX_BYTES = 32 * 1024 * 1024`，并通过现有Settings和 `.env.example` 暴露。禁止在路由中散落魔法数字。

### 8.2 两阶段导入

预览阶段：

- 接收 `UploadFile`，限制文件扩展名、MIME提示和最大字节数；不要信任客户端文件名。
- 流式读取并计算SHA-256，禁止无界读入内存。
- UTF-8 BOM可接受，无法解码时返回可识别错误。
- 解析表头、规范化值并逐行校验。
- 返回总行数、有效行数、错误行数、重复数、错误样例和文件SHA-256。
- 预览不得写入正式指标表。
- 任意数据行无效都使批次不可提交；预览可以收集有限数量的错误样例，但不得静默丢弃错误行后导入其余行。

提交阶段：

- 客户端重新上传同一CSV，并提交预览阶段获得的 `expected_file_hash`、provider、provider_version、edition_year和license_provenance。
- 服务端重新计算哈希、重新解析全部行并验证元数据；哈希不一致返回稳定错误。
- 单个数据库事务写入批次和全部有效指标。
- 任意无效行或数据库错误整体回滚，不允许部分导入。
- 不持久化客户端文件路径，不创建需要跨请求维护的临时预览文件，也不接受服务器路径参数。

### 8.3 错误模型

定义稳定错误码并使用项目现有异常映射，不在路由里散落字符串：

```text
journal_metric_file_too_large
journal_metric_invalid_encoding
journal_metric_missing_headers
journal_metric_invalid_rows
journal_metric_duplicate_import
journal_metric_preview_mismatch
journal_metric_batch_not_found
journal_metric_batch_not_ready
journal_metric_year_out_of_range
literature_search_range_outside_policy
```

## 9. 匹配服务

匹配必须是确定性的，不访问外部网络。

优先级：

```text
1. issn_l_exact
2. issn_exact
3. eissn_exact
4. normalized_title_exact
5. none
```

规则：

- 论文的任一有效ISSN可与指标行的 `issn_l/issn/eissn` 交叉精确匹配，但匹配方法要反映论文侧使用的字段。
- 同一最高优先级命中多个不同 `journal_key` 时返回 `ambiguous`，不得随意选择第一条。
- 期刊名称只进行规范化后的完全相等，不进行自动模糊匹配。
- 所有匹配仅查询激活批次。
- 一次结果页最多100条，必须批量查询，不得每篇论文执行一次数据库查询。
- 先收集页面内所有ISSN和标准化名称，一次或少量SQL取回候选，然后在内存中用纯函数完成匹配。
- 不因指标查询失败而使PubMed结果页整体失败；可恢复错误返回 `unavailable` 并记录不含敏感数据的warning。

## 10. 指标选择与十年历史

定义：

- `latest`：每个指标字段各自从激活批次中选择年份最大的非空值。
- `publication_year`：仅选择与论文发表年份完全相同的指标快照。
- `history`：按 `metric_year DESC` 返回最多10个年度。

必须分别返回年份，不能用一个年份覆盖所有字段：

```json
{
  "status": "matched",
  "match_method": "issn_exact",
  "latest": {
    "impact_factor": {"value": 8.6, "year": 2025},
    "jcr": {"best_quartile": "Q1", "year": 2025},
    "wos": {"indexes": ["SCIE"], "year": 2025},
    "cas": {"quartile": "1区", "year": 2024}
  }
}
```

缺值使用 `null`，禁止使用0、空字符串、推测值或相邻年份。

## 11. API契约

### 11.1 结果分页

扩展 `RankedCitationItem`：

```python
journal_metric: JournalMetricSummary | None = None
```

没有导入任何激活批次时也返回结构化状态：

```json
{
  "status": "not_configured",
  "match_method": null,
  "latest": null,
  "reason": "no_active_journal_metric_import"
}
```

列表响应只返回摘要，不返回十年历史。

### 11.2 单篇十年详情

```http
GET /api/v1/literature-search/{result_id}/items/{pmid}/journal-metrics
```

行为：

- 验证结果存在。
- 验证PMID属于该不可变结果快照。
- 动态匹配该论文期刊。
- 返回最新摘要、精确发表年度指标和最近10年历史。
- 结果或PMID不存在时使用现有404领域异常。

### 11.3 导入管理

新增独立路由前缀：

```http
GET  /api/v1/journal-metrics/imports
POST /api/v1/journal-metrics/imports/preview
POST /api/v1/journal-metrics/imports/commit
POST /api/v1/journal-metrics/imports/{id}/activate
POST /api/v1/journal-metrics/imports/{id}/archive
```

所有路由必须有Pydantic响应模型、类型注解、分页边界和明确状态码。

激活批次必须在事务中：

1. 验证目标为 `ready` 或当前 `active`。
2. 停用同provider同年度的旧active批次。
3. 激活目标批次。
4. 提交后普通查询立即使用新版本。

归档当前active批次后，该年度可以没有active版本；不得暗中激活其他版本。

## 12. 性能要求

- SQLite保存约25万条十年指标应正常工作。
- 结果页指标装配不得出现N+1查询。
- 读取20条和100条结果页时，指标查询次数应为常数级并由测试验证仓储方法只调用一次批量接口。
- CSV导入使用批量插入，避免逐行commit。
- 列表接口不序列化十年历史。
- 不新增Redis等非必要依赖。

## 13. 验收条件与测试硬门禁

先写以下验收测试并确认在实现前失败。每个AC至少对应一个测试，不得删除或弱化测试来适配实现。

### AC-01 默认15年

Given 请求未提供日期范围；When 执行检索；Then 实际PubMed查询包含当前年份及之前14年的边界。

### AC-02 更窄范围

Given 用户请求最近5年；When 执行检索；Then 最终范围保持5年且不被扩展为15年。

### AC-03 超界裁剪

Given 用户范围部分早于15年窗口；When 构建执行请求；Then 使用交集并返回裁剪warning。

### AC-04 完全超界

Given 用户范围完全早于15年窗口；When 执行；Then 返回422稳定错误码且不调用PubMed。

### AC-05 重跑可复现

Given 去年创建的检索任务；When 今年重跑；Then 使用原任务保存的有效年份，不静默滚动一年。

### AC-06 ISSN解析

Given 含Print ISSN、Electronic ISSN、ISSNLinking和MedlineTA的EFetch XML；When 解析；Then 四个标准化字段准确返回。

### AC-07 缺失ISSN兼容

Given 不含ISSN节点的真实形态XML；When 解析；Then 论文其他字段正常且ISSN字段为null。

### AC-08 无效ISSN

Given 错误校验位或非法字符；When 规范化；Then 返回null且不参与匹配。

### AC-09 旧快照兼容

Given 不含新增字段的旧 `items_json`；When 获取结果、导出BibTeX和执行现有筛选；Then 行为保持正常。

### AC-10 CSV预览只读

Given 合法CSV；When 预览；Then 返回统计和令牌，正式指标表无新增记录。

### AC-11 CSV阻断错误

Given 缺少表头、非法编码或全部记录无效；When 预览；Then 返回稳定错误且不写库。

### AC-12 CSV提交原子性

Given 提交过程中有阻断错误；When 提交；Then 批次和指标均不留部分数据。

### AC-12A CSV哈希一致性

Given提交文件与预览文件内容不同；When提交；Then返回`journal_metric_preview_mismatch`且不写库。

### AC-13 重复文件

Given 相同SHA-256文件已成功导入；When 再次导入；Then 返回重复导入错误。

### AC-14 激活切换

Given 同来源同年度两个ready版本；When 激活新版；Then 旧版停用且查询只使用新版。

### AC-15 匹配优先级

Given ISSN命中A而期刊名称命中B；When 匹配；Then 选择ISSN对应A。

### AC-16 歧义保护

Given 同一最高优先级命中不同期刊键；When 匹配；Then 返回ambiguous且不展示任一指标。

### AC-17 旧论文名称匹配

Given 旧快照没有ISSN但规范化期刊名唯一命中；When 查询；Then 返回matched和`normalized_title_exact`。

### AC-18 不自动模糊匹配

Given 只有相似但不完全相等的期刊名；When 匹配；Then 返回not_found。

### AC-19 独立年份

Given最新IF为2025、中科院为2024；When读取摘要；Then分别返回2025和2024，不能合并成同一年。

### AC-20 发表年度精确性

Given论文发表于2014且本地只有2016—2025；When查询详情；Then发表年度指标为null并返回`publication_year_metric_not_available`。

### AC-21 十年限制

Given存在12个激活年度；When查询详情；Then只返回年份最新的10条并按降序排列。

### AC-22 空值诚实性

Given期刊只有Q区没有IF；When返回API；ThenIF为null而不是0。

### AC-23 ESCI真实性

Given指标为ESCI且有IF；When返回API；Then仍为ESCI，不推断为SCIE。

### AC-24 未配置状态

Given没有激活导入批次；When获取论文结果页；ThenPubMed结果正常返回且指标状态为not_configured。

### AC-25 不影响评分

Given导入指标前后同一评分生成结果；When获取评分和排序；Then现有论文评分字段和值不因期刊指标改变。

### AC-26 无N+1

Given一页100篇论文；When装配指标；Then使用批量候选查询，不执行每篇一次指标SQL。

### AC-27 详情身份边界

GivenPMID不属于指定result；When请求详情；Then返回404，不允许跨结果读取。

### AC-28 归档行为

Given一个active批次；When归档；Then普通指标查询不再使用该批次且不会自动启用旧版。

### AC-29 十年滚动

Given11个年度批次；When激活最新年度并执行保留策略；Then最旧年度归档、最近10年保持active/可查询，数据不物理删除。

### AC-30 全量回归

Given所有新增功能完成；When运行现有文献检索、BibTeX、去重、评分、收藏和PubMed客户端测试；Then全部通过。

建立追踪表：

```text
AC编号 → 测试函数 → 测试文件 → 最终PASS/FAIL
```

## 14. 实施阶段与停止条件

### 阶段A：测试和契约

- 写AC对应测试。
- 扩展Pydantic响应模型。
- 确认测试因功能缺失而失败，而不是测试自身错误。

停止条件：所有AC已有测试映射，RED状态已确认。

### 阶段B：PubMed和15年策略

- 实现日期边界纯函数。
- 实现执行层强制边界。
- 解析ISSN/eISSN/ISSN-L/缩写。
- 保持旧快照兼容。

停止条件：AC-01至AC-09通过，相关现有测试通过。

### 阶段C：数据库与导入

- 新迁移。
- ORM和schemas。
- CSV预览、提交、批次激活归档。

停止条件：迁移往返通过，AC-10至AC-14、AC-28、AC-29通过。

### 阶段D：匹配与API装配

- 批量匹配。
- 最新摘要。
- 十年详情。
- 未配置和错误降级。

停止条件：AC-15至AC-27通过。

### 阶段E：全量验证

- 运行所有后端测试和静态检查。
- 输出验收追踪报告。
- 不修改前端。

## 15. 必须真实运行的命令

在PowerShell中：

```powershell
Set-Location D:\AI_project\rag_medicine
$env:PYTHONPATH = ""
$python = "F:\software\programme\Anaconda\envs\med-research-ai\python.exe"

& $python -m pytest tests\modules\literature_search tests\unit\test_pubmed_client.py -q
& $python -m pytest -q
& $python -m ruff check app tests alembic
& $python -m mypy app\cli app\integrations app\modules\literature_search
& $python -m alembic check
& $python -m alembic heads
```

迁移往返必须在临时SQLite数据库或仓库既有迁移验证机制中完成，禁止对用户正式 `data/app.db` 执行破坏性downgrade。

如果仓库环境中 `ruff` 或 `mypy` 的调用方式不同，以 `pyproject.toml` 和当前已安装环境为准，但必须真实执行等价命令。

本任务不修改前端，因此不要求本轮修复前端问题；但若API类型契约影响全仓库构建，可运行前端只读验证并如实报告，不得顺带改前端。

## 16. 完成声明格式

最终只在所有硬门禁通过后输出：

1. 实现结果摘要。
2. 实际修改文件清单。
3. 数据库迁移说明。
4. API端点和请求示例。
5. 31项AC追踪表及PASS状态。
6. 每条真实验证命令及结果。
7. 已知限制。
8. 明确说明没有修改前端。

如果任何测试或检查失败：

- 不得声称完成；
- 给出失败命令、关键错误、已完成范围和剩余工作；
- 继续修复属于本任务引入的问题；
- 不通过删除测试、降低断言、跳过测试或改变产品规格来制造通过。

## 17. 明确非目标

本轮不要实现：

- 前端卡片、详情弹窗或数据管理页面；
- XLSX导入；
- Clarivate在线API；
- 自动下载或打包真实JCR数据；
- 模糊期刊名称自动匹配；
- 完整JCR多学科排名；
- 期刊指标参与文章评分或排序；
- PubMed超过500条的增量远程分页；
- 云端同步期刊指标；
- 自动删除十年前的数据库记录。

如发现这些能力对未来有价值，只记录为后续建议，不得扩大本次实现范围。
