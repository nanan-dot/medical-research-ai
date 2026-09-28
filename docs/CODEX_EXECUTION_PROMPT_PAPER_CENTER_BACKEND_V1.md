# Codex 执行提示词：论文中心 V1 后端完整化

## 一、任务目标

在本机仓库 `D:\AI_project\rag_medicine` 中，直接补全“论文中心”进度展览台所需的后端能力。

前端冻结参考：

- `C:\Users\ADMIN\Desktop\rag医学检索\预览图设计继续\论文中心-V2-研究进度展览台.png`

论文中心不是论文库、数据驾驶舱或 AI 聊天页。它只回答：

1. 当前在研究什么；
2. 论文研究进行到哪里；
3. 用户下一步应该继续做什么。

最终后端必须一次有界聚合返回：当前研究、继续研究任务、近期研究动态、最近研究论文和统一进度统计，并提供稳定的当前研究选择与阶段更新能力。下一步建议必须由可解释、可测试的确定性规则生成，不调用大模型。

## 二、执行技能与顺序

必须完整读取并遵循：

1. `fastapi-python`：FastAPI、Pydantic v2、异步 SQLAlchemy 契约和错误边界；
2. `python-design-patterns`：KISS、职责分离、浅层组合，避免把聚合逻辑塞入现有大 service；
3. `acceptance-testing`：先规格、再行为测试、确认 RED，最后实现至 GREEN；
4. 若涉及 PostgreSQL 方言或迁移设计，再使用 `postgresql-database-engineering`，但不得将 SQLite 特有行为写入领域逻辑。

同时完整读取仓库所有适用 `AGENTS.md`、`docs/CODE_STANDARDS.md`、现有 paper_research、paper_library、document_reader、paper_analysis、research_context、migration 和测试代码。以当前代码为准，禁止根据本提示词猜测已有契约。

## 三、安全与范围边界

1. 范围仅限论文中心后端聚合、必要的数据模型/迁移、契约、测试和后端文档。
2. 不修改前端，不修改其他页面，不重构无关模块。
3. 正式数据库 `data/app.db` 不得 upgrade、downgrade、写入或用于测试。所有迁移验证使用临时数据库。
4. 工作区有大量用户和其他任务的未提交修改。禁止 `reset`、`checkout`、`clean`、删除目录或覆盖无关内容；修改文件前重读最新版本，发现外部修改后重新读取并最小合并。
5. 使用 `apply_patch` 编辑文件。不得修改或弱化既有测试来迁就实现。
6. 不抓取外部数据，不伪造论文、DOI、PMID、页码、统计或商业指标。
7. 不引入 Redis、消息队列、大模型或新的基础设施。当前功能应以现有数据库和有界查询完成。
8. 保持当前 local actor scope 部署边界；新增用户偏好必须按现有 actor scope 隔离，不能宣称生产级多用户认证。

## 四、推荐架构边界

优先在 `app/modules/paper_research` 内增加轻量论文中心聚合能力，复用其他模块的源数据，不复制论文、阅读或分析事实。

建议职责：

- `center_schema.py`：稳定 HTTP DTO 与枚举；
- `center_repository.py`：有界批量查询，只返回领域投影所需记录；
- `next_action.py`：纯函数规则，生成可解释下一步任务；
- `center_projector.py` 或小型 service：组合当前研究、任务、动态、最近论文、统计；
- `model.py`：仅保存无法可靠推导的用户选择/阶段状态；
- 现有 `router.py`：只做参数验证和依赖注入。

文件名应服从仓库现有约定；若已有等价边界，复用并最小扩展。禁止创建万能 God Service。

## 五、数据源与唯一事实来源

- 论文身份与元数据：`LibraryItem` / paper library member；
- 阅读状态、章节和最近工作：`PaperWorkState`；
- 精确阅读位置与页暴露：document reader session/exposure；
- 分析状态与任务进度：`PaperAnalysis` 的持久化任务快照；
- 待确认字段：analysis pending confirmations；
- 研究项目及论文关系：`ResearchContext` / `PaperResearchRelation`；
- 活动事实：`PaperActivity`，必要时扩展为结构化、可跳转事件，但必须兼容旧记录；
- 当前研究与研究阶段：新增最小 actor-scoped preference/state，不能用“最近更新研究”隐式猜测。

不要把聚合结果复制为新的缓存表。不要让前端自行拼接领域规则。

## 六、HTTP 契约

### 1. 论文中心聚合

```http
GET /api/v1/paper-research/center
```

可选参数：

- `continue_limit`：1～10，默认 3；
- `activity_limit`：1～20，默认 5；
- `recent_limit`：1～20，默认 5。

返回使用严格 Pydantic DTO，不返回无类型 `dict[str, object]`。建议结构：

```json
{
  "current_research": null,
  "continue_tasks": [],
  "recent_activities": [],
  "recent_papers": [],
  "summary": {
    "papers": 0,
    "reading": 0,
    "deep_reading": 0,
    "completed": 0,
    "pending_confirmation": 0
  },
  "capabilities": {
    "current_research_selection": "available",
    "exact_reader_resume": "available",
    "next_action_rules": "available",
    "ai_task_planning": "unavailable"
  }
}
```

### 2. 当前研究

```http
GET /api/v1/paper-research/current-context
PUT /api/v1/paper-research/current-context
PATCH /api/v1/paper-research/current-context/stage
```

选择和阶段更新必须支持 optimistic concurrency：`expected_version` 不匹配返回现有统一结构化 `409`，旧状态保持不变。

允许清除当前研究，但必须显式表达；禁止把不存在/无权访问的研究设为当前研究。

研究阶段使用稳定枚举：

- `problem_definition`
- `literature_reading`
- `paper_understanding`
- `evidence_organization`
- `conclusion_formation`

不要通过关联论文数量自动推进阶段。

### 3. 活动历史

聚合首页返回有限条活动；如页面需要“查看全部”，增加：

```http
GET /api/v1/paper-research/activities?cursor=...&limit=...
```

使用稳定游标 `(created_at, id)`，时间相同也不能重复或漏项。每条活动应包含：

- `id`、`kind`、`occurred_at`；
- `paper_item_id`、论文标题；
- 可选 `research_context_id`、研究名称；
- 结构化 `target`；
- 用户可读摘要；
- `target_available` 和不可用原因。

兼容旧 `detail` 文本，不伪造无法从旧记录恢复的跳转目标。

## 七、继续任务与确定性下一步规则

每个任务至少返回：

- 论文身份、标题、期刊、年份、全文能力；
- 工作模式：`reading | deep_reading | confirmation`；
- 当前章节、阅读进度、分析完成数/总数；
- 最后工作时间；
- `next_action.kind/title/description/reason_codes/target`；
- 排序原因和是否手动置顶；
- entry capability，不能把不可阅读论文标成可继续。

规则优先级必须在纯函数中显式定义并单测。最低要求：

1. 有待确认字段 → `confirm_analysis`；
2. 分析任务未完成 → `continue_analysis`；
3. 阅读未完成且有精确 reader session → `continue_reading`，target 包含 session/page/offset；
4. 阅读未完成但只有章节 → `continue_reading`，target 退化为 item/section；
5. 可阅读但未开始 → `start_reading`；
6. 能分析且未开始 → 根据既有工作语义决定是否 `start_analysis`；
7. 资源失效 → 不生成可执行按钮，返回结构化不可用原因。

任务排序：

```text
手动置顶（若本轮实现最小持久化支持）
> 待确认
> 最近未完成工作
> 当前研究中的高角色优先级论文
> 未开始但可工作的论文
```

同分时必须使用稳定 tie-breaker（时间、item id），500 条候选仍保持确定顺序。若手动置顶不是前端冻结需求，可不新增该写能力，但不得返回虚假的 pinned 状态。

所有文案由结构化字段和国际化友好的 action kind 支撑；后端可返回默认中文文案，但前端不能只能依赖不可解析字符串。

## 八、统计口径

首页统计必须定义互斥或明确可重叠语义，并在 schema/docstring/test 中固定：

- `papers`：正式纳入论文库的论文总数；
- `reading`：阅读状态为 reading；
- `deep_reading`：存在进行中的持久化分析任务；
- `completed`：阅读完成且不存在进行中/待确认分析，或采用另一明确口径；必须选择一种并固定；
- `pending_confirmation`：待确认字段总数还是论文数，必须在字段名中区分。本版本建议返回 `pending_confirmation_items` 与 `pending_confirmation_fields`，避免含义模糊。

统计必须使用有界聚合查询，不加载全部对象后在 Python 中计数。

## 九、性能与一致性要求

1. 聚合接口禁止对每篇论文逐条查询，必须批量加载；测试应设置查询预算或用事件监听证明无 N+1。
2. 默认首页数据规模下建议查询次数固定，不随候选论文数线性增长。
3. 最近阅读 session 选择必须稳定，忽略隐藏历史；文件版本不匹配时返回降级或不可用，不提供错误精确跳转。
4. 所有列表排序加入唯一 id tie-breaker。
5. current-context 的并发更新使用独立 session 验证：一个成功，一个结构化 409；失败者不能覆盖成功者。
6. 新聚合读取不得产生数据库写入。
7. 无当前研究、空论文库、仅失效论文、仅历史分析、处理中、失败、取消和旧活动记录都要安全返回。

## 十、迁移要求

如新增当前研究偏好表：

- actor scope 唯一；
- research context 外键具有明确删除策略；
- stage 有 check constraint；
- version 从 1 开始；
- SQLite 与生产方言兼容；
- revision 的 `down_revision` 必须指向当前唯一 head；
- upgrade/downgrade 不能破坏现有 paper library、reader、analysis 数据。

迁移只在临时数据库执行：`upgrade → downgrade → upgrade`，并运行 Alembic check。正式数据库保持原 revision。

## 十一、验收标准

实施前先建立完整 traceability，以下每项至少映射一个真实行为测试。

- **AC-PCB-01**：空库、无当前研究时，center 返回完整稳定空结构和 capabilities。
- **AC-PCB-02**：可以设置、读取、切换、清除当前研究；不存在研究返回结构化 404/422。
- **AC-PCB-03**：研究阶段只能取稳定枚举，更新后持久化，不能被论文状态隐式改变。
- **AC-PCB-04**：两个独立 session 并发更新 current-context，只有一个成功，另一个 409，成功值保留。
- **AC-PCB-05**：继续任务一次返回阅读、分析、待确认状态及真实 capability，不虚构可执行入口。
- **AC-PCB-06**：next-action 规则的全部分支、降级和 reason codes 有纯函数测试。
- **AC-PCB-07**：精确续读使用最新有效 reader session 的 page/offset；隐藏、过期文件或缺失 session 正确降级。
- **AC-PCB-08**：继续任务排序符合优先级，时间相同以 id 稳定排序；500 候选连续运行顺序一致。
- **AC-PCB-09**：近期活动跨论文聚合，结构化 target 可用；旧记录无法定位时诚实降级。
- **AC-PCB-10**：活动游标分页在相同时间边界不重复、不遗漏，跨 actor scope 隔离。
- **AC-PCB-11**：最近研究论文按真实最近工作排序，返回状态、元数据与 entry capability。
- **AC-PCB-12**：五类统计符合固定口径，待确认论文数与字段数不混淆。
- **AC-PCB-13**：当前研究仅影响相应研究投影，不泄漏其他研究关系或任务。
- **AC-PCB-14**：center 在部分资源失效、处理中、失败、取消、历史未知进度时不伪造完成度。
- **AC-PCB-15**：聚合查询无 N+1，查询次数不随 1/100/500 候选线性增长。
- **AC-PCB-16**：limit 边界验证、确定性排序和响应 schema/OpenAPI 均稳定。
- **AC-PCB-17**：新写接口遵循现有 actor scope、CAS、错误 envelope 和事务回滚约定。
- **AC-PCB-18**：迁移旧库回填/默认值安全，临时库 upgrade→downgrade→upgrade 与 Alembic check 通过。
- **AC-PCB-19**：现有 paper_research、paper_library、document_reader、paper_analysis、research_context 回归全部通过。
- **AC-PCB-20**：正式数据库 revision 和内容未发生变化，git diff 无越界前端或无关模块修改。

关键测试必须先确认 RED，再实施。不能仅为行覆盖编写测试，必须验证 HTTP 行为、持久化结果、并发和排序。

## 十二、验证门禁

完成前必须依次执行并记录：

1. 新论文中心测试全集；
2. `tests/modules/paper_research` 全部测试；
3. `tests/modules/paper_library` 全部测试；
4. `tests/modules/document_reader` 全部测试；
5. `tests/modules/paper_analysis` 全部测试；
6. `tests/modules/research_context` 全部测试；
7. 与新迁移直接相关的 migration tests；
8. Ruff（只修本任务相关文件，不批量改写无关代码）；
9. 临时数据库 migration `upgrade → downgrade → upgrade`；
10. 临时数据库 `alembic check`；
11. `git diff --check`；
12. 检查正式 `data/app.db` 的 revision/文件摘要未变化。

如仓库有既定命令或隔离环境，使用仓库规范。Windows 环境按 `AGENTS.md` 清空错误注入的 `PYTHONPATH`。

## 十三、文档与最终报告

新增论文中心后端 traceability 文档，记录：

- 页面区域 → API → 字段 → 数据源；
- AC-PCB-01～20 → 测试文件/测试名 → 结果；
- 统计口径；
- next-action 规则表；
- capability 与降级语义；
- 查询预算；
- migration revision。

最终报告必须包含：

1. 每项 AC 的测试映射和通过结果；
2. 修改文件与职责；
3. 新 API 契约摘要；
4. migration revision 与临时库 round-trip 结果；
5. Ruff、相关回归、Alembic check、git diff check 结果；
6. 是否修改前端（必须否）；
7. 是否升级或写入正式数据库（必须否）；
8. local actor scope、未提供 AI 任务规划等剩余边界。

只有 AC-PCB-01～20 全部有真实测试且通过，才可声明完成。若发现缺陷，直接修复并重复验证；除非出现无法安全解决的真实并发冲突或缺少必须由用户提供的授权数据，不要停在阶段性汇报。
