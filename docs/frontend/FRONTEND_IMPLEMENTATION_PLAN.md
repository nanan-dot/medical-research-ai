# FE-01—FE-08 implementation plan

## Shared architecture decisions

Use Vue 3 Composition API, TypeScript, Vue Router and the existing `apiRequest` layer. FE-01 will decide whether Pinia/Tailwind are needed after assessing dependency and migration impact; they are not current repository dependencies. Separate `api/`, feature types, composables/adapters, focused components, and route views. A single feature-status registry will distinguish LIVE, MOCK, and UNAVAILABLE.

## FE-01 — Design system and application shell

- **Goal:** tokens, responsive app shell, navigation, top bar, shared right evidence/context rail, status badges.
- **Dependencies:** none for shell; health/model information may be LIVE where useful.
- **LIVE/MOCK/UNAVAILABLE:** only shell states and model/privacy display use LIVE; future route entries retain their matrix status.
- **Files:** create design tokens, layout/navigation/context components, feature-status types; modify `App.vue`, global styles and router.
- **Tests:** route/status badge, responsive navigation, keyboard/focus behavior; typecheck, Vitest, build.
- **Risk / acceptance:** avoid replacing working pages; desktop/tablet/mobile shell works and no future feature is labelled LIVE.

## FE-02 — Workbench, sources, documents, document detail

- **Goal:** implement first operational workflow using existing source and document APIs.
- **Dependencies:** knowledge-source and document APIs.
- **LIVE:** source registration/sync, document list/detail/retry/index states. **MOCK:** workbench recent activity. **UNAVAILABLE:** cross-process task progress.
- **Files:** feature adapters/composables and focused source/document/workbench views; modify route registration.
- **Tests:** loading/empty/error/partial-success states and API adapter mapping.
- **Risk / acceptance:** destructive actions retain source-file safety copy; pagination and retry behavior match schemas.

## FE-03 — Paper analysis and evidence Q&A

- **Goal:** evidence-first analysis and conversation screens with shared context rail.
- **Dependencies:** paper-analysis and conversation APIs.
- **LIVE:** analysis status/corrections/export and cited Q&A/no-answer. **MOCK:** none required. **UNAVAILABLE:** unsupported cross-paper synthesis.
- **Files:** analysis, conversation, citation/context components and adapters; modify relevant views/routes.
- **Tests:** citations, no-answer/uncertainty, pending/failed analysis, feedback.
- **Risk / acceptance:** never render unsanitized evidence HTML; all factual UI values retain source/status context.

## FE-04 — R2-WP01/WP02 literature search builder

- **Goal:** redesign the existing LIVE intent, term, MeSH, and query workflow within the shared shell.
- **Dependencies:** three literature-search POST APIs.
- **LIVE:** request parsing, editable terms, source-labelled MeSH candidates, boolean query. **MOCK:** optional clearly-labelled result preview only. **UNAVAILABLE:** real PubMed retrieval.
- **Files:** preserve/rework literature-search feature components and adapter; modify only their route integration.
- **Tests:** edit preservation, fallback, MeSH empty/error, invalid term, query explanation.
- **Risk / acceptance:** never show mock papers as retrieved PubMed results; a visible R2-WP03 boundary remains.

## FE-05 — Comparison and evidence-matrix prototypes

- **Goal:** high-fidelity prototype layouts for later multi-paper workflows.
- **Dependencies:** none; no assumed backend.
- **LIVE:** none. **MOCK:** typed synthetic structural rows only. **UNAVAILABLE:** saving, import, synthesis, real evidence.
- **Files:** typed mock adapters, comparison/matrix route views and reusable table/context components.
- **Tests:** prototype badge, no factual identifiers, responsive tables.
- **Risk / acceptance:** data is visibly simulated and cannot be persisted or exported as research output.

## FE-06 — Research directions, group report, writing prototypes

- **Goal:** planning-oriented UI and group-report entry without fabricated research outputs.
- **Dependencies:** research-direction router requires confirmation; no writing project API.
- **LIVE:** none until schema/API review. **MOCK:** typed planning form shells. **UNAVAILABLE:** generation, reporting, saving.
- **Files:** prototype adapters and dedicated views/components.
- **Tests:** status presentation and disabled unavailable actions.
- **Risk / acceptance:** no generated claims, proposals, or fake source evidence.

## FE-07 — Tasks, settings, Agent, evaluation

- **Goal:** integrate real model settings and define honest status surfaces for unavailable capabilities.
- **Dependencies:** model-config API; evaluation/research routers need confirmation.
- **LIVE:** model configuration and connection test. **MOCK:** non-persistent UI preferences only. **UNAVAILABLE:** task queue and Agent execution.
- **Files:** settings adapters/components, unavailable panels, status registry integration.
- **Tests:** cloud consent, masking, test failure, unavailable actions.
- **Risk / acceptance:** never expose keys; cost acknowledgement remains mandatory.

## FE-08 — Mobile, accessibility, final test/build, documentation

- **Goal:** responsive refinement, accessibility pass, replacement map for mock adapters, delivery docs.
- **Dependencies:** FE-01—FE-07 artifacts.
- **LIVE/MOCK/UNAVAILABLE:** audit and preserve all labels.
- **Files:** targeted style/test/docs updates only.
- **Tests:** keyboard navigation, viewport coverage, full Vitest/typecheck/build/audit.
- **Risk / acceptance:** all supported pages remain usable at mobile widths and the final status document identifies every mock boundary.
