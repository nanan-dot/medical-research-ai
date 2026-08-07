# R2 真实用户检索验收脚本

状态：**待执行**。本脚本覆盖 R2 文献检索全流程（9 步），用于验证「输入方向 → 生成检索式 → 检索 PubMed → 筛选 → 去重 → 保存 → 阅读顺序 → 比较 → 导出证据矩阵」端到端可用性。每步给出可执行操作、预期结果、需记录字段与耗时。

## 准备

- 试用者：1 名未参与 R2 开发的科研用户；观察者只在用户明确求助时介入。
- 环境：本地启动后端（`uvicorn app.main:app`，`/api/v1`）+ 前端（`npm run dev`，Vite 代理 `/api` → `http://127.0.0.1:8000`）。
- 前置：后端已执行 `alembic upgrade head`；模型设置中已配置可用的检索意图解析模型（本地或云端均可）。
- 网络：PubMed（NCBI E-utilities）与 NLM MeSH 需网络可达；MeSH 不可达时系统应显式返回空候选集合而不编造。
- 隐私：记录中不出现姓名、邮箱、论文正文；5 篇保存文献只记录公开 PMID/DOI。
- 记录：开始/结束时间、每步是否独立完成、求助次数、阻塞/严重/一般错误。

### 参考方向（PICO 示例）

试用者可自选真实方向。若缺乏检索经验，使用以下示例：

> **方向**：奥希替尼一线治疗 EGFR 突变晚期非小细胞肺癌的疗效与安全性
> **PICO**：P=EGFR 突变（19del/L858R）晚期非小细胞肺癌成人患者；I=奥希替尼（三代 EGFR-TKI）一线治疗；C=一代/二代 EGFR-TKI 或含铂化疗；O=无进展生存期、总生存期、客观缓解率、≥3 级不良事件。

参考检索式（**示例，非系统生成**；系统生成的检索式以「生成检索式」步骤为准）：

```
("osimertinib"[Title/Abstract] OR "AZD9291"[Title/Abstract])
AND ("carcinoma, non-small-cell lung"[MeSH Terms] OR "non-small cell lung cancer"[Title/Abstract])
AND ("EGFR"[Title/Abstract] OR "epidermal growth factor receptor"[Title/Abstract])
AND (first-line OR "first line" OR initial)
```

## 固定任务（9 步）

每步记录：`耗时`（分钟）、`独立完成`（是/否）、`求助`（次数）、`观察`（一句话）。观察必须是具体现象，不得只写"好/坏"。

### 第 1 步：输入真实方向

- **操作**：打开 `/literature-search`，在「研究主题」输入一个真实方向（可用上例），点击「生成候选条件」。
- **预期结果**：显示候选条件（疾病/干预/靶点/机制/时间范围/研究类型/语言/排除项/retmax）；候选来源标注为「模型候选」或「规则候选」；原始主题原文保留展示；候选字段均可编辑。
- **API 入口**：`POST /api/v1/literature-search/parse-query`（前端 `literatureSearchApi.parseQuery`）。
- **记录字段**：输入方向文本、候选来源（model_candidate / rule_fallback）、是否需要人工修改候选、clarification_questions 是否出现。
- **耗时**：____ 分钟

### 第 2 步：生成检索式

- **操作**：点击「扩展关键词与 MeSH」→ 在词分组编辑器中审查英文关键词/同义词分组 → 点击「生成 PubMed 检索式」→ 阅读布尔检索式与字段限定说明。
- **预期结果**：同义词组以 `OR` 连接、概念组以 `AND` 连接、带字段标签（如 `[Title/Abstract]`）；MeSH 候选标注来源 `NLM MeSH`（网络可用时），不可用则显式空候选；检索式不含纯中文词；检索式可被用户读懂。
- **API 入口**：`POST /api/v1/literature-search/expand-terms`、`POST /api/v1/literature-search/build-query`（前端 `literatureSearchApi.expandTerms` / `buildQuery`）。
- **记录字段**：检索式可读性打分（1–5）、是否需人工修正词分组、MeSH 候选可用性、布尔逻辑是否可理解。
- **耗时**：____ 分钟

### 第 3 步：检索 PubMed

- **操作**：在「执行 PubMed 检索」区块点击「执行检索」。系统会创建检索任务并立即真实调用 PubMed（ESearch + EFetch），成功后跳转到结果页。
- **预期结果**：任务状态为「已完成」（succeeded）；结果数 > 0；结果条目带真实 PMID/DOI/标题/作者/期刊/年份，并如实标注是否有摘要与文献类型；页面展示本次检索式与结果总数。
- **API 入口**：`POST /api/v1/literature-search`（创建任务 + 执行检索，服务端复用 `pubmed_executor`）；结果读取 `GET /api/v1/literature-search/{id}`。
- **记录字段**：任务 ID、`total_count`、`retmax`、检索日期（`searched_at`）、结果相关性主观打分（1–5）、是否出现明显无关结果。
- **耗时**：____ 分钟

### 第 4 步：筛选结果

- **操作**：在结果页使用筛选（年份 / 文献类型 / 期刊 / 作者 / 有摘要 / 已保存 / 已读 / 标签）、排序（relevance / newest / classic / custom）、分页切换。
- **预期结果**：筛选后条数（filtered_total）与分页更新；每条结果带排序理由（sort_reason）；`classic` 排序基于可解释信号（权威期刊白名单 + verified + 近 5 年），不出现被引量/影响因子等编造字段；年份缺失的条目排在最后。
- **API 入口**：`GET /api/v1/literature-search/{id}/results`（白名单参数 `year / publication_type / journal / author / has_abstract / saved / read_status / tags / sort / page / page_size`，未知参数被忽略，非法值 422）；用户态读写 `PATCH /api/v1/literature-search/{id}/items/{pmid}/state`。
- **记录字段**：使用的筛选条件与排序方式、筛选后条数、`sort_reason` 是否可解释、是否出现筛不干净或漏筛。
- **耗时**：____ 分钟

### 第 5 步：去重

- **操作**：在结果页点击「去重」→ 查看生成的重复组 → 逐组点击解决（保留单条 / 全部保留 / 合并 / 撤销）。
- **预期结果**：每个重复组标注匹配方法（PMID / DOI / 标题规范化 / 作者+年份）与置信度（clear / fuzzy）；解决操作可撤销；原始检索结果不被删除或改写。
- **API 入口**：`POST /api/v1/literature-search/{task_id}/deduplicate`（**注意：入参是任务 ID，不是结果 ID**）、`GET /api/v1/duplicate-groups`、`POST /api/v1/duplicate-groups/{id}/resolve`。
- **已知边界**：从「执行检索」直接跳转的结果页 URL 不含 `?task=` 参数，前端回退用结果 ID 作为任务 ID；若同一整数恰好也是某个任务 ID，可能去重到错误任务（见 `docs/R3_BACKLOG.md`）。**从「检索历史」页进入结果页（URL 带 `?task=`）可避开该边界。**
- **记录字段**：重复组数量、各匹配方法分布、置信度、采用的动作、是否出现误判（非重复被判为重复或反之）。
- **耗时**：____ 分钟

### 第 6 步：保存 5 篇论文

- **操作**：从结果页选择 5 篇（建议覆盖不同文献类型），逐篇点击「加入知识库」；同一篇再次点击应幂等返回已有记录。
- **预期结果**：5 篇均保存成功；每条返回全文状态（`metadata_only` / `local_pdf_available` / `open_access_available`）与可解释理由；保存不自动下载全文、不绕过付费墙；5 个 PMID/DOI 均可被 `POST /api/v1/citation-check` 校验为真实可解析。
- **API 入口**：`POST /api/v1/literature-results/{result_id}/save`（每篇一个 `pmid`；前端 `literatureSearchApi.saveToLibrary`）；知识库列表 `GET /api/v1/library-items`；来源核验 `POST /api/v1/citation-check`。
- **记录字段**：5 个 PMID、各自 `fulltext_status` 与 `fulltext_status_reason`、核验结果（真实/伪造）、是否有保存失败。
- **耗时**：____ 分钟

### 第 7 步：排定阅读顺序

- **操作**：在结果页点击「生成阅读顺序」→ 查看每篇的类别标签（综述 / 指南共识 / 原始研究 / 前沿 / 高相关）、优先级与理由；如有需要，拖拽调整顺序并保存人工顺序。
- **预期结果**：每条带 `category` + `priority` + `reason` + `evidence_features`（真实字段触发的特征）；理由可读、不出现被引量/影响因子；保存人工顺序后 `order_source=manual`，重新生成不覆盖人工顺序。
- **API 入口**：`POST /api/v1/literature-search/{result_id}/reading-order`（生成，可带 `manual_order`）、`PUT /api/v1/literature-search/{result_id}/reading-order/order`（保存人工顺序，全量替换）。
- **记录字段**：分类是否符合直觉（如综述应优先）、理由是否可读、人工顺序是否被保留、`order_source` 是否正确切换。
- **耗时**：____ 分钟

### 第 8 步：比较 3 篇

- **操作**：从已保存的 5 篇中选 3 篇（**需为本地文档库中已绑定 PDF 且已完成论文分析的文档，否则比较单元格显示「缺失」**）。打开 `/comparisons`，输入 3 个文档 ID（从 `/documents` 文档库页获得），创建比较矩阵；查看字段行×论文列；对其中一个单元格做人工修订；导出 CSV 与 Markdown。
- **预期结果**：矩阵单元格带可追溯来源（真实 PMID/DOI + locator）或显式「缺失」；人工修订后状态为 user_edited，重新生成不覆盖；研究类型行突出；导出文件可在本地编辑器打开核对。
- **前置说明**：比较矩阵的证据来自 `paper_analysis` + `library_item`（`comparison/service.py:_evidence_value`）。只有本地文档且已有结构化分析的收藏才有生成值；`metadata_only` 收藏无本地文档，比较单元格为「缺失」。这是当前真实能力边界，不是系统缺陷。
- **API 入口**：`POST /api/v1/comparisons`（`selected_document_ids` 为本地文档 ID，3–10 个且不重复）、`GET /api/v1/comparisons/{id}`、`PATCH /api/v1/comparisons/{id}/cells`、`POST /api/v1/comparisons/{id}/regenerate`、`GET /api/v1/comparisons/{id}/export?format=csv|markdown`。
- **记录字段**：3 个文档 ID、有来源的单元格数、「缺失」单元格数、人工修订是否保留、矩阵是否可用于实际工作（1–5）。
- **耗时**：____ 分钟

### 第 9 步：导出证据矩阵

- **操作**：基于第 8 步的比较任务创建证据矩阵，并导出 Markdown 与 CSV；用本地编辑器打开核对中文、来源、缺失值标注。
- **预期结果**：矩阵带版本号（v1）、字段行×文档列、文献状态尾注（included/pending + 用户备注）；缺失值显式标注「缺失」，不编造数据。
- **API 入口**：`POST /api/v1/evidence-matrices`（`name` + `source_comparison_id`，继承比较的字段与文献）、`POST /api/v1/evidence-matrices/{matrix_id}/export`（body `{"format": "markdown"}` 或 `{"format": "csv"}`）。
- **前端状态**：证据矩阵页（`/evidence-matrix`）当前为 **MOCK**（`frontend/src/views/EvidenceMatrix/EvidenceMatrixView.vue` 使用原型数据，未接入 `/evidence-matrices` API；见 `docs/frontend/FRONTEND_IMPLEMENTATION_STATUS.md`）。因此本步通过 API 直接调用完成；前端接入列入 `docs/R3_BACKLOG.md`。
- **记录字段**：矩阵 ID、版本号、导出格式、缺失值标注是否正确、打开导出的核对结果。
- **耗时**：____ 分钟

## 每步 API 入口速查表

| 步骤 | 前端页面 | API 入口 | 入参关键点 |
|---|---|---|---|
| 1 输入方向 | `/literature-search` | `POST /literature-search/parse-query` | `raw_topic` |
| 2 生成检索式 | `/literature-search` | `POST /literature-search/expand-terms`、`POST /literature-search/build-query` | candidate / term_groups |
| 3 检索 PubMed | `/literature-search` → 结果页 | `POST /literature-search`、`GET /literature-search/{id}` | search_string（布尔检索式） |
| 4 筛选结果 | `/literature-search/results/:id` | `GET /literature-search/{id}/results`、`PATCH /literature-search/{id}/items/{pmid}/state` | 白名单筛选/排序/分页参数 |
| 5 去重 | 结果页「去重」面板 | `POST /literature-search/{task_id}/deduplicate`、`GET /duplicate-groups`、`POST /duplicate-groups/{id}/resolve` | **任务 ID**（非结果 ID） |
| 6 保存 5 篇 | 结果页「加入知识库」 | `POST /literature-results/{result_id}/save`、`POST /citation-check` | result_id + pmid（逐篇） |
| 7 阅读顺序 | 结果页 ReadingPlan | `POST /literature-search/{result_id}/reading-order`、`PUT /literature-search/{result_id}/reading-order/order` | result_id |
| 8 比较 3 篇 | `/comparisons` | `POST /comparisons`、`GET /comparisons/{id}`、`PATCH /comparisons/{id}/cells`、`POST /comparisons/{id}/regenerate`、`GET /comparisons/{id}/export` | 本地文档 ID（3–10） |
| 9 导出证据矩阵 | `/evidence-matrix`（MOCK）→ 走 API | `POST /evidence-matrices`、`POST /evidence-matrices/{matrix_id}/export` | `source_comparison_id` 继承 |

## 错误处理指引

- **缺乏检索经验 / 反馈不清**：使用上方 PICO 示例方向与参考检索式；观察者不代操作，只提示「检索式可以由系统生成，注意核对括号与字段标签」。
- **检索结果随时间变化**：这是已知异常。每步记录 `searched_at`（检索日期）；重跑会创建新版本并给出新旧结果变化摘要（新增/减少 PMID），用于判断时间漂移。
- **网络失败 / PubMed 超时**：任务状态变为「失败」（failed）并显示 `error_message`；在「检索历史」对该任务点击「重跑」创建新版本重试。记录失败原因。
- **空结果**：`total_count = 0` 时如实显示；检查检索式是否过窄或字段标签错误。
- **MeSH 不可达**：系统返回显式空候选集合，不编造描述符；记录该现象并继续手工补充同义词。
- **临时需求越界**（例如要自动 Meta 分析、下载全文 PDF）：记录到 `docs/R3_BACKLOG.md`，不现场实施。
- **阻塞问题**：观察者记录复现步骤与现象，修复后由同一试用者从失败步骤重做；阻塞问题未修复前报告不签署。

## 完成率

固定任务共 9 项；`任务完成率 = 无观察者代操作完成项 / 9`。主观评价（相关性打分、可理解打分、矩阵可用性）必须附至少一个具体观察或选择结构化真假项，否则不作为缺陷证据。
