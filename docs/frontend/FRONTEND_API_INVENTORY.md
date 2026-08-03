# Frontend API inventory (FE-00)

Status terms: **LIVE** is registered in the FastAPI application and covered by repository tests or current implementation status. **UNAVAILABLE** has no registered API. No endpoint below is inferred from a planned feature.

| Frontend feature | Method | Path | Request schema | Response schema | Status | Evidence |
|---|---|---|---|---|---|---|
| Health / capability probe | GET | `/api/v1/health` | — | `HealthStatus` | LIVE | `app/modules/health/router.py` |
| Model settings | GET, POST, DELETE | `/api/v1/model-configs[/{id}]` | `ModelConfigCreate` | `ModelConfigRead` | LIVE | `app/modules/model_config/router.py`, `schema.py` |
| Model connection test | POST | `/api/v1/model-configs/{id}/test` | `ConnectionTestRequest` | `ConnectionTestResult` | LIVE | `app/modules/model_config/router.py` |
| Knowledge sources | GET, POST, PATCH, DELETE | `/api/v1/knowledge-sources[/{id}]` | `KnowledgeSourceCreate`, `KnowledgeSourceUpdate` | `KnowledgeSourceRead` | LIVE | `app/modules/knowledge_source/router.py`, `schema.py` |
| Knowledge-source sync | POST, GET | `/api/v1/knowledge-sources/{id}/sync[-status]` | — | `KnowledgeSourceSyncSummary` | LIVE | `app/modules/knowledge_source/router.py` |
| Document library | GET | `/api/v1/documents` | query `offset`, `limit`, filters | `DocumentPage` | LIVE | `app/modules/document/router.py`, `schema.py` |
| Document processing | POST, DELETE | `/api/v1/documents/{id}/parse`, `/index`, retry paths | — | `DocumentRead` / `DocumentIndexResult` | LIVE | `app/modules/document/router.py` |
| Paper analysis | POST, GET, PATCH | `/api/v1/paper-analysis[/{id}]` | `PaperAnalysisCreate`, `PaperAnalysisCorrection` | `PaperAnalysisRead` | LIVE | `app/modules/paper_analysis/router.py`, `schema.py` |
| Evidence Q&A | GET, POST, DELETE | `/api/v1/conversations[/{id}]` and message paths | `ConversationCreate`, `MessageCreate`, `FeedbackCreate` | `ConversationRead`, `MessageRead` | LIVE | `app/modules/conversation/router.py`, `schema.py` |
| Literature intent | POST | `/api/v1/literature-search/parse-query` | `ParseQueryRequest` | `ParseQueryResponse` | LIVE | `app/modules/literature_search/router.py`, `schema.py` |
| Terms / MeSH / query | POST | `/api/v1/literature-search/expand-terms`, `/build-query` | `ExpandTermsRequest`, `BuildQueryRequest` | `ExpandTermsResponse`, `BuildQueryResponse` | LIVE | `app/modules/literature_search/router.py`, `schema.py` |
| PubMed result list | — | — | — | — | UNAVAILABLE | No PubMed router/client; R2 status limits work to WP02. |
| Comparison / evidence matrix | GET only | `/api/v1/research-direction`, `/evaluation` | — | currently untyped stub responses | NEEDS_CONFIRMATION | Routers exist, but no feature-specific schemas or acceptance record. |
| Writing projects / task center / Agent runs | — | — | — | — | UNAVAILABLE | `writing` is a CRUD stub; no task or Agent API is registered. |

## Cross-cutting findings

- API base is `/api/v1`; Vite proxies `/api` to `http://127.0.0.1:8000` (`frontend/vite.config.ts`).
- OpenAPI is reusable at `/openapi.json` while `DEBUG=true`; `app.main` enables `/docs` only in debug mode.
- App errors use `{ "error": { "code", "message" } }` (`app/common/exception_handlers.py`). Validation errors retain FastAPI's `detail` format, which the existing `apiRequest` client also supports.
- Offset/limit pagination is implemented for documents through `DocumentPage`; other list APIs use arrays or need endpoint-specific review.
- No durable asynchronous task API exists. Document states are real state fields, not a task queue. Treat generic task-center progress as MOCK/UNAVAILABLE until an API is registered.

## FE-08 addendum

- `/tasks` is LIVE only within the bounded document-status scope: it calls the existing document list and retry endpoints, and does not claim a generic asynchronous task queue.
- No project-writing, Agent-run, or evaluation-run endpoint is registered. Their frontend pages remain MOCK/UNAVAILABLE as described in `FRONTEND_MOCK_BOUNDARIES.md`.
- CORS is configured through `settings.CORS_ORIGINS` in `app/main.py`; `.env.example` does not declare a CORS value. Same-origin Vite proxy works in development; deployed cross-origin frontend requires confirmation/configuration.
