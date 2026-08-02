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
