# 医学科研RAG平台 — 项目文档与功能说明

> 文档版本：V1.0 ｜ 生成日期：2026-08-17
> 数据来源：`H:\AI_project\rag_medicine` 源码结构、`docs/` 各阶段状态文档、git 提交历史、API 路由注册
> 说明：本文档为项目现状梳理，功能描述以代码与文档实际交付为准，不含未实现的规划内容

---

## 1. 项目概述

**医学科研智能助手平台（rag_medicine）** 是一套面向医学科研人员的本地化 RAG + Agent 辅助平台，覆盖从**文献检索 → 证据整理 → 方向决策 → 科研写作 → 学术诚信**的完整研究链路。

| 项 | 内容 |
|---|---|
| 项目路径 | `H:\AI_project\rag_medicine` |
| 技术栈（后端） | FastAPI + SQLAlchemy(async) + Alembic + Pydantic v2 + httpx |
| 技术栈（前端） | Vue 3 + TypeScript + Vite + Vitest |
| Python 环境 | conda `med-research-ai`（Python 3.12） |
| LLM 接入 | 统一 OpenAI 兼容客户端：云端（OpenAI/OpenRouter）+ 本地 Ollama |
| RAG 能力 | FAISS 向量库 + BM25 混合检索 + RRF 融合 + 重排序 |
| Agent 能力 | LangGraph 状态机编排 + 人工确认 + 轨迹可观测 |
| 数据库 | SQLite（Alembic 管理，50+ 迁移） |
| 当前分支 | `feature/r0-wp01-baseline`（历史名沿用，实际已完成 R0–R4 各阶段） |

**核心设计原则（贯穿全项目）：**
- **确定性检索**：代码决定真实论文/元数据，LLM 只基于真实摘要写理由，不产候选/元数据/不编造
- **无发明规则**：未收录术语拒绝生成、无证据明确失败、检索失败不伪造成功
- **隐私安全**：密钥走 `.env`、日志脱敏、AI 使用留痕、内容出境需显式授权
- **版本不可变**：研究条件/提纲/草稿/方向等关键资产以不可变快照 + 版本号管理

---

## 2. 版本演进（R0 → R4）

| 阶段 | 主题 | 状态 |
|---|---|---|
| R0 | 工程基线：FastAPI 骨架、迁移回滚、云端/本地 LLM 最小调用、PaperQA2 独立实验、RAG 演示 | ✅ 已验收（2026-08-02） |
| R1 | 知识源登记与授权目录、增量同步、文档解析/索引双状态 | ✅ 已验收 |
| R2 | 文献检索链路：意图建模 → 术语扩展/MeSH → PubMed 布尔检索 → 结果去重/排序/阅读计划 → 收藏 | ✅ 已验收 |
| R3 | 研究闭环：研究条件 → 主题结构化 → 证据分析 → 候选方向 → 可行性评分 → 导师确认 → 提纲/写作/引用核验/AI 披露 | ✅ 代码验收通过（真人场景验收待执行，如实记录不伪造） |
| R4 | 文献推荐工作台 + LangGraph Agent 编排（分类/路由/限制/人工确认/轨迹） | ✅ 进行至 WP15 |

---

## 3. 功能模块详解

### 3.1 知识资产域（R1）

#### 知识源管理（knowledge_source）
- 登记本地文件夹、Obsidian Vault、临时导入目录三类知识源；校验目录存在性与可读性、拒绝重复登记、解析符号链接
- **增量同步**：扫描 `.pdf/.md/.doc/.docx/.pptx/.txt`，自动忽略 `.obsidian/.git/.trash`；流式 SHA-256 指纹，统计新增/修改/删除/跳过/失败
- 内容变化将文档标记为 `outdated`，不修改原始文件；目录不可用显示 `unavailable`

#### 文档生命周期（document + upload + preview + annotation + OCR + navigation）
- **解析/索引双状态机**：`pending/parsing/succeeded/failed` 与 `pending/indexing/succeeded/failed/outdated`，失败任务安全重试，不伪造成功
- **多格式解析**：PDF（逐页 1-based 页码、去跨页页眉页脚、识别扫描版）、Markdown（UTF-8 严格、front matter、标题层级）、DOCX/PPTX；旧 `.doc` 需本机转换器，绝不上传原文件
- **文档上传**：独立上传模块，文件走 Git 忽略目录
- **文档预览**：DOCX 转 HTML 预览
- **PDF 批注**：页面级/选区级标注（document_annotation），科研审计数据不删除
- **OCR 任务**：异步任务调度（scheduler + engine），支持队列与结果存储
- **文档导航**：全文/章节级内容导航与定位

#### 图书馆（library_item）
- 文献收藏与元数据管理，PMID/DOI 唯一索引
- **PMC 开放全文获取**（open_fulltext）：合法渠道拉取 PMC 开放全文并本地存储

### 3.2 文献检索域（R2 + R4）

#### 检索意图建模（R2-WP01）
- `POST /literature-search/parse-query`：把自然语言主题解析为可编辑的检索意图候选（疾病/干预/靶点/机制/时间/研究类型/语言/排除项）
- 原始主题永远保留；**不生成最终检索式**，全部字段由用户确认后再执行

#### 术语扩展与 MeSH（R2-WP02）
- 可编辑术语组：疾病/干预/靶点/机制，含保守中英别名、药物别名、基因别名（不编造未知术语）
- NLM MeSH 官方查询适配器，标注来源；不可用时返回空而不臆造
- 安全布尔检索式构造：同义词 OR、概念组 AND、字段标签；校验禁入 PubMed 的非法字符

#### PubMed 检索执行（R2-WP03 起）
- ESearch + EFetch 执行、速率限制、按日缓存、失败降级
- PICO 回退、过滤、排序、阅读顺序推荐、结果级去重（重复分组 + 去重工作视图）
- **可追溯策略工作台**：检索式、术语来源、策略指纹（fingerprint）全记录，历史版本可对比
- BibTeX 导出、阅读计划

#### 文献推荐（R4-WP01~06）
- 自然语言需求 → 可解释检索式构造（未收录术语拒绝）
- 真实 PubMed 检索 + 证据装配（只保留有摘要、未撤回的真实记录）
- LLM 只基于真实摘要写推荐理由；**模型输出含论文元数据时整条拒绝并确定性降级**
- 前端推荐工作台：检索中/错误/空结果/带警告/真实来源状态分栏展示，明确 LIVE · PubMed 边界

### 3.3 论文研究域（R3 + R4）

#### 论文分析（paper_analysis）
- 单篇论文结构化分析（研究设计/人群/干预/结局/机制），分析结果持久化供复用

#### 论文研究工作台（paper_research，2026-08 前端裁定）
- **研究概览**：论文集合总览
- **单篇精读**：论文详情 + 阅读批注入口（PDF 批注为精读次级入口）
- **证据问答**：基于真实论文摘要的证据问答（conversation 模块），含无答案策略（R1_NO_ANSWER_POLICY：不确定时明确说不知道，不编造）

#### 多论文比较与证据矩阵（comparison + evidence_matrix + evidence_analysis）
- 多篇论文对比任务（comparison_tasks），生成结构化对比矩阵
- **证据矩阵**：证据-来源绑定（PMID/DOI 必须存在于真实文献库）
- **证据分析**：统计层（纯函数：主题频次/样本量趋势/研究类型分布）+ 解读层（逐项绑定真实来源）；研究类型不混级

### 3.4 研究方向决策域（R3）

#### 研究条件（research_conditions）
- 不可变版本快照；每个字段保存 `value/known/source`；`known=false` 只接受 `source=unknown`，杜绝模型擅自补全

#### 主题结构化（topic_structuring）
- 原始主题不可覆盖；PICO/PECO/机制/非结构化四类守卫，不完整模板降级为 `unstructured` 并说明原因
- 澄清问题回填机制

#### 候选方向生成（research_direction）
- 一次生成 ≥3 个仅含核心字段的候选；详情按需生成
- 文献依据/证据/争议全部绑定真实来源；缺口字段强制保守措辞；gap-based + cross-topic 混合去重
- 合并保留目标并标记来源、DELETE 物理删除

#### 可行性评分（feasibility）
- 十维规则评分 + 用户自评；未填维度不猜分并降低置信度；评分只用于相对比较，不输出发表概率

#### 导师确认工作流（advisor_workflow）
- 真实/AI 模拟导师意见（模拟始终标注 AI 自测）；接受/修改/拒绝由纯函数状态机控制，修改保存不可变旧版
- 导师讨论 Markdown 报告导出

### 3.5 科研产出域（R3）

#### 组会汇报（presentation）
- 提纲复用已保存的论文分析/对比矩阵，不重复提取；图表未解析只提示人工查看原文，不生成数值

#### 综述/开题提纲（outline）
- 以证据矩阵为唯一事实来源；无来源内容显式标记缺证；候选方向不作既定事实

#### 写作项目管理（writing_project）
- 9 类写作类型；用户材料与生成内容分表存储；草稿/章节/引用/待确认项/模型事件存完整 JSON 快照
- 不可变版本 + 乐观并发（expected_version 冲突拒绝写入）

#### 证据驱动写作（evidence_writing + writing）
- 纯函数写作状态机：提纲确认 → 草稿生成 → 编辑 → 润色
- **句子级来源标记**：用户提供/论文证据/模型总结/模型推断/待确认
- 润色保护：数字、年份、PMID/DOI、专有名词 token 改变时拒绝保存；用户句子不可被改写

#### AI 写作辅助（writing_ai）、写作覆盖度（writing_coverage）、写作评审（writing_review）
- 单句 AI 建议、覆盖度评估、多角色评审

### 3.6 学术诚信域（R3）

#### 引用核验（citation_check）
- 三级核验：L1 本地格式 → L2 存在性（按日缓存）→ L3 标题/作者/年份一致性
- 非法 PMID/DOI 本地即标 `invalid_format`；网络失败标 `unverified`（不把失败误判为不存在）
- 陈述级核验：无引用/主题不匹配/通过；无效引用不自动创造替代文献

#### AI 使用披露（ai_disclosure）
- AI 使用事件记录：模型/目的/输入摘要/输出版本/人工修改/是否云端；不存输入全文
- 可编辑披露草稿 + 导出；confidential 项目输入范围替换为 `[confidential]`

### 3.7 系统能力域

#### 模型配置（model_config）
- 多供应商模型配置管理（云端/本地），内容出境授权标记（模型隐私设置迁移 d2f60a9c）

#### 评测（evaluation）
- 检索指标（retrieval_metrics）+ 答案指标（answer_metrics）评测运行，数据集管理与 runner

#### 反馈（feedback）
- 匿名用户反馈收集

#### 任务中心（task）
- 统一任务记录（R3 起），各模块任务状态汇总

#### 导出（export）
- Markdown 渲染导出（本地文件导出）

### 3.8 Agent 编排域（R4-WP12~15）

- **LangGraph 状态机**（agents/graph.py）：任务分类 → 规划 → 本地/外部检索 → 证据检查 → 方向 → 写作 → 引用检查 → 人工确认 → 完成/错误，条件边只读显式状态字段，限制最大步数
- **任务分类与路由**（agents/router + classifier）：规则优先，固定任务不启用 Agent、多工作流请求才启用、模糊任务要求澄清；分类结果不是工具执行授权
- **限制与人工确认**（agents/limits）：步骤/工具调用/资源/总时长纯规则校验；`interrupt()` 暂停确认，相同 thread_id 恢复，批准继续/拒绝终止
- **执行轨迹**（agents/trace）：运行节点/状态/耗时/审批记录，API Key 等密钥脱敏后导出

---

## 4. 后端架构

### 4.1 分层结构

```
app/
├── main.py                 # FastAPI 入口（CORS、统一异常处理）
├── api/v1/                 # 路由聚合（44 个 router 注册）
├── core/                   # 配置 / 数据库 / 模型 / 安全
├── common/                 # 异常体系 / 日志 / 哈希 / 路径工具
├── integrations/           # 外部集成
│   ├── llm/                #   统一 OpenAI 兼容 LLM 客户端
│   ├── ollama/             #   本地 Ollama 适配（禁云端回退）
│   ├── pubmed/             #   PubMed 客户端（缓存/限流/异常）
│   ├── paperqa2/           #   PaperQA2 隔离适配器
│   └── scispacy_client.py  #   scispaCy 可选集成
├── rag/                    # RAG 引擎
│   ├── bm25_store / faiss_store / embeddings
│   ├── hybrid_retriever / vector_retriever / reranker / rrf
│   └── orchestrator / splitter / notes_pipeline / schemas
├── agents/                 # LangGraph Agent 编排（state/graph/router/limits/trace）
└── modules/                # 40+ 业务模块（router/schema/service/repository/model 五件套）
```

### 4.2 业务模块清单（app/modules/）

| 域 | 模块 |
|---|---|
| 知识资产 | knowledge_source、document、document_upload、document_preview、document_annotation、document_ocr、document_navigation、library_item |
| 文献检索 | literature_search（14 个子模块）、recommendation、comparison |
| 论文研究 | paper_analysis、paper_research、conversation、evidence_matrix、evidence_analysis、research_context |
| 方向决策 | research_conditions、topic_structuring、research_direction、feasibility、advisor_workflow |
| 科研产出 | presentation、outline、writing_project、writing、writing_ai、writing_coverage、writing_review、evidence_writing、export |
| 学术诚信 | citation_check、ai_disclosure |
| 系统 | health、model_config、evaluation、feedback、task |

### 4.3 数据模型（Alembic 迁移摘要，50+ 版本）

按领域归纳主要数据表：
- **知识/文档**：knowledge_sources、documents、document_assets、parsed_document_content、document_annotations、document_ocr_jobs、document_task_states
- **检索**：literature_search_tasks、literature_search_results、literature_search_item_state、literature_strategy_fingerprint、literature_reading_orders、literature_duplicate_groups、result_scoped_dedup_work_views、library_items、pmc_open_fulltext_acquisitions、paperqa_index_mapping
- **研究流程**：research_conditions、topic_structuring、research_directions、feasibility_scores、feasibility_weight_profiles、advisor_workflow、research_context_evidence_links
- **产出**：evidence_matrix、comparison_tasks、outlines、presentations、writing_projects、writing_ai_suggestions、writing_reviews、local_markdown_exports
- **诚信/系统**：ai_usage_events、ai_disclosure_drafts、citation_check、evaluation_runs、task_records、anonymous_user_feedback、model_privacy_settings、no_answer_state

---

## 5. 前端页面清单（Vue 3 路由）

| 路由 | 页面 | 功能 |
|---|---|---|
| `/` | 首页（素问科研起始工作台） | 研究空间/继续研究/最近活动/知识概览/快速操作/系统状态，LIVE 后端数据 |
| `/models` | 模型设置 | 多供应商模型配置 |
| `/sources` | 知识库 | 知识源登记/同步/聚合统计 |
| `/documents` | 文档库 | 文档管理/过滤器/上传（入口归知识库导入流程） |
| `/documents/:id` | 文档详情 | 阅读批注工作台（预览/批注/OCR/导航） |
| `/literature-search` | 文献检索（可追溯策略工作台） | 意图编辑/术语扩展/MeSH/布尔式预览/策略指纹 |
| `/literature-search/history` | 检索历史 | 策略版本对比 |
| `/literature-search/results/:id` | 检索结果页 | 结果规模感知/去重工作区/阅读计划/收藏（FE-19~22 持续重构中） |
| `/recommendations` | 文献推荐工作台 | LIVE PubMed 推荐 + 理由分栏 |
| `/analysis` | 论文分析 | 证据问答 tab（/chat 重定向于此） |
| `/comparisons` | 多论文比较 | 对比矩阵 |
| `/evidence-matrix` | 证据矩阵 | 证据-来源绑定表 |
| `/research-directions` | 研究方向 | 候选方向生成/详情/合并 |
| `/citation-check` | 引用核验 | 三级核验报告 |
| `/presentations` | 组会汇报 | 提纲列表 + 编辑器 |
| `/writing` | 科研写作 | 写作项目列表 + 编辑器 |
| `/tasks` | 任务中心 | 统一任务记录 |
| `/agent` | Agent 编排 | 任务分类/运行/审批/轨迹 |
| `/evaluation` | 评测 | 检索/答案指标评测 |
| `/feedback` | 反馈 | 匿名反馈 |

**前端架构约定**：`src/api/` 封装后端接口（全部连真实 API，禁止硬编码演示数据）、`src/components/` 按域组织、`src/router/` 由 `features.ts` 驱动配置、`src/composables/` 共享逻辑、Vitest 单元测试 + TypeScript 严格检查。

---

## 6. 质量基线（以 R4-WP15 时刻为准）

- 全量 pytest：**491 passed, 13 skipped**（R4 状态文档记录；真实云端/本地模型集成测试默认跳过，需显式开关）
- ruff 0 错误、mypy 0 错误、alembic check 无漂移（最近 code-health 提交确认全绿）
- 前端：typecheck / Vitest / build 全通过
- 规范：`docs/CODE_STANDARDS.md`（V2.0，42 条），AGENTS.md/CLAUDE.md 有引用

---

## 7. 当前状态与注意事项（2026-08-17）

1. **工作区存在未提交改动**：`git status` 显示文献检索去重相关（DuplicateReview 组件删除、literature_search 模块修改、knowledge_source 同步增强、paperqa2 factory 等）——对应 1.2 目录 FE-22 续作"去重工作区与收尾"提示词，属于**正在进行的重构**，未提交
2. 前端推倒重做决策仍有效：R1 骨架页与 R2 组件已由素问风格新页面逐步替换（首页/文献检索/论文研究/推荐工作台已落地），剩余页面按 1.2 前端设计持续演进
3. 数据/上传文件（`.env`、`data/`、`uploads/`）均被 Git 忽略，不提交真实密钥与敏感材料
4. 运行方式（git-bash）：
   ```bash
   cd /h/AI_project/rag_medicine
   env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m uvicorn app.main:app --reload
   # 健康检查 http://127.0.0.1:8000/api/v1/health ｜ Swagger /docs
   ```

---

## 8. 待办与边界（如实记录）

- R3 真人场景验收（用户/导师真实输入）**尚未执行**，状态文档已如实标注，不伪造结论
- R4 Agent 检查点与运行记录目前**仅在进程内保存**，服务重启后失效（无数据库迁移）
- 引用核验报告当前为进程内短期存储
- 前端出境隐私提示（云端模型数据出境告知）仍待前端工作包实现
- 详见 `docs/R4_BACKLOG.md`、`docs/R3_BACKLOG.md`
