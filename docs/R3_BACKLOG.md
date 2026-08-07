# R3 Backlog

本清单记录 R2 阶段发现、但不在 R2 范围内实施的问题与增强点。按来源分类，每项注明**真实证据出处**（代码/文档/试用流程定位）；不在 R3 已授权范围内、不涉及真实用户缺陷/需求证据的项不列入。R3 实施前须逐项评审并立项。

## 一、R2 范围明确缺陷（发现于代码审查 / 前端执行检索功能修复）

### 1. 结果页去重的任务 ID / 结果 ID 混淆边界

- **证据**：`frontend/src/views/LiteratureSearch/ResultsView.vue` 中，去重接口 `POST /literature-search/{task_id}/deduplicate` 期望任务 ID，而结果页路由参数 `:id` 来自 `latest_result_id`（结果 ID）。前端在 `?task=` 查询参数缺失时以结果 ID 回退为任务 ID；若同一整数恰好同时是某任务 ID 与另一任务的结果 ID，会对错误任务去重。
- **影响**：去重触发对象可能错误，属于去重准确性的边界缺陷。
- **现状缓解**：从「检索历史」页进入结果页（URL 带 `?task=任务ID`）可避开该边界；`docs/R2_USER_TEST_SCRIPT.md` 第 5 步已标注该已知边界。
- **修复方向（供评审）**：结果页统一携带 `?task=`（执行检索成功跳转时由 `createTask` 返回的任务 ID 直接写入跳转 URL）；或将去重接口改为接受结果 ID 并由服务端解析对应任务。
- **验证方式**：前端组件测试覆盖「从执行检索直接跳转」与「从历史带 `?task=` 进入」两条路径的去重调用入参。

### 2. 证据矩阵前端仍为 MOCK，未接入 `/evidence-matrices` API

- **证据**：`frontend/src/views/EvidenceMatrix/EvidenceMatrixView.vue` 使用 `frontend/src/mocks/comparison` 原型数据，页面标注 `EVIDENCE MATRIX · MOCK`；`frontend/src/api/` 目录无 `evidenceMatrix.ts`，而 `POST /api/v1/evidence-matrices` 与 `POST /evidence-matrices/{id}/export` 后端能力在 R2-WP12 已实现（见 `docs/R2_IMPLEMENTATION_STATUS.md` WP12）。
- **影响**：证据矩阵能力仅能通过 API 调用（`docs/R2_USER_TEST_SCRIPT.md` 第 9 步当前即如此），前端用户无法在页面内创建/导出矩阵。
- **修复方向（供评审）**：新增类型安全 `evidenceMatrix.ts` API 客户端，将矩阵页接入真实端点（创建 / 读取 / 单元格编辑 / 版本 / 导出 CSV/Markdown），保留缺失值显式标注与 `provenance=model/manual` 区分；前端测试覆盖。
- **验证方式**：前端 typecheck / Vitest / build；用真实 `POST /evidence-matrices` 创建与导出核对。

---

## 二、R2 已知限制 / 增强点（来自各 WP 状态文档，未在 R2 实施）

### 3. 跨进程任务队列与数据库互斥

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP03「Rate limiting and backoff are in-process only」；WP04/WP06 相关单进程锁。
- **内容**：以跨进程任务队列（带后台进度与巡检）替代单进程索引/消息锁；队列状态可被多实例共享。
- **注**：此项已在 `docs/R2_BACKLOG.md` 优先候选第 1 条记录，此处归档到 R3 统一清单。

### 4. 结果级缓存为进程内 TTL，重启丢失

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP03「Cache is in-memory TTL; a restart clears it」。
- **内容**：PubMed E-utilities 缓存持久化到磁盘/数据库，跨重启复用；需设计缓存失效与密钥脱敏策略。

### 5. `is_open_access` 由 PMC id 推断，非许可核验

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP03「is_open_access is inferred from the presence of a PMC id, not from a license check」。
- **内容**：改用许可元数据（如 NCBI 许可信号）核验开放获取状态；不得绕过付费墙。

### 6. MeSH 查找依赖运行时网络，不可达时降级为空候选

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP02「MeSH lookup needs network access to the official NLM service at runtime; failures degrade to an explicit empty candidate set」。
- **内容**：提供离线/缓存 MeSH 词表回退，减少运行时网络依赖，同时保持「不编造描述符」约束。

### 7. 中文翻译与同义词覆盖有限

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP02「Curated translation and synonym coverage is intentionally limited. Unknown Chinese terms require user review」。
- **内容**：扩充医学词库（需真实数据来源与审核，不得虚构），或提供用户自定义同义词库。

### 8. 去重标题比对为规范化后精确匹配

- **证据**：`docs/R2_IMPLEMENTATION_STATUS.md` WP06「Title comparison is deliberately exact after normalization, not semantic similarity or translation inference」。
- **内容**：是否引入语义相似度/翻译推断作为 fuzzy 候选（需隐私评估与误判校准）。

### 9. 检索结果随时间变化，重跑产生版本差异

- **证据**：`docs/R2_USER_TEST_SCRIPT.md`「检索结果随时间变化」异常处理；WP04 重跑版本机制。
- **内容**：在检索历史/结果页提供「时间漂移」可视化对比（新增/减少 PMID 差异），辅助用户判断。

### 10. 多论文证据矩阵跨论文综合（R1 遗留，需新工作包）

- **证据**：`docs/R2_BACKLOG.md` 优先候选第 6 条。
- **内容**：在 R2-WP12 证据矩阵基础上做跨论文综合（表格/结论汇总），不得编造无来源结论。

### 11. PDF 复杂版式与可选 OCR

- **证据**：`docs/R2_BACKLOG.md` 优先候选第 3 条；`docs/frontend/FRONTEND_IMPLEMENTATION_STATUS.md` FE-02「scanned-PDF OCR limitation」。
- **内容**：双栏、表格、公式、混合扫描页与可选 OCR 的解析增强。

---

## 三、越界需求（R2 阶段明确禁止，仅登记不实施）

以下需求在 R2 来源需求/阶段禁止范围中明确排除，即使真实试用中用户提出，也只记录证据、不现场实施：

| 需求 | 出处/证据 | 状态 |
|---|---|---|
| 正式候选研究方向模块 | `.codex/R2-WP13-prompt.txt` 阶段禁止范围 | 越界，不实施 |
| 完整写作系统 | 同上 | 越界，不实施 |
| LangGraph Agent | 同上 | 越界，不实施 |
| 自动 Meta 分析 | 同上 | 越界，不实施 |
| 下载/绕过付费墙获取全文 PDF | 同上 + WP07 版权边界（`docs/R2_IMPLEMENTATION_STATUS.md` WP07） | 越界，不实施 |
| 多用户与机构部署 | 同上 | 越界，不实施 |

## 四、进入 R3 的规则

1. 每项必须关联真实证据（缺陷复现步骤 / 用户观察 / 代码定位），不虚构。
2. 实施前完成隐私评估、验收指标与独立工作包立项；临时需求不得绕过 R1/R2/R3 边界。
3. R3 工作包按优先级与依赖排期：缺陷类（第 1、2 项）优先于增强类（第 3–11 项）。
