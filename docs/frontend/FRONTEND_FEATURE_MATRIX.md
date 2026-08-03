# Frontend feature-state matrix (FE-08)

| Page / capability | State | Data source | Boundary |
|---|---|---|---|
| Workbench | MOCK | Typed local adapter | No fabricated papers or metrics. |
| Knowledge sources / documents | LIVE | Registered APIs | Loading, empty, failure, retry and pagination remain visible. |
| Paper analysis / evidence Q&A | LIVE | Registered APIs | Evidence and pending confirmation remain explicit. |
| Literature builder | LIVE | Parse/expand/build-query APIs | PubMed result list remains unavailable until R2-WP03. |
| Comparison / evidence matrix | MOCK | Typed local adapter | Demo papers only; no DOI, PMID, statistics, or factual evidence. |
| Research directions / presentations / writing | MOCK | Typed local adapters | Candidate and local-draft surfaces only; no final decisions or generated academic content. |
| Task center | LIVE (bounded) | Document list and retry APIs | Document parse/index state only; no generic queue. |
| Settings | LIVE / UNAVAILABLE | Model-config and health APIs | Other categories do not fabricate diagnostics; keys are masked. |
| Agent lab / evaluation center | MOCK | Typed local prototypes | R4 boundary; no LangGraph, tool, runner, score, or medical result. |
| Citation check / reading plan | UNAVAILABLE | No registered API | State clearly directs users to later integration. |
