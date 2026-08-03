# Frontend page state matrix (FE-00)

| Page / capability | Primary state | Data source | Empty / failure / pending policy |
|---|---|---|---|
| Workbench | MOCK | Typed mock adapter for recent activity only | Clearly label prototype data; no invented papers or metrics. |
| Knowledge sources | LIVE | Knowledge-source APIs | Empty registration state, unavailable-path state, sync failure and retry states. |
| Document library | LIVE | Document APIs | Empty list, loading, parse/index failure, partial batch-index success, pagination. |
| Document detail | LIVE | Document read/content-summary APIs | Not found, parsing/indexing, missing content, retry action. |
| Paper analysis | LIVE | Paper-analysis APIs | Pending/analyzing/failed/succeeded; preserve source evidence and pending confirmations. |
| Evidence Q&A | LIVE | Conversation APIs | No-answer, uncertainty, citations absent, model failure, empty conversation. |
| Literature search builder | LIVE | Parse / expand / build-query APIs | Model fallback, MeSH unavailable, invalid user term, editable term/query state. |
| PubMed results | UNAVAILABLE | No backend API | “Awaiting R2-WP03” only; optional visual prototype must be typed MOCK and cannot claim fetched results. |
| Multi-paper comparison | MOCK | Typed mock adapter | Prototype label; no fake DOI/PMID/page/statistics. |
| Evidence matrix | MOCK | Typed mock adapter | Prototype label and source placeholders, never factual medical evidence. |
| Research directions | NEEDS_CONFIRMATION | Stub router exists | Do not call LIVE until schemas and acceptance are confirmed. |
| Group report / writing | UNAVAILABLE | No project/task writing API | Entry and empty “awaiting integration” state only. |
| Task center | UNAVAILABLE | No task API | No fake progress or task completion. |
| Settings | LIVE (model settings), MOCK (shell preferences) | Model-config APIs | Cost acknowledgement, privacy warning, connection failure. |
| Agent lab | UNAVAILABLE | No Agent API | Explicit unavailable state. |
| Evaluation center | NEEDS_CONFIRMATION | Stub router exists | Do not present evaluation results as real. |
