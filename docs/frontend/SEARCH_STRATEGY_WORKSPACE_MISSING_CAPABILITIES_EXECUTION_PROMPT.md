# 素问·检索中心最终策略工作台——缺失能力补齐执行提示词

> **范围修订（2026-08-23，最高优先级）**：用户已明确取消本轮前端设计。禁止进行像素复刻、CSS/布局/视觉密度迭代、Hero 装饰重做及 overlay/diff 优化。本提示词中涉及页面视觉设计的内容不再执行；仅允许为真实 API 接入、状态展示、业务流程、可访问性和基本可用性所必需的最小前端功能修改。重点为后端真实能力、数据持久化、契约、迁移和功能验收。

## 1. 执行目标

在现有仓库 `D:\AI_project\rag_medicine` 内增量补齐“检索中心最终版策略工作台”当前无法真实实现的能力，并完成后端、前端、迁移、自动化测试和浏览器验收的完整业务闭环。

本任务不是视觉 Demo，不允许把本地状态、历史结果、测试 fixture 或硬编码数字包装成真实业务能力。最终必须实现：

1. 持久化检索策略草稿与可靠自动保存；
2. 独立于检索结果快照的策略版本管理；
3. 可解释、可追踪的策略版本比较；
4. 可编辑并持久化的检索术语与锁定状态；
5. 完整的 NLM MeSH 验证与部分失败状态；
6. 独立的 PubMed Query 验证；
7. 基于当前策略的真实 PubMed Count；
8. 修改上游内容后的依赖失效、重新生成和 dirty 状态；
9. 入口页 → 策略工作台 → 真实检索 → 结果页的连续链路。

## 2. 工作区与安全边界

- 开始前执行 `Set-Location -LiteralPath 'D:\AI_project\rag_medicine'`，确认 `git rev-parse --show-toplevel`。
- 完整阅读根目录 `AGENTS.md`、`docs/CODE_STANDARDS.md`、当前提示词及相关设计文档。
- 当前工作树可能已有用户修改。不得覆盖、回滚、格式化或删除无关改动。
- 禁止 `git reset --hard`、`git checkout --`、`git clean`、删除数据库、重建仓库。
- 只允许修改项目应用代码、项目测试、项目文档和必要 Alembic 迁移；不得修改注册表、系统环境变量、服务、权限、防火墙或其他系统配置。
- 不得访问或修改旧的 `H:` 仓库。
- 不执行破坏性数据库升级。可以生成迁移并在隔离测试数据库验证；是否升级用户本地 `data/app.db` 必须保持可控并如实报告。
- 不引入第二套 API Client、Router、状态框架、UI 框架或图标库。

## 3. 必须先阅读的现有实现

至少完整检查：

```text
frontend/src/router/index.ts
frontend/src/api/literatureSearch.ts
frontend/src/types/searchEntry.ts
frontend/src/composables/useQueryIntent.ts
frontend/src/composables/useSearchTerms.ts
frontend/src/composables/useSearchStrategyCreator.ts
frontend/src/views/LiteratureSearch/
frontend/src/components/search-entry/

app/modules/literature_search/model.py
app/modules/literature_search/schema.py
app/modules/literature_search/repository.py
app/modules/literature_search/service.py
app/modules/literature_search/router.py
app/modules/literature_search/query_model.py
app/modules/literature_search/query_builder.py
app/modules/literature_search/mesh_client.py
app/modules/literature_search/pubmed_executor.py
app/integrations/pubmed/

tests/modules/literature_search/
alembic/ 或项目实际迁移目录
```

先输出并保存一份契约盘点，明确现有结构能否复用。不得在未确认字段和调用关系时假设接口。

## 4. 不可混淆的领域概念

必须将以下对象明确分离：

### 4.1 Working Strategy Draft

用户正在编辑的可变策略。包含研究问题、结构化意图、术语、MeSH、Query、限制条件、验证状态、Count 状态和保存状态。

### 4.2 Immutable Strategy Version

用户主动创建的不可变策略快照。版本号属于策略本身，不是检索次数。

### 4.3 Search Execution Task

一次真实 PubMed 检索执行。它引用一个确定的策略版本或受控草稿快照。

### 4.4 Search Result Snapshot

一次执行产生的结果快照。现有 `LiteratureSearchTaskVersion` 如果表示重跑结果版本，必须保留其真实语义，不得冒充 Strategy Version。

### 4.5 Fingerprint

后端基于规范化策略生成，用于 dirty 判断、缓存 Count、执行复用与审计。前端不得另算一套权威 fingerprint。

## 5. 推荐后端分层

根据现有目录命名调整，但必须保持单一职责。建议新增或拆分为：

```text
app/modules/literature_search/
├── strategy_model.py             # 草稿、不可变版本、术语状态等持久化模型
├── strategy_schema.py            # 策略 API 的请求/响应契约
├── strategy_repository.py        # 仅数据访问
├── strategy_service.py           # 草稿、版本、失效传播与并发规则
├── strategy_fingerprint.py       # 规范化与 fingerprint 纯函数
├── strategy_diff.py              # 版本差异纯函数
├── strategy_validation.py        # Query/MeSH/阻塞项聚合
├── strategy_count.py             # PubMed count 协调、缓存与过期保护
└── strategy_router.py            # HTTP 边界
```

如果现有文件更合适，可增量扩展，但禁止把所有逻辑继续堆入一个 service/router/model 文件。

依赖方向必须为：`router → service → repository/integration`。业务层不得导入路由层。

## 6. 持久化数据模型最低要求

字段名以现有项目惯例为准，但能力必须完整：

### 6.1 SearchStrategyDraft

- `id`
- `owner/user scope`：若当前项目没有认证，遵循现有单用户本地模式，不伪造 user_id
- `research_question`
- `intent_mode`：PICO、PECO、非结构化等真实支持模式
- `intent_json`
- `limits_json`
- `query_text`
- `query_source`：generated/user_edited
- `fingerprint`
- `revision`：乐观并发控制
- `generation_state`
- `validation_state`
- `count_state`
- `created_at`
- `updated_at`
- `last_saved_at`

### 6.2 SearchStrategyTerm

- 稳定 `id`
- `strategy_id`
- `concept_group`
- `text`
- `normalized_text`
- `source`：research_question / smart_expansion / user_added
- `field_tag`
- `relation_type`（如果真实可得）
- `is_locked`
- `position`
- `warning_code` 与可解释详情
- `created_at/updated_at`

### 6.3 SearchStrategyMeshTerm

- 稳定 `id`
- `strategy_id`
- `descriptor`
- `mesh_id`
- `concept_group`
- `source=nlm_mesh` 只能由后端官方查询结果赋予
- `verification_status`：verified / not_found / unavailable / stale
- `is_locked`
- `verification_checked_at`
- 必要的可解释元数据

### 6.4 SearchStrategyVersion

- `id`
- `strategy_id`
- 单策略内单调递增 `version`
- 不可变 `snapshot_json`
- `fingerprint`
- `created_at`
- 可选的用户说明

需要数据库唯一约束保证 `(strategy_id, version)` 唯一；需要外键和删除语义；迁移必须支持已有数据，不得重写历史迁移。

## 7. API 契约最低要求

路径遵循现有 `/api/v1/literature-search` 体系，可合理命名，但至少覆盖：

```text
POST   /literature-search/strategies
GET    /literature-search/strategies/{strategy_id}
PATCH  /literature-search/strategies/{strategy_id}

POST   /literature-search/strategies/{strategy_id}/regenerate
POST   /literature-search/strategies/{strategy_id}/terms
PATCH  /literature-search/strategies/{strategy_id}/terms/{term_id}
DELETE /literature-search/strategies/{strategy_id}/terms/{term_id}
POST   /literature-search/strategies/{strategy_id}/terms/remap

POST   /literature-search/strategies/{strategy_id}/mesh/refresh
PATCH  /literature-search/strategies/{strategy_id}/mesh/{mesh_term_id}

POST   /literature-search/strategies/{strategy_id}/validate
POST   /literature-search/strategies/{strategy_id}/count

POST   /literature-search/strategies/{strategy_id}/versions
GET    /literature-search/strategies/{strategy_id}/versions
GET    /literature-search/strategies/{strategy_id}/versions/{version}
GET    /literature-search/strategies/{strategy_id}/compare?from_version=x&to_version=y

POST   /literature-search/strategies/{strategy_id}/execute
```

### 7.1 并发控制

`PATCH` 必须携带期望 revision（请求体或 If-Match，遵循项目惯例）。过期修改返回明确的 409，不允许后写静默覆盖先写。

### 7.2 幂等与防重复

- 创建版本不能因重复点击产生两个相同版本。
- execute 复用现有任务幂等/fingerprint 规则。
- count 和 validate 结果必须绑定请求 fingerprint；旧响应不得覆盖新策略。

### 7.3 错误语义

至少区分：400 业务无效、404 不存在、409 revision 冲突、422 请求结构错误、502/503 外部 PubMed/NLM 暂时不可用。

## 8. 自动保存真实行为

- 前端编辑研究问题、意图、术语、限制条件和 Query 后，使用 500–1000ms debounce 自动保存。
- 页面明确展示：未保存、正在保存、已保存、保存失败、冲突。
- “已保存”和 `last_saved_at` 必须来自成功后端响应。
- 保存失败保留用户本地编辑，提供重试，不能回滚成假成功。
- revision 冲突必须提示刷新或比较，不允许静默覆盖。
- 刷新页面后从后端恢复完整草稿；localStorage 只能作为恢复辅助，不能作为权威保存状态。
- 多次快速编辑只提交必要的最新状态，并避免过期响应覆盖。

## 9. 上游修改与失效传播

建立明确状态机：

- 修改研究问题：Intent、Terms、MeSH、Query、Validation、Count 标记 stale；必须经用户确认后重新生成。
- 修改 Intent：Terms、MeSH、Query、Validation、Count 标记 stale。
- 修改术语或 MeSH：Query、Validation、Count 标记 stale。
- 修改 Query 或 Limits：Validation、Count 标记 stale。
- 被锁定术语在重新映射时按真实业务规则保留。
- 旧 Count 只能显示为“已过期”，不得继续冒充当前策略匹配数。
- 只有 blocking validation 为零且 Count/Query 对应当前 fingerprint 时，才进入 Ready。

状态转换应由后端领域服务负责，前端只展示后端权威结果。

## 10. 术语与锁定能力

- 支持增加、删除、锁定、解锁和重新映射。
- 每项操作持久化并返回新 revision/fingerprint。
- 锁定状态不能只用颜色表达，必须有图标、文本或 aria-pressed。
- 重新映射不得删除锁定术语。
- 术语来源必须真实区分：研究问题、智能扩展、用户添加。
- Warning 必须使用结构化 code/message/severity，不只返回不可解析字符串。
- 如果后端无法证明概念关系，前端不显示伪造关系。

## 11. NLM MeSH 能力

- 复用现有 NLM MeSH client，不新增伪造词表。
- 官方请求结果必须记录 mesh_id、descriptor、验证时间和状态。
- NLM 故障只让 MeSH 区块进入 unavailable/error，不能使整个策略消失。
- 未找到是合法空结果，与外部服务失败分开。
- refresh 后结果绑定当前 strategy revision/fingerprint；过期响应丢弃。
- 只有真实官方确认的条目才能显示“NLM MeSH 已验证”。

## 12. Query Validation

建立独立验证响应，至少包含：

- `is_syntax_valid`
- `is_mesh_valid`
- `are_field_tags_valid`
- `warnings[]`
- `blocking_errors[]`
- `validated_fingerprint`
- `validated_at`

验证必须覆盖括号、布尔运算符、字段标签和已知 MeSH 引用。能本地确定的规则使用纯函数；需要外部确认的部分清楚标记 unavailable，不能伪装通过。

用户手动编辑 Query 后立即将旧验证状态标记 stale，重新验证成功后才恢复 Ready。

## 13. 真实 PubMed Count

- 必须调用 PubMed 的真实 count/ESearch 能力或复用项目已有等价集成。
- 请求使用当前 query + limits。
- 响应至少包含 `count`、`fingerprint`、`retrieved_at`、`source=pubmed`。
- 不允许调用生成式模型估算数量。
- 支持 loading、success、error、stale。
- 相同 fingerprint 可短期缓存；TTL 抽取为配置常量。
- 修改策略后旧 Count 立即进入 stale。
- 测试不得访问真实外网，使用受控 transport/test double；浏览器联调可以使用真实本地后端，但必须如实区分外部网络是否成功。

## 14. 策略版本与比较

- “创建新版本”把当前已保存草稿生成不可变快照。
- 版本号必须由数据库事务安全地产生。
- 相同 revision/fingerprint 的重复请求不得意外生成重复版本。
- 比较结果必须是结构化差异：question、intent、terms added/removed/changed、mesh、query、limits。
- 前端版本下拉只展示真实版本。
- “版本对比”在版本少于 2 个时诚实禁用并说明原因。
- 不得修改历史版本；基于旧版本继续工作必须生成新的 working draft/revision。

## 15. 执行检索

- execute 必须验证策略存在、已保存、无 blocking errors，且服务端重新确认 fingerprint。
- 执行请求引用 strategy_id 和可选 strategy_version_id，后端生成审计快照。
- 继续复用现有 LiteratureSearchTask、PubMed executor、结果和历史能力，禁止造第二套检索任务体系。
- 防重复点击；真实成功后路由到 `/literature-search/results/:id`。
- 失败时留在工作台并展示可恢复错误。

## 16. 前端架构与页面要求

保留：

```text
/literature-search           检索入口页
/literature-search/workspace 策略工作台
```

入口成功后应携带真实 `strategy_id` 进入 workspace，例如 query 参数或命名路由参数，方式必须与现有 Router 规范一致。

建议新增：

```text
frontend/src/
├── api/searchStrategies.ts
├── types/searchStrategy.ts
├── composables/
│   ├── useSearchStrategy.ts
│   ├── useStrategyAutosave.ts
│   ├── useStrategyValidation.ts
│   └── useStrategyCount.ts
└── components/literature-search/
    ├── SearchStrategyHero.vue
    ├── SearchJourneyProgress.vue
    ├── StrategyStepper.vue
    ├── ResearchQuestionSection.vue
    ├── SearchIntentSection.vue
    ├── SearchTermsSection.vue
    ├── PubMedQuerySection.vue
    ├── SearchLimitsSection.vue
    ├── StrategyReadyState.vue
    ├── StrategyStickyBar.vue
    └── dialogs/
```

实际边界须结合已有组件，复用 `SearchEntryView`、`QueryBuilder`、`TermEvidencePanel` 等能安全复用的逻辑。Route View 必须保持组合层，不得形成单体组件。

页面最终结构遵循用户文档和参考图：Hero、四阶段旅程、轻量 Stepper、研究问题、检索意图、术语与 MeSH、Query、Limits、Ready、Sticky Bar；不得新增右侧 Dashboard。

## 17. Loading / Empty / Error / Accessibility

- Strategy、Terms、MeSH、Validation、Count 分区独立状态。
- MeSH/Count 外部错误不导致整页崩溃。
- Empty Terms、Empty MeSH、未创建版本都有真实可操作空状态。
- 所有交互使用真实 button/input/dialog 语义。
- Dialog 支持焦点圈定、Escape、关闭后焦点恢复。
- icon button 有 aria-label；toggle 使用 aria-pressed；状态不只依靠颜色。
- Stepper 支持键盘，并随 IntersectionObserver 更新；尊重 prefers-reduced-motion。
- Sticky Bar 不覆盖正文和 Sidebar；1024px 与移动端不横向溢出。

## 18. 必须建立的验收标准

### 数据与持久化

- AC-STRAT-01：入口生成后创建真实策略草稿，并携带 strategy_id 进入 workspace。
- AC-STRAT-02：刷新 workspace 后从后端恢复相同草稿。
- AC-STRAT-03：编辑触发 debounce 自动保存，UI 状态与真实响应一致。
- AC-STRAT-04：保存失败保留输入并可重试，不显示假“已保存”。
- AC-STRAT-05：过期 revision 返回 409，前端不得静默覆盖。

### 失效传播

- AC-STRAT-06：修改问题使全部下游状态 stale。
- AC-STRAT-07：修改术语使 Query、Validation、Count stale。
- AC-STRAT-08：旧异步响应无法覆盖新 fingerprint 状态。

### 术语与 MeSH

- AC-STRAT-09：新增、删除、锁定和解锁术语真实持久化。
- AC-STRAT-10：重新映射保留锁定术语。
- AC-STRAT-11：来源和 Warning 使用结构化真实数据。
- AC-STRAT-12：NLM verified 只出现在官方验证成功后。
- AC-STRAT-13：MeSH not_found 与 unavailable 正确区分。
- AC-STRAT-14：MeSH 失败不阻断其他策略区域。

### Query 与 Count

- AC-STRAT-15：Query 验证返回语法、MeSH、字段和阻塞错误。
- AC-STRAT-16：用户编辑 Query 后旧验证立即 stale。
- AC-STRAT-17：Count 来自当前 query+limits 的真实 PubMed 请求。
- AC-STRAT-18：Count 请求失败时不显示伪造数量。
- AC-STRAT-19：Count 响应 fingerprint 不匹配时被丢弃。

### 版本与执行

- AC-STRAT-20：策略版本与检索结果版本在模型和 UI 中语义分离。
- AC-STRAT-21：创建新版本产生不可变、单调递增快照。
- AC-STRAT-22：重复请求不会意外生成重复版本。
- AC-STRAT-23：版本比较真实返回各领域差异。
- AC-STRAT-24：不足两个版本时版本比较诚实禁用。
- AC-STRAT-25：存在 blocking error 时后端拒绝执行。
- AC-STRAT-26：成功执行引用策略快照并进入真实结果页。
- AC-STRAT-27：重复点击只产生一次有效执行。

### 页面、恢复与无障碍

- AC-STRAT-28：Hero/Stepper/主要 Section/Sticky Bar 均展示真实状态。
- AC-STRAT-29：Stepper 点击和滚动观察正确同步。
- AC-STRAT-30：键盘、焦点、Dialog、aria 状态通过专项测试。
- AC-STRAT-31：1440、1280、1024、768、390 视口不横向溢出且 Sticky Bar 不遮挡。
- AC-STRAT-32：入口→工作台→执行→结果以及刷新、前进、后退形成连续流程。

每条 AC 必须映射至少一个自动化测试或明确的浏览器验收证据。没有覆盖的 AC 不得标完成。

## 19. 测试与验证顺序

### 19.1 迁移和后端

1. 为模型、fingerprint、diff、失效规则写单元测试，先确认 RED 再实现 GREEN。
2. 为每个策略 API 写接口测试，覆盖成功、404、409、422、外部服务错误。
3. 使用隔离测试数据库验证 Alembic upgrade/downgrade/upgrade 或仓库既有等价流程。
4. 执行仓库真实后端命令：pytest、ruff、mypy。Windows/PYTHONPATH 必须遵守 `AGENTS.md`。

### 19.2 前端

1. API 契约测试。
2. composable 的防抖、竞态、失败、冲突测试。
3. 组件状态和可访问性测试。
4. 入口到结果的路由/流程测试。
5. 执行真实 `package.json` 中对应的 test、typecheck、lint/ESLint、build。

### 19.3 浏览器验收

- 实际启动本地后端和前端。
- 使用可重复的浏览器脚本。
- 验证至少 1440×900、1280×800、1024×768、768×1024、390×844。
- 保存截图、console error、pageerror、requestfailed 结果。
- 使用测试数据库/受控外部适配器验证完整成功链路，不污染用户真实数据。
- 如果真实 PubMed/NLM 网络未测试，明确标【未实测】，不得用 mock 结果声称真实外网通过。

## 20. 完成门禁

只有同时满足以下条件才可宣称完成：

1. AC-STRAT-01 至 AC-STRAT-32 全部有追踪映射；
2. 所有可自动化 AC 均有通过测试；
3. 后端 pytest、ruff、mypy 真实执行并通过，或明确报告与本次无关的既有失败证据；
4. Alembic 在隔离数据库验证通过；
5. 前端全量 test、typecheck、相关 ESLint、build 通过；
6. 浏览器五视口和关键完整流程完成；
7. 没有假保存、假版本、假 MeSH、假 Count、假验证或假结果；
8. 没有未说明的 TODO/mock/console.log/@ts-ignore/any；
9. 当前工作树中的用户改动完整保留。

如遇普通代码、测试、迁移或浏览器问题，应自行定位并继续修复，不要在首轮实现或部分测试通过后停止。只有确实需要用户作不可推断的产品决定，或连续三轮遇到同一外部阻塞时，才可停止并明确给出证据。

## 21. 最终交付报告

最终必须包含：

- 完整修改目录树；
- 数据模型和迁移说明；
- API 契约清单及请求/响应示例；
- 前端组件和数据流说明；
- AC-STRAT-01 至 AC-STRAT-32 追踪表；
- 实际运行的每条命令和真实结果；
- 浏览器截图绝对路径；
- 未执行项统一标记【未实测】；
- 既有问题与本次引入问题分开说明；
- 性能、并发、外部 API、医学真实性和安全风险。

严禁使用“应该通过”“理论上完成”“基本完成”代替验证结果。
