# 医学 Skills → 项目功能融合点清单

> 目的：把 Hermes 医学类 skills（search-lit / fulltext-retrieval / verify-refs / manage-refs / review-paper / present-paper）中封装的专家流程，融合为 rag_medicine 产品功能。
> 原则：**左侧导航大功能不变，在大功能内部以子功能/增量方式融合**；与 R2/R3/R4 工作包节奏对齐。
> 状态标记：🟢 已融合 / 🟡 部分融合 / 🔴 未融合
> 更新时间：2026-08-04（R2-WP03 完成时）

---

## 一、导航结构与融合落位（现状）

| 分组 | 大功能（不变） | 融合落位（子功能/增量） | 对应 Skill |
|---|---|---|---|
| 研究空间 | 工作台 / 论文分析 / 证据问答 | 论文分析：引用真实性标注 | verify-refs |
| 知识资产 | 知识库 / 文档库 / 文献检索 / 多论文比较 | 文献检索：反幻觉校验 + BibTeX 导出；知识库：OA 全文获取 | search-lit / fulltext-retrieval |
| 科研产出 | 研究方向 / 写作与汇报 / 组会汇报 | **引用核验 `citation-check`（已有预留位，UNAVAILABLE → 激活）**；写作：综述骨架；汇报：论文驱动 PPT | verify-refs / manage-refs / review-paper / present-paper |
| 智能工具 | Agent 实验室 / 评测中心 | 评测中心：引用审计作为评测项 | verify-refs |

---

## 二、逐 Skill 融合清单

### 1. search-lit（文献检索 + 引用管理）→ 文献检索模块

**现状**：`app/modules/literature_search/`（query_builder / mesh_client / term_expansion）+ `app/integrations/pubmed/`（ESearch/ESummary/EFetch + 限流 + 缓存 + 重试）已完成，WP03 真实联网验证通过（4/4）。

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| E-utilities 调用（esearch/esummary/efetch） | `app/integrations/pubmed/client.py` | 🟢 | 已实现并通过 live 测试 |
| 限流（3 req/s）、退避重试 | `rate_limit.py` + `_backoff` | 🟢 | 已实现 |
| TTL 缓存 | `cache.py` | 🟢 | 已实现 |
| 布尔查询构建（MeSH/同义词） | `query_builder.py` / `mesh_client.py` | 🟢 | 已实现 |
| **引用反幻觉协议**（verified=true/false 标记） | `literature_search/schema.py` 检索结果 | 🔴 | **建议 WP03.5 增量**：检索结果增加 `verified` 字段 |
| **BibTeX 生成**（`FirstAuthor_Year_Key` + verified 字段） | `literature_search` 导出接口 | 🔴 | 建议 WP03.5 增量：`GET /literature-search/{id}/bibtex` |
| 引用雪球扩展（snowball，Semantic Scholar） | 文献检索/多论文比较 | 🔴 | R3 候选 |

### 2. fulltext-retrieval（OA 全文获取）→ 知识库/文档库

**现状**：`app/modules/knowledge_source/` + `app/integrations/`（有 paperqa2、pubmed、ollama、llm）。

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| DOI → arXiv → Unpaywall → PMC → OpenAlex → Crossref 级联 | `knowledge_source` 采集管线（新增 `integrations/unpaywall.py` 等） | 🔴 | **R2-WP04/05 候选**（知识源采集） |
| PDF 校验（`%PDF-` 头 + ≥10KB） | 采集管线下载校验 | 🔴 | 同上 |
| PDF → Markdown（pymupdf4llm） | 文档解析（已有 pypdf） | 🟡 | 现有 pypdf 可升级为 pymupdf4llm |
| 检索报告（per-DOI status/source） | 知识源采集报告 | 🔴 | 同上 |

### 3. verify-refs（引用真实性审计）→ 引用核验（激活预留位！）

**现状**：导航 `citation-check` 引用核验（`features.ts` 已定义，UNAVAILABLE，showInNavigation: false）。

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| 手稿引用提取 + 对 PubMed/CrossRef 校验 | **激活 `citation-check` 子功能**（设为可见 + 新路由 + 新模块 `app/modules/citation_check/`） | 🔴 | **R2 收尾或 R3 首选**——已有预留位，改动最小、价值最高 |
| 审计报告 `reference_audit.json`（每引用 verified/来源/日期） | 前端引用核验页展示 ✅/⚠️/❌ | 🔴 | 同上 |
| 反幻觉：不可验证引用必须标记 | 审计输出 + 写作页联动 | 🔴 | 同上 |

### 4. manage-refs（引用管理）→ 写作与汇报

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| citation-key 校验、pandoc 渲染 | `app/modules/writing/` | 🔴 | R3 写作辅助 |
| 手稿 ↔ DOCX 交叉引用 QC | 写作模块导出流程 | 🔴 | R3 |
| Zotero 集成（可选） | 知识资产 | 🔴 | 可选，非核心 |

### 5. review-paper（综述骨架）→ 写作与汇报

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| 综述 7 部分骨架（叙事/PRISMA-ScR/系统综述） | `writing` 模块"新建综述"模板 | 🔴 | R3 写作辅助 |
| RV1-RV9 自查探针 | 写作后检查 | 🔴 | R3 |

### 6. present-paper（汇报 PPT）→ 组会汇报

**现状**：前端 `Presentations` 页面已有壳（MOCK）。

| Skill 能力 | 融合位置 | 状态 | 说明 |
|---|---|---|---|
| 论文驱动 PPT 生成（journal club/组会）+ 讲者备注 + Q&A | `research_direction`/`presentations` 后端生成 | 🔴 | R3/R4 |
| 前端 Presentations 页接入真实接口 | `frontend/src/views/Presentations/` | 🟡 | 已有页面壳 |

---

## 三、当前阶段（R2-WP03 完成后）推荐动作

按"改动小、价值高、不破坏现有验收"排序：

1. **【推荐，小改动】WP03.5 增量：文献检索反幻觉字段 + BibTeX 导出**
   - 检索结果 schema 增加 `verified` 标记（复用 WP03 已验证的 PubMed 数据）
   - 新增 BibTeX 导出接口（skill 的 key 规范：`FirstAuthor_Year_Key`）
   - 影响面：`literature_search` 模块内，不碰导航、不碰其他模块

2. **【推荐，独立模块】激活 `citation-check` 引用核验子功能**
   - 导航 `features.ts`：`citation-check` 设 `showInNavigation: true`
   - 新增 `app/modules/citation_check/`（提取引用 → PubMed/CrossRef 校验 → 审计报告）
   - 前端新增 `CitationCheckView.vue`
   - 这是 verify-refs skill 的完整产品化，且导航预留位本来就在

3. **【后续 WP】fulltext-retrieval 级联采集** → 排入 R2-WP04/05（知识源采集强化）

---

## 四、验证纪律

- 每项融合必须实际运行测试（pytest / npm typecheck+test+build）后才标记 🟢。
- 真实网络功能（PubMed/Unpaywall/CrossRef）必须跑 live 测试（如 `RUN_PUBMED_LIVE_TEST=1`），未实测标注【未实测】。
- 不伪造 PMID/DOI/论文数据；所有文献数据来自 API 真实响应。
