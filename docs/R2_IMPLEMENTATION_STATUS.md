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
