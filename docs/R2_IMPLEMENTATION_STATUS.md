# R2 implementation status

## R2-WP01 — medical literature search intent modelling

**Status:** complete

### Entry decision

R1 automated acceptance passed (168 tests at the time of the handoff). The real-user trial remains an explicit R2 backlog item and does not block this work package, as confirmed by the user.

### Delivered

- Added `POST /api/v1/literature-search/parse-query` for converting the raw user topic into an editable search-intent candidate.
- Preserved the raw topic in every response; the API does not generate or expose a final database search expression.
- Added bounded candidate fields: topic, disease, intervention, target, mechanism, date range, study types, language, exclusions, and `retmax`.
- Used the configured model only for candidate extraction, constrained relative date language from the original input, and used a no-invention rule fallback for invalid model JSON.
- Added a `/literature-search` page with a manual `QueryBuilder`; all candidate fields can be reviewed and changed before any later search work.

### Verification

- Backend: `173 passed, 5 skipped` (`pytest -q`)
- Backend static checks: Ruff and mypy passed.
- Migration check: Alembic reports no new upgrade operations; WP01 introduces no persistence model.
- Frontend: `12 passed` (Vitest), Vue typecheck passed, and production build passed.

### Known limitations / R2 backlog

- A real-user trial remains to be carried out and recorded during R2; it was intentionally not treated as a WP01 blocker.
- Candidate extraction is not medical terminology normalization or clinical decision support. Users must review all candidates.
- WP01 intentionally contains no PubMed/search-provider execution or final search-expression generation. Those capabilities belong to later work packages.

### Next boundary

Stop after R2-WP01. Do not begin R2-WP02 as part of this work package.

## R2-WP02 — keyword, synonym, and MeSH assistance

**Status:** complete

### Delivered

- Added editable term-group expansion for disease, intervention, target, mechanism, and topic fallback.
- Added conservative Chinese-to-English aliases, curated synonym groups, drug aliases, and gene/target aliases without fabricating unknown terms.
- Added an official-source-labelled NLM MeSH lookup adapter. Unavailable or empty lookups return no assumed MeSH descriptor.
- Added safe PubMed boolean-query construction: synonyms are joined by `OR`, concept groups by `AND`, and field tags are included in the returned query.
- Added validation for non-ASCII Chinese terms, braces, semicolons, and newlines so they cannot be sent directly into PubMed query output.
- Added the editable frontend `SearchTermsEditor`, MeSH candidate display, boolean-query preview, and operator explanation.

### Verification

- Backend: `188 passed, 5 skipped` (`pytest -q`), including 15 WP02 unit tests and a 10-topic curated term matrix.
- Ruff and mypy passed; Alembic reports no new upgrade operations. WP02 has no persistence-model change.
- Frontend: `13 passed` (Vitest), Vue typecheck and production build passed.
- Production dependency audit: `0 vulnerabilities`.

### Manual verification steps

1. Start the API and frontend, open `/literature-search`, and submit a topic such as `胃癌 EGFR 免疫治疗`.
2. Review and edit the generated term groups, removing an unwanted synonym if needed.
3. Select “扩展关键词与 MeSH”; verify each MeSH candidate identifies `NLM MeSH` as its source, or that an unavailable lookup is shown without an invented descriptor.
4. Generate the PubMed query and confirm every synonym group is parenthesized with `OR`, concept groups use `AND`, and no Chinese-only term appears in the query.

### Known limitations / R2 backlog

- MeSH lookup needs network access to the official NLM service at runtime; failures degrade to an explicit empty candidate set.
- Curated translation and synonym coverage is intentionally limited. Unknown Chinese terms require user review and must not be emitted as PubMed terms.
- The generated query is an editable search aid, not medical advice or an executed provider search.

### Next boundary

Stop after R2-WP02. The next task is R2-WP03; do not start it here.

## R2-WP03 — PubMed client (NCBI E-utilities)

**Status:** implemented — automated tests NOT yet executed in this session

### Entry decision

R2-WP02 completed (188 passed, 5 skipped). WP03 depends on WP02 only in the sense that
the query builder emits PubMed boolean strings; WP03 itself adds the execution layer.

### Delivered

- Added `app/integrations/pubmed/` following the existing `paperqa2/` adapter pattern:
  `client.py`, `schemas.py`, `exceptions.py`, `rate_limit.py`, `cache.py`, `__init__.py`.
- ESearch / ESummary / EFetch orchestration with:
  - API key + email support (`PubMedConfig`, `SecretStr` for the key, no hardcoding);
  - timeout (httpx, configurable), retry (3 attempts, exponential backoff, honors
    `Retry-After` on 429), rate limiting (`RateLimiter`, 350ms no-key / 100ms with key);
  - TTL cache keyed on normalized parameters (email/api_key/tool excluded);
  - structured exceptions deriving from `AppError`; no raw httpx/XML/JSON leakage;
  - request logging at debug/info level without exposing XML bodies or secrets.
- `PubMedRecord` with pmid/doi/title/authors/journal/year/abstract/publication_types plus
  `is_open_access` and `withdrawn` flags.
- Metadata normalization: complex author formats (collective authors, initials-only,
  missing name parts), missing year/abstract/journal degrade to `None`, withdrawn records
  detected via `CommentsCorrectionsList` `RefType="RetractionIn"`.
- XML parsing is namespace-agnostic (local-name matching) to tolerate NCBI returning both
  namespaced and plain `PubmedArticleSet` XML.
- Unit tests `tests/unit/test_pubmed_client.py` (Mock-based, no network) and live-gated
  integration tests `tests/integrations/test_pubmed_live.py` (`RUN_PUBMED_LIVE_TEST=1`).
- `.env.example` PubMed section clarified (key optional, email required).

### Verification status — VERIFIED（2026-08-05 Hermes 实测）

- `pytest tests/ -q` → **233 passed, 13 skipped**（完整后端套件，含 WP03 的
  `tests/unit/test_pubmed_client.py`）。
- 真实联网：`RUN_PUBMED_LIVE_TEST=1 pytest tests/integrations/test_pubmed_live.py`
  → **4/4 PASSED**（ESearch / ESummary / EFetch 真实调用 NCBI）。
- `mypy app/integrations/pubmed/` → Success（0 错误；已补 `asyncio` 导入、清理
  多余 `type: ignore`）。
- `ruff check app/ tests/` → All checks passed。

### WP03.5 — 医学 skills 融合（2026-08-05 完成）

两个融合动作已实现并提交（`824d367`），对应 `docs/SKILLS_FUSION_MAP.md`：

1. **文献检索反幻觉 + BibTeX 导出**（search-lit skill 融合）：
   - `literature_search` 新增结果持久化表（`literature_search_results`）、
     `pubmed_executor.py`（真实 EFetch 打标）、`bibtex.py`（BibTeX 序列化，
     key 规范 `FirstAuthor_Year_Word` + verified 字段）。
   - 新增 `POST /api/v1/literature-search/execute`、`GET /{id}/results`、
     `GET /{id}/bibtex`。
2. **引用核验子功能激活**（verify-refs skill 融合）：
   - 新增 `app/modules/citation_check/`（extractor → verifier → audit），
     前端 `CitationCheckView.vue` + `citationCheck.ts`，导航 `citation-check`
     设为可见（科研产出分组内）。
   - 验证：`RUN_CITATION_CHECK_LIVE_TEST=1` live 测试 **4/4 PASSED**
     （真实 PMID/DOI 标 true、伪造标 false）。
   - 前端 `npm run typecheck` / `npm run test`（19 passed）/ `npm run build` 全过。

### Known limitations / R2 backlog

- Rate limiting and backoff are in-process only (single process); multi-instance
  deployments need an external limiter.
- Cache is in-memory TTL; a restart clears it.
- `is_open_access` is inferred from the presence of a PMC id, not from a license check.

### Next boundary

Stop after R2-WP03.5. The next task is R2-WP04（检索任务与历史）; do not start it here.

## R2-WP04 — 检索任务与历史（2026-08-05 完成）

### Delivered

- `literature_search` 新增任务实体（original_query / structured_query / search_string /
  database / result_count / retmax / filters / model_version / user_edits / status 状态机），
  任务与 WP03.5 的 `LiteratureSearchResult` 通过 `literature_search_task_results` 关联表
  连接（保存结果引用而非复制 items_json，处理"历史记录过大"）。
- 端点：POST /literature-search（创建任务）、GET /literature-search（分页历史）、
  GET /literature-search/{id}（详情含版本）、POST /literature-search/{id}/rerun（重跑创建新版本）、
  GET /literature-search/{id}/strategy（检索策略导出）。
- 重跑创建新版本不覆盖旧版本；新旧版本结果数量变化生成 change 摘要。
- 前端 `History.vue` + 路由 /literature-search/history + API 客户端。
- Alembic 迁移 `c1d2e3f4a5b6`（literature_search_tasks + task_results）。

### Verification status — VERIFIED（2026-08-05 Hermes 实测）

- `pytest tests/ -q` → **240 passed, 13 skipped**（含 test_history.py 7 个新测试）。
- live 联网测试 → **8 passed**（PubMed + citation_check 真实 API）。
- `mypy app/modules/literature_search/` → Success（0 错误；修复 def list 遮蔽内置 list、
  status Literal 收窄、delete/get_task None 保护）。
- `ruff check app/ tests/` → All checks passed。
- 前端 `npm run typecheck` / `npm run test`（21 passed）/ `npm run build` 全过。
- `alembic upgrade head` 实测成功（a1b2c3d4e5f6 → c1d2e3f4a5b6）。

### Next boundary

Stop after R2-WP04. The next task is R2-WP05; do not start it here.

## R2-WP05 — 筛选、排序与分页（2026-08-05 完成）

### Delivered

- `filtering.py`：白名单筛选参数（year / publication_type / journal / author / has_abstract /
  saved / read_status / tags），未知参数拒绝，非法值 422。
- `ranking.py`：relevance（PubMed 默认序）/ newest / classic / custom 四种排序；classic 用
  可解释信号（权威期刊白名单 + verified + 近 5 年）替代被引量（不编造数据）；每条结果带
  sort_reason；年份缺失硬排最后；同分用 pmid 次级键稳定排序。
- `user_state.py` + `literature_search_item_state` 表：saved / read_status / tags / custom
  排序序号（manage-refs 融合：用户态与结果快照分离，不污染 items_json）。
- `GET /literature-search/{id}/results` 扩展筛选/排序/分页（服务端切片，避免整份下发）；
  用户态读写最小端点。
- 前端：LiteratureFilters 组件、PaperResults 分页组件、useLiteratureResults composable
  （筛选状态同步 URL query，刷新不丢失）、ResultsView 页。
- Alembic 迁移 `d3e4f5a6b7c8`（item_state 表）。

### Verification status — VERIFIED（2026-08-05 Hermes 实测）

- `pytest tests/ -q` → **261 passed, 13 skipped**（含 test_filters.py 21 个新测试）。
- live 联网测试 → **8 passed**（PubMed + citation_check 真实 API）。
- `mypy app/modules/literature_search/` → Success（16 源文件 0 错误；修复 None 处理、
  ReadStatus Literal 收窄）。
- `ruff check app/ tests/` → All checks passed。
- 前端 `npm run typecheck` / `npm run test`（26 passed）/ `npm run build` 全过。
- `alembic upgrade head` 实测成功（c1d2e3f4a5b6 → d3e4f5a6b7c8）。
- 修复记录：classic 排序 None 年份硬排最后；update_item_state 首次写入 None 崩溃；
  Vue readonly() 深度包装导致 readonly string[] 类型冲突；分页按钮当前页禁用。

### Next boundary

Stop after R2-WP05. The next task is R2-WP06; do not start it here.

## R2-WP06 — reversible literature deduplication

**Status:** complete

### Delivered

- Added reversible duplicate groups, members, and resolution audit records. Original
  `literature_search_results.items_json` and task/result associations are never modified or deleted.
- Matches prioritize PMID then normalized DOI; normalized title and first-author/year are fuzzy
  candidates requiring a human decision. Every group records the actual match method and confidence.
- Added `POST /literature-search/{id}/deduplicate`, `GET /duplicate-groups`, and
  `POST /duplicate-groups/{id}/resolve`; undo clears the merge decision and canonical pointers.
- Added a result-page review panel that renders only server-provided matching evidence and source task IDs.

### Known limitations

- Local single-user scope uses `local_user` as the default resolver identifier; multi-user identity
  and permission workflows remain out of scope.
- Title comparison is deliberately exact after normalization, not semantic similarity or translation inference.

### Verification

- Backend: `266 passed, 13 skipped` (`pytest tests/ -q`).
- Static checks: `mypy app/modules/literature_search/` passed; `ruff check app tests alembic` passed.
- Migration: upgrade head, downgrade to `d3e4f5a6b7c8`, then upgrade head all completed.
- Frontend: Vue typecheck passed; Vitest `27 passed`; production build passed.

### Independent verification（2026-08-05 Hermes 独立复测）

- `pytest tests/ -q` → **266 passed, 13 skipped**（真实输出，与 Codex 报告一致）。
- `mypy`（17 源文件）/ `ruff` / `alembic upgrade head` → 全部通过。
- 前端 `npm run typecheck` / `npm run test`（27 passed）/ `npm run build` → 全过。
- `dedup.py` 代码审查：纯函数设计、不可变 dataclass、匹配方法 Literal、不推断翻译标题——符合 CODE_STANDARDS.md。

### Next boundary

Stop after R2-WP06. The next task is R2-WP07; do not start it here.

## R2-WP07 — connect pubmed records to local library（保存论文与知识库衔接，2026-08-05 完成）

### Delivered

- `library_item` 模块（model/schema/service/router/repository）：正式收藏（区别于
  item_state.saved 的临时收藏，语义在注释说明）；保存元数据、绑定/解绑本地 PDF、
  分页列表 + 状态筛选。
- `document/matcher.py`：按精确 PMID/DOI 匹配本地文档（纯函数，无模糊匹配防误配）。
- 全文状态 enum：metadata_only / local_pdf_available / open_access_available / unavailable，
  带 fulltext_status_reason 可解释理由。
- 幂等保存：同 (pmid|doi) 返回已有记录。
- **版权边界（fulltext-retrieval 融合）**：保存不自动下载、不绕过付费墙；OA 状态仅基于
  可验证信号记录，无任何抓取逻辑。
- 前端 SaveToLibraryButton 组件 + 结果页"加入知识库"按钮。
- Alembic 迁移 `f5a6b7c8d9e0`（library_items 表）。

### Verification status — VERIFIED（2026-08-05 Hermes 独立复测）

- `pytest tests/ -q` → **269 passed, 13 skipped**（修复 test_database EXPECTED_TABLES 缺 library_items）。
- `mypy`（21 源文件）/ `ruff` → 全过（修复 Codex 遗留的 19 处 E701/E702 单行多语句，
  重命名 repository.list → list_items 避免遮蔽内置 list）。
- Alembic：upgrade head → downgrade → upgrade head 实测通过（可回滚）。
- 前端 `npm run typecheck` / `npm run test`（27 passed）/ `npm run build` 全过。
- Codex 自测（3 定向 passed + 前端）与 Hermes 复测一致；全量 pytest/mypy/ruff/迁移回滚由 Hermes 补齐。

### Next boundary

Stop after R2-WP07. The next task is R2-WP08; do not start it here.

## R2-WP08 — explainable reading-order recommendations（推荐阅读顺序，2026-08-05 完成）

### Delivered

- `reading_order.py`：纯函数规则分类器（review-paper 证据金字塔融合）——
  review → guideline → original_research → frontier → highly_relevant；
  分类依据 CitationItem.publication_types 真实字段；明确排除 "Journal Article"
  （PubMed 默认类型，不能作为一手研究判据）；不编造影响因子/被引量。
- 每篇解释：category / priority / reason / evidence_features（触发分类的真实特征）；
  search-lit 融合：相关度只用 verified + PMID 检索序。
- 人工顺序：manual_order 持久化（reading_order 表 + 迁移 f5c6d7e8f9a0），
  重新生成不覆盖人工顺序（order_source: rule/manual）。
- 端点：POST /literature-search/{id}/reading-order。
- 前端 ReadingPlan 组件（类别标签 + 优先序 + 理由 + 特征 + 手动调整）接入结果页。
- library_item.repository 新增 list_by_pmids（按 PMID 批量查全文状态，供阅读顺序用）。

### Verification status — VERIFIED（2026-08-05 Hermes 独立复测）

- `pytest tests/ -q` → **289 passed, 13 skipped**（含 test_reading_order.py 20 个新测试）。
- `mypy`（18 源文件）/ `ruff` → 全过（修复 order_source Literal 收窄、F401 未用 import、
  test_library_item.py 遗留 E701/E702 紧凑风格）。
- Alembic upgrade head 实测成功（f5a6b7c8d9e0 → f5c6d7e8f9a0）。
- 前端 `npm run typecheck` / `npm run test`（31 passed）/ `npm run build` 全过。
- Claude Code 执行 3 轮（每轮 60 轮上限），命令经 subagent 逃逸沙箱运行。

### Next boundary

Stop after R2-WP08. The next task is R2-WP09; do not start it here.

## R2-WP09 — notes mini-rag baseline（Mini-RAG 基线，2026-08-05 完成）

### Delivered

- `app/rag/`：notes_pipeline（NotesRAG 门面：index/search/save/load）、splitter（标题切片 +
  固定长度回退，滑动窗口 step=size-overlap）、embeddings（EmbeddingClient 抽象 +
  OllamaEmbeddingClient 本地优先 + DummyEmbeddingClient【开发用，确定性哈希向量】+
  create_embedding_client 工厂）、faiss_store（FAISS 存向量+vector_id，元数据独立
  metadata.json 双向映射，维度/损坏校验）、schemas（Chunk/RetrievalResult 含 source_path/heading）。
- **本地 embedding 优先（零成本+隐私）**：ollama 失败降级 dummy 而非云端（融合点）。
- **可解释引用**：检索结果携带 source_path + heading（反幻觉延伸）。
- **元数据边界**：FAISS 不存元数据，独立 JSON 回查（异常处理显式设计）。
- tests/rag/（40 个测试）+ experiments/minirag/（README + demo.py + 2 个中文样例笔记）。
- 环境：安装 faiss-cpu 1.15.0 + numpy 2.5.1（清华镜像，绕过代理）。

### Verification status — VERIFIED（2026-08-05 Hermes 独立复测）

- `pytest tests/ -q` → **329 passed, 13 skipped**（含 tests/rag 40 个新测试）。
- `mypy app/rag/` → Success（7 源文件；修复 _require_embedding/_require_store None 收窄）。
- `ruff check app/rag/ tests/rag/` → All checks passed（修复 7 个 F401）。
- 手工验证（真实运行）：索引 2 篇中文笔记 → 11 chunks；"EGFR 耐药机制"检索命中正确
  章节（带来源+heading+score）；保存索引 → 新实例加载 → 检索成功（round-trip）。
- 修复：runtime_checkable 未导入、load_index 未恢复 embedding、测试 mock json 解析、
  overlap 语义断言、loopback 消息断言。

### Next boundary

Stop after R2-WP09. The next task is R2-WP10; do not start it here.

## R2-WP10 — BM25 and hybrid retrieval baseline (completed 2026-08-06)

### Delivered

- Added `BM25Store`, which reuses WP09 `Chunk` metadata and applies deterministic medical tokenization: complete Latin/numeric tokens are case-folded (`EGFR`, `NCT04209660`), while Chinese runs use character bigrams for out-of-vocabulary medical terms such as 奥希替尼. No jieba dependency was added.
- Added `VectorRetriever` adapter over the existing `FaissIndexStore`; it and `BM25Store` expose the same text-search shape and accept injected query embedding/index dependencies.
- Added rank-only Reciprocal Rank Fusion (`1 / (60 + rank)`), with `chunk_id` de-duplication. Raw FAISS distances and BM25 scores are never added directly.
- Extended retrieval records with `chunk_id`, retriever name, rank, raw score, fused score, and per-route contributions. `HybridRetriever` can append one JSONL record per query with both Top-K lists and fused results.
- Added `experiments/retrieval_baseline/`: fixed, auditable questions over the existing WP09 local sample notes; the runner saves per-strategy results plus Recall@K and MRR.

### Verification

- TDD RED: before implementation, `pytest tests/rag/test_rrf.py tests/rag/test_bm25.py tests/rag/test_hybrid.py -q` failed collection because the three target modules did not exist.
- TDD GREEN: after implementation, the initial targeted suite passed (`15 passed`); the final targeted suite passed (`17 passed`) and the RAG suite passed (`57 passed`).
- Full backend suite: `348 passed, 13 skipped` (`pytest -q`; one pre-existing FastAPI/httpx deprecation warning).
- Ruff: `ruff check app/rag tests/rag experiments/retrieval_baseline` passed.
- Baseline runner was executed and saved results to ignored `data/retrieval_baseline.json` and JSONL trace. With Dummy embedding its vector/hybrid scores are not semantic-quality evidence; BM25 exact-term behavior is covered by unit tests.
- No persistence model changed, so no Alembic revision was created. `alembic check` remains non-green because it detects pre-existing `library_items` DOI/PMID index uniqueness drift; this WP does not touch those models or migrations.

### Known limitations / next boundary

- `rank_bm25` is declared as an optional dependency but was not importable in the specified Python environment; BM25 is therefore implemented with the standard-library formula rather than adding an unverified installation step.
- The baseline uses WP09 Dummy embeddings for offline reproducibility. A valid semantic vector/hybrid quality comparison requires the same manually labelled question set with a verified local Ollama embedding; it must not be replaced with a cloud fallback.
- Stop after R2-WP10. The next task is R2-WP11; do not start it here.

## R2-WP10 — bm25 and hybrid retrieval baseline（BM25 与混合检索，2026-08-06 完成）

### Delivered

- `app/rag/bm25_store.py`：BM25 索引（build/add，追加后重算全局统计量防 IDF 失真）；
  医学分词——英文/数字 token 保留原样（egfr/nct04209660）+ 中文确定性 2-gram（不新增 jieba 依赖）。
- `app/rag/rrf.py`：RRF 纯函数融合（k=60，按排名融合，FAISS 距离与 BM25 分数不直接相加）。
- `app/rag/hybrid_retriever.py`：FAISS + BM25 双路 + RRF + chunk_id 去重 + JSONL 检索日志。
- `app/rag/vector_retriever.py`：WP09 FAISS 适配为与 BM25 同接口（可切换对比）。
- `schemas.py` 扩展：RetrievalResult 加 retriever_name/rank/raw_score/fused_score + RetrievalContribution。
- `experiments/retrieval_baseline/`：固定问题集（3 题，含 EGFR/NCT 编号）+ 对比脚本 +
  README；结果落盘 data/retrieval_baseline.json + .retrieval.jsonl。
- **Skills 融合**：pytest-skill（fixture/parametrize）、TDD（RED→GREEN 记录）、
  systematic-debugging（根因修复）、coding-agent-cli-execution（方法名不遮蔽内置/
  无 E701-E702/无探针残留）、simplify-code（复用 WP09 faiss_store/embeddings）。

### Verification status — VERIFIED（2026-08-06 Hermes 独立复测）

- `pytest tests/ -q` → **348 passed, 13 skipped**（含新 19 个测试：bm25/rrf/hybrid）。
- `mypy app/rag/` → Success（11 源文件）；`ruff` → All checks passed。
- 基线实验真实运行：vector recall@3=0.167/MRR=0.111（dummy 非语义，README 已标注）、
  **bm25 recall@3=1.000/MRR=1.000**（精确医学词完美命中）、hybrid recall@3=0.833/MRR=0.611。
- **修复 alembic 漂移（WP07 遗留）**：library_items 的 doi/pmid 索引 model 声明 unique=True
  但迁移只建普通索引 → 新迁移 ee5f23856af4 重建 unique 索引；`alembic check` 通过
  （No new upgrade operations）；upgrade 实测成功。
- 未执行：前端（纯后端）、Ollama 真实 embedding 集成（RUN_OLLAMA_EMBEDDING_TEST 门控）。

### Next boundary

Stop after R2-WP10. The next task is R2-WP11; do not start it here.

## R2-WP11 — 多论文比较（2026-08-06 完成）

### Delivered

- 完成真实比较矩阵前端：按字段行、按论文列展示 `cell_value`、可追溯 `sources`、生成/人工修订/缺失状态；研究类型行以视觉标识突出，单元格提供人工修订入口。
- 比较页从原型切换为 LIVE，使用已有 `/comparisons` 路由与 feature 预留位；用户输入 3 至 10 个已保存文档 ID 创建任务，任务 ID 保留在 URL query 中。
- 新增 `GET /comparisons/{id}/export?format=csv|markdown`。导出来自服务端持久化比较矩阵，CSV 和 Markdown 均不杜撰缺失值。
- 添加 TestClient 全链路集成测试：创建、读取、编辑、重新生成（人工值保留）和 CSV/Markdown 导出。

### Verification

- 定向后端：`pytest tests/modules/comparison/test_comparison_api.py tests/unit/test_comparison_service.py -q` — `6 passed`（1 个现有 FastAPI/httpx 弃用警告）。
- 定向 Ruff：`ruff check app/modules/comparison tests/modules/comparison tests/unit/test_comparison_service.py` — `All checks passed!`。
- 前端：`npm run typecheck` 通过；`npm run test` — `20 passed / 31 passed`；`npm run build` 通过。

### Independent verification（2026-08-06 Hermes 复测）

- `pytest tests/ -q` → **354 passed, 13 skipped**（全量，含 comparison 新测试）。
- `mypy app/modules/comparison/` → Success（6 源文件）；`ruff check app/modules/comparison/` → All checks passed。
- `alembic check` → No new upgrade operations（模型-迁移一致）。
- 代码审查：review-paper 反幻觉落地——无 source_indices 锚点的字段返回缺失（不编造）；
  user_value 优先；研究类型行标注；FIELD_MAPPING 语义化；无紧凑风格残留。

### Next boundary

Stop after R2-WP11. The next task is R2-WP12; do not start it here.

## R2-WP12 — editable evidence matrix（证据矩阵，2026-08-06 完成，后端）

### Delivered

- `app/modules/evidence_matrix/`：EvidenceMatrix/MatrixDocument/MatrixField/MatrixCell
  4 表规范化存储（避免 JSON 大字段后期难迁移）；CRUD + 增删论文 + 字段管理 +
  单元格编辑 + 版本化 + 导出 CSV/Markdown。
- **manage-refs 融合**：user_notes 独立存储、topic_relevance/reading_status/document_status
  独立枚举字段（unread/reading/read、included/pending、low/medium/high）。
- **verify-refs 融合**：sources 绑定真实 PMID/DOI；无来源值标 missing 而非"已验证"；
  provenance=model/manual 区分。
- **review-paper 融合**：缺失显式标注（MISSING_VALUE），不编造数据；字段软删除
  （active=False，单元格保留供版本回溯）；regenerate 只更新 generated 格，
  user_edited 保留，version 递增。
- `app/modules/comparison/shared.py`：从 comparison 抽取共享常量（MISSING_VALUE/
  DEFAULT_FIELDS/FIELD_MAPPING/ComparisonField/SourceRef），WP11+WP12 复用。
- Alembic 迁移 c7d8e9f0a1b2（evidence matrix 4 表）。
- 前端：**跳过**（用户决策：全部前端推倒重做，WP12+ 前端不着急做）。

### Verification status — VERIFIED（2026-08-06 Hermes 独立复测）

- `pytest tests/ -q` → **363 passed, 13 skipped**（含 test_evidence_matrix_service.py 9 个新测试：
  CRUD/字段增删不丢数据/论文 3-10 边界/备注隔离/版本递增/CSV 转义/人工值保留）。
- `mypy app/modules/evidence_matrix/ app/modules/comparison/` → Success（14 源文件）。
- `ruff` → All checks passed。
- `alembic upgrade head` 实测（b6f9a1c3d7e2 → c7d8e9f0a1b2）；`alembic check` → No new ops。
- 修复（Hermes 验证发现）：service `def list` 遮蔽内置（改 list_matrices）、
  `_active_field_keys` 忘 await、repository.list_fields 未过滤软删除字段、
  MISSING_VALUE 错误 import 路径（comparison.service + evidence_matrix.service +
  WP11 测试）、StrEnum 未收窄（4 处）、缺 import（MatrixDocumentUpdate 等）、
  ruff F401/F841（12 处）。

### Next boundary

Stop after R2-WP12. The next task is R2-WP13; do not start it here.

## R2-WP13 — 真实用户检索验收（2026-08-07 文档产出；真实试用待执行）

### 交付

- `docs/R2_USER_TEST_SCRIPT.md`：9 步固定任务（输入方向 → 生成检索式 → 检索 PubMed →
  筛选 → 去重 → 保存 5 篇 → 阅读顺序 → 比较 3 篇 → 导出证据矩阵），每步含可执行操作、
  预期结果、API 入口、记录字段与耗时栏；附 PICO 示例方向与参考检索式、错误处理指引、
  完成率定义。
- `docs/R2_USER_TEST_REPORT.md`：报告模板，含执行记录表、每步记录表、验收判定、缺陷分类
  （阻塞/严重/一般）、完成条件；明确当前「待执行」，不填写虚构完成率。
- `docs/R2_ACCEPTANCE.md`：验收标准逐条（结果相关性 / 检索式可理解 / 去重准确 /
  矩阵可用于实际工作），每条含判定标准、证据要求、结论栏与签署栏；附附加核验项
  （5 篇 PMID/DOI 真实可解析，verify-refs 融合）。
- `docs/R3_BACKLOG.md`：基于代码审查与现有状态文档的增强点/越界需求清单（不虚构），
  分三类：R2 明确缺陷（2 项）、R2 已知限制/增强点（9 项）、越界需求（6 项登记不实施）。

### 前端执行检索功能修复（含测试）

执行检索功能此前缺前端驱动，用户在 `/literature-search` 无法把构建的检索式真正提交为
PubMed 检索任务。本轮完成修复：

- `frontend/src/composables/useSearchTerms.ts`：新增 `createTask`（封装
  `POST /literature-search`，错误返回 `null` 并暴露 `taskLoading/taskError`；空检索式不发起请求）。
- `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`：新增「执行 PubMed 检索」区块
  （保存本地草稿 / 复制检索式 / 执行检索），`runSearch` 以原始主题为 `original_query`、
  检索式为 `search_string` 提交任务，成功后跳转结果页。
- `frontend/src/views/LiteratureSearch/History.vue`：「查看结果」链接带 `?task=任务ID`，
  供结果页区分任务 ID 与结果 ID。
- `frontend/src/views/LiteratureSearch/ResultsView.vue`：去重调用优先使用 `?task=` 参数，
  缺失时回退 `resultId`（已知边界，见 `docs/R3_BACKLOG.md` 缺陷 1）。
- `frontend/src/views/LiteratureSearch/LiteratureSearchView.test.ts`：新增「执行检索」全链路
  组件测试（解析 → 扩展 → 构建 → 执行 → 跳转结果页），断言 `POST /literature-search`
  被调用且路由跳转至 `/literature-search/results/{latest_result_id}`。

### 状态

- **文档与前端修复已落地；未运行任何命令。**
- 前端 typecheck / Vitest / build、后端回归、真实用户 9 步试用均**待执行**【未实测】；
  按规范不声称通过。
- 真实试用执行并记录脱敏证据后，将 `docs/R2_USER_TEST_REPORT.md` 状态改为「完成」并
  签署 `docs/R2_ACCEPTANCE.md`。

### Next boundary

Stop after R2-WP13 文档与前端修复。下一步：执行真实用户 9 步试用并填写
`docs/R2_USER_TEST_REPORT.md`，完成 WP13 验收与签署；不得开始 R3。
