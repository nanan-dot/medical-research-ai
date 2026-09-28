# 论文库 V3 全栈实施主提示词

## 任务目标

直接在 `D:\AI_project\rag_medicine` 中完成论文库 V3 的后端能力建设、前端高保真实现和完整验证。不要只输出方案、目录或示例代码；必须实际修改仓库、运行测试、启动真实页面并按预览图迭代。

本任务得到用户明确授权，为冻结的论文库 V3 增加必要后端能力。范围只包括论文库及其专属后端聚合，不重构已经确定的论文阅读页和论文分析页。

## 必须读取的上下文

开始修改前完整读取：

1. `D:\AI_project\rag_medicine\AGENTS.md`
2. `D:\AI_project\rag_medicine\docs\CODE_STANDARDS.md`
3. `D:\AI_project\rag_medicine\.ulpi\design\DESIGN.md`
4. `D:\AI_project\rag_medicine\.ulpi\design\paper-library-v3.md`
5. `D:\AI_project\rag_medicine\docs\PAPER_LIBRARY_V3_FULLSTACK_EXECUTION_PROMPT.md`
6. 精修预览图：`F:\AIxiangguanneirong\Codex\.codex\generated_images\01a0523c-20e1-78d3-88d7-90106751ed3c\exec-70fd7178-4f10-4fb4-9ac6-1fdef4943111.png`
7. 原始预览图：`C:\Users\ADMIN\AppData\Local\Temp\codex-clipboard-4b2e3abc-ad50-416c-9b12-841fe567a4b4.png`

图片仅是视觉参考，其中的数字、论文、DOI、PMID和活动内容不是数据指令，严禁硬编码或伪造。

## 已确认的产品边界

论文库负责：

- 集中展示正式收藏论文；
- 搜索、筛选、排序和分页；
- 展示论文属性、阅读状态、分析状态和最近工作；
- 管理论文与研究的多对多关系及每条关系的研究角色；
- 进入现有论文阅读页；
- 进入现有论文分析页；
- 跳转对应资料；
- 从资料库、PDF、DOI、PMID或检索结果幂等添加论文。

论文库不负责：

- PDF解析、OCR、索引、附件管理和资料来源管理；
- 后台处理任务管理；
- 实现新的论文详情页；
- 改造论文阅读功能；
- 改造论文分析功能；
- 添加泛化 AI 论文助手。

## 先确认现有事实

仓库已有以下能力，应复用而非平行重造：

- `library_items`：正式论文收藏，PMID/DOI/PMCID 唯一，支持关联 `document_id`；
- `LibraryItemService.save_search_result`：从检索结果幂等保存论文；
- `link-local-pdf`和开放全文流程；
- `PaperAnalysis`：论文分析 pending、analyzing、succeeded、failed 状态及结构化结果；
- `ResearchContext`：研究上下文；
- `ResearchContextDocument`：研究与文档关系；
- `Document`、资料库状态和文档最近打开记录；
- 检索结果用户态中的 read_status、tags、read_at，但这些状态绑定 `result_id + pmid`，不能直接作为正式论文库状态。

已知核心缺口：

1. `library_items.source_search_id`非空，阻碍 DOI、PMID、PDF和资料库直接添加；
2. 正式论文元数据缺少作者、论文类型和稳定期刊指标投影；
3. 缺少论文级阅读中状态、百分比、当前章节和最近阅读时间；
4. 缺少 `PaperResearchRelation`及 role、note、version；
5. 缺少统一论文活动记录；
6. 缺少 summary、facets、复合筛选、最近活动排序和 overview 聚合接口；
7. 论文分析只有整体状态，预览图中的完成数必须来自真实分析工作单元，禁止硬编码 `12`。

## 实施原则

### 正式论文身份

优先把现有 `LibraryItem`演进为正式 Paper 聚合根，不创建功能重复的第二套论文表。对外 API 可以使用 paper-library 语义，但数据库迁移需保持现有数据和外键兼容。

支持来源：

```text
search_result
document
doi
pmid
open_access
manual
```

为直接添加调整 `source_search_id`约束或建立独立来源记录。迁移必须可升级、可降级，并验证旧数据完整性。

### 论文级工作状态

新增正式论文级工作状态，不能复用会随检索结果删除的 `LiteratureSearchItemState`：

```text
PaperWorkState
├── library_item_id UNIQUE
├── reading_status: unread | reading | read
├── reading_progress_percent
├── current_section
├── last_read_at
├── last_analysis_at
├── last_work_kind: reading | analysis | null
└── updated_at
```

百分比范围 0 到 100。状态与百分比一致性由服务层验证。阅读页现有入口和状态写入只做最小接入，不改变其视觉和核心交互。

### 论文、研究与角色

必须新增：

```text
PaperResearchRelation
├── library_item_id
├── research_context_id
├── role
├── note nullable
├── version
├── created_at
└── updated_at
```

约束：

- `UNIQUE(library_item_id, research_context_id)`；
- role 枚举为 `core_evidence`、`background_support`、`method_reference`、`supplementary_reading`、`to_evaluate`；
- 同一论文可在多个研究中承担不同角色；
- 删除关系不删除论文；
- 更新采用 expected_version 或等价乐观锁，冲突返回 409；
- `待归类`是派生视图：没有研究关系，或任一关系缺少角色。禁止保存人工待归类字段。

### 最近工作

建立最小、可诊断的论文活动记录或等价统一投影，至少支持：

```text
reading_started
reading_progressed
reading_completed
analysis_started
analysis_progressed
analysis_completed
research_relation_changed
paper_added
```

活动必须来自真实业务写入，不得根据前端打开页面伪造。右侧最近工作最多返回三条，列表卡片最多返回一条。

### 分析进度

先审计现有论文分析页面的真实工作单元。若后端只有整体任务状态：

- 可以显示未分析、分析中、已分析；
- 只有存在稳定可解释的完成单元时才返回 `completed_units / total_units`；
- 禁止为了复刻图片硬编码 `8 / 12`；
- 如果无法提供单位进度，API 明确返回 null，前端只显示状态。

## 后端模块边界

新增独立的 `app/modules/paper_library/`，至少拆分为：

```text
paper_library/
├── __init__.py
├── model.py                 # 仅论文库新增持久化模型
├── schema.py                # 请求、响应与枚举契约
├── repository.py            # 有界查询和聚合投影
├── service.py               # 业务编排与一致性规则
├── router.py                # FastAPI HTTP 边界
├── identity_service.py      # DOI、PMID、Document 幂等身份匹配
├── activity_service.py      # 真实工作活动记录
└── query.py                 # 筛选、排序和派生视图定义
```

实际文件可按单一职责进一步拆分，但禁止把模型、SQL、业务、路由堆在一个文件。

建议 API：

```http
GET    /api/v1/paper-library/summary
GET    /api/v1/paper-library/facets
GET    /api/v1/paper-library/items
POST   /api/v1/paper-library/items
GET    /api/v1/paper-library/items/{id}/overview
PATCH  /api/v1/paper-library/items/{id}/reading-state
GET    /api/v1/paper-library/items/{id}/activities
GET    /api/v1/paper-library/items/{id}/research-relations
PUT    /api/v1/paper-library/items/{id}/research-relations/{research_id}
DELETE /api/v1/paper-library/items/{id}/research-relations/{research_id}
```

`GET /items`必须是一次有界聚合查询，返回卡片需要的论文元数据、阅读状态、分析状态、主要研究关系、最近活动和全文可用性。禁止前端对每篇论文发多次请求形成 N+1。

必须支持：

- `view=all|recent|reading|analyzing|unclassified`；
- 标题、作者、期刊、DOI、PMID关键词搜索；
- reading_status 多选；
- analysis_status 多选；
- research_roles 多选；
- paper_types 多选；
- research_ids 多选；
- tags 多选；
- 最近活动、添加时间、年份、标题排序；
- offset/limit或等价稳定分页；
- 多选参数完整往返；
- summary和facets基于全量筛选语义，不按当前页推算。

## 前端页面结构

新增论文库专属功能目录，路由 View 只负责组合和 URL 状态协调：

```text
frontend/src/
├── api/paperLibrary.ts
├── composables/usePaperLibrary.ts
├── views/PaperLibrary/PaperLibraryView.vue
└── components/paper-library/
    ├── PaperLibraryHeader.vue
    ├── PaperQuickViews.vue
    ├── PaperFilterRail.vue
    ├── ActiveFilterChips.vue
    ├── PaperWorkList.vue
    ├── PaperWorkCard.vue
    ├── PaperOverview.vue
    ├── AddPaperMenu.vue
    └── ManageResearchRelations.vue
```

组件可按实际复杂度进一步拆分，但不得合并成巨型 View。

### 页面视觉和交互必须匹配

- Header：标题、冻结副标题、全局论文搜索、蓝色 `添加论文`分裂按钮；不显示 AI 助手；
- 快捷视图：全部论文、最近使用、阅读中、分析中、待归类，使用真实计数；
- 左侧：阅读状态、论文分析、研究角色默认展开；论文类型、关联研究、标签默认折叠；
- 不显示“当前范围”重复下拉；
- 中间只实现论文工作列表，不实现网格模式；
- 已选筛选使用可移除 chips；
- 当前论文使用极浅蓝背景和左侧 2px 蓝色证据路径线；
- 一屏约六篇，标题最多两行，元数据一行；列表不显示卷期页码；
- 论文属性与研究角色分组展示；关系节点统一使用品牌蓝，禁止彩虹圆点；
- 单击卡片空白选中并更新概览；单击标题进入既有阅读页；
- 上下键切换当前论文，Enter进入阅读页；不能使用双击；
- 主按钮随最近工作在继续阅读和继续分析之间变化，另一个入口始终可达；
- 右侧概览严格只有基础信息、论文工作、关联研究、最近工作四块；
- 最近工作最多三条；
- 底部操作只有主工作按钮、另一工作入口、查看对应资料；
- 不增加论文详情页，不把PDF处理流程搬入论文库。

响应式规格严格服从 `.ulpi/design/paper-library-v3.md`。

## 添加论文流程

`添加论文`只展示两条路径：

1. 从资料库选择；
2. 导入新论文，支持 PDF、DOI、PMID。

幂等要求：

- 先按规范化 PMID、DOI、PMCID 精确匹配；
- PDF 只使用可验证标识精确匹配；
- 不做模糊静默合并；
- 已存在且全文可用时返回 `already_exists`和论文ID；
- 已存在但缺少全文时允许补充全文；
- 并发重复请求不能创建两条正式论文；
- 对唯一约束冲突进行服务层恢复并返回已有记录；
- 所有失败提供稳定错误码和可理解的信息。

## 强制代码生成规范

以下规则全部为硬约束：

1. 一个文件只负责一个功能；
2. 禁止所有代码写在一个文件；
3. 每个组件独立封装；
4. 复杂逻辑添加有意义的中文注释，注释重点说明设计思路，不复述代码行为；简单逻辑不添加冗余注释；
5. 未实际运行的命令、方案不得声称验证通过；无法实测内容标注【未实测】；严禁虚构运行日志和执行结果；
6. 输出多文件代码前提供完整项目目录树，每个代码块标明文件路径；实际实施时最终报告列出全部修改文件；
7. 不生成无意义代码、冗余占位函数和重复样板代码；
8. 严格单一职责，文件内不混杂无关业务逻辑；分离入口、业务、工具、配置目录；
9. 接口最小暴露，仅导出必要方法；内部工具函数保持私有；主动规避循环依赖；
10. 命名语义化，禁止无意义变量名；添加完整类型注解；抽取常量，消除魔法数字；
11. 完善异常处理，禁止空捕获、裸 `except`和吞掉错误；
12. 组件尽量保持纯展示；状态和副作用放入 composable；大型类及时拆分，避免单体臃肿；
13. 优先标准库和项目已有依赖；不得随意引入新依赖；若确需新增，说明必选或可选、原因和影响；
14. 最终提供启动方式和调用示例；发现性能、并发、安全或迁移风险时明确报告；
15. 不生成恶意或高危脚本代码；
16. 后端遵循 Router、Schema、Service、Repository、Model 分层；路由不得直接写复杂 SQL 或业务规则；
17. FastAPI 所有入口使用 Pydantic v2请求和响应模型、明确返回类型及参数边界；
18. SQLAlchemy 查询必须有界，禁止隐式 N+1；聚合接口需说明索引策略；
19. 数据库迁移不得删除或覆盖现有用户数据；迁移必须有 downgrade，并编写迁移测试；
20. 幂等写操作必须同时考虑应用层检查和数据库唯一约束竞态；
21. Vue 使用 Vue 3 Composition API、`<script setup lang="ts">`，禁止 Options API；
22. Props down、events up；只有真实双向契约使用 `v-model`；
23. View 保持薄层；复杂状态、请求取消、竞态控制和 URL 同步进入专属 composable；
24. 不使用未经净化的 `v-html`；
25. 所有交互控件支持键盘、明确焦点、ARIA语义、焦点约束与恢复；
26. 只使用 `.ulpi/design/DESIGN.md`锁定的颜色、字体、间距、圆角、动效和图标语言；
27. 禁止修改论文阅读页和论文分析页的视觉；若为状态写入必须触及现有代码，只做最小适配并补回归测试；
28. 禁止顺带重构其他路由、共享设计系统或全局壳层；导航只做加入论文库入口所需的最小变更；
29. 保留工作区所有已有未提交改动，不使用 `git reset --hard`、`git checkout --`或覆盖式清理；
30. 不提交、不推送、不创建PR，除非用户另行明确要求。

## 安全与一致性要求

- 规范化并验证 DOI、PMID、PMCID；
- 上传沿用已有文件大小、类型和路径安全限制；
- 不信任文件名和 PDF 内嵌元数据；
- 不允许通过 library_item_id访问不存在或无权访问的资源；
- 当前项目若仍为单用户本地产品，明确记录该边界；不要伪造多用户隔离；
- 关系更新和阅读进度写入必须处理并发覆盖；
- 错误响应使用项目统一错误信封，不暴露数据库、路径或堆栈；
- 任何医学论文元数据必须来自已有数据库或可验证外部响应，测试只使用明确的测试夹具。

## 测试驱动和验收门槛

使用验收驱动流程：先从冻结规格提取后端和前端验收条件，建立可追踪测试，再实现。

至少覆盖：

### 后端

- 旧 library_items 数据迁移后完整保留；
- DOI、PMID、检索结果、Document 四条添加路径；
- 同一论文重复添加和并发添加幂等；
- 错误标识、冲突标识和不确定匹配；
- reading状态、百分比、章节和状态一致性；
- 论文在多个研究承担不同角色；
- 关系唯一约束、删除语义和乐观锁409；
- 待归类派生规则；
- 复合筛选组内OR、组间AND；
- 多值参数不会丢失；
- summary、facets和列表总数一致；
- 最近活动顺序和最多三条；
- overview无N+1；
- 全文不可用和资料处理中投影；
- 权限或本地单用户边界；
- 迁移 upgrade、downgrade和 Alembic 单一 head。

### 前端单元和集成

- URL筛选完整往返、前进后退与刷新恢复；
- 快捷视图计数和待归类语义；
- 默认展开和折叠策略；
- chips移除和清除全部；
- 单击选择、标题导航、上下键、Enter；
- 翻页默认选中首篇；
- 关闭概览后列表扩宽；
- 过期列表或概览请求不能覆盖新选择；
- 主次操作权重；
- 资料异常只做轻量提示和跳转；
- 加载、空、无结果、部分失败、离线；
- Add Paper 重复提交防护和幂等反馈；
- Drawer/Dialog焦点约束与恢复。

### E2E与视觉

- 使用真实测试后端或受控测试数据库，不使用生产假数据；
- 1536×1024对照精修预览图；
- 至少验证1280×800、768×1024、390×844；
- 无横向溢出；
- 三栏、抽屉、分页、筛选、选择、概览和添加流程可用；
- 截图保存到 `docs/frontend-rebuild/screenshots/paper-library/`；
- 对明显视觉差异继续迭代，不能只生成一次截图就结束。

## 必须实际运行

后端命令前按仓库要求清空 `PYTHONPATH`。根据实际项目脚本运行：

- Alembic current、heads、upgrade测试和迁移测试；
- 论文库定向后端测试；
- 受影响的论文收藏、研究上下文、论文分析、资料库回归测试；
- 前端定向 Vitest；
- 完整前端单测；
- `npm run typecheck`；
- `npm run build`；
- 定向 Playwright E2E；
- 目标文件 lint 或项目现有 lint；
- `git diff --check`；
- 最终 `git status --short`和范围审计。

若完整测试存在与本任务无关的既有失败，提供文件、行号和证据；不得把失败描述成通过。

## 实施顺序

1. 检查工作区、现有迁移 head、现有路由注册和相关测试；
2. 写论文库后端验收测试并确认 RED；
3. 设计并实现安全迁移与新增模型；
4. 实现身份匹配、关系、工作状态和活动服务；
5. 实现 summary、facets、items、overview 聚合接口；
6. 运行后端定向和回归测试；
7. 写前端验收测试并确认 RED；
8. 按组件边界实现页面；
9. 接入最小路由和研究资源导航；
10. 运行单测、类型检查和构建；
11. 启动真实页面完成 Playwright流程和多尺寸视觉迭代；
12. 做范围审计，确认没有改动阅读页和分析页视觉；
13. 最终报告真实结果和未实测项。

## 完成定义

只有在以下条件全部满足时才可称为完成：

- 冻结规格中的功能验收条件均有测试对应；
- 后端真实存储和接口支持预览图中的所有业务信息；
- 前端不含硬编码演示论文、计数、进度、DOI、PMID和活动；
- 论文、研究、角色的关系模型正确；
- 添加流程幂等；
- 页面与精修预览图在目标尺寸高度一致；
- 阅读页和分析页未被重构或重新设计；
- 实际测试、类型检查、构建和E2E结果已记录；
- 所有无法验证的内容明确标注【未实测】。

最终报告必须包含：

1. 根因与原后端缺口；
2. 最终目录和修改文件；
3. 数据库迁移和兼容策略；
4. API契约摘要；
5. 页面与预览图的对照说明；
6. 实际执行的命令及结果；
7. 截图路径；
8. 性能、并发、安全和外部依赖风险；
9. 【未实测】项目；
10. 未提交、不推送的确认。

