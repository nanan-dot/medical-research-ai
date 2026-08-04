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

### Verification status — PENDING

- pytest for the new files could not be executed in this session: every external program
  invocation (`python`, `pytest`, `bash`, `cmd`, project venv python) was blocked by the
  session permission system ("requires approval") before it could run.
- This document is updated WITHOUT claiming test results. Tests must be run and the
  results recorded here before the work package is considered accepted.
- Static review of the new code was performed; no claims of runtime verification are made.

### Known limitations / R2 backlog

- Rate limiting and backoff are in-process only (single process); multi-instance
  deployments need an external limiter.
- Cache is in-memory TTL; a restart clears it.
- `is_open_access` is inferred from the presence of a PMC id, not from a license check.

### Next boundary

Stop after R2-WP03. The next task is R2-WP04; do not start it here.
