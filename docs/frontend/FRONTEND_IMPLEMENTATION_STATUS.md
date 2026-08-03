# Frontend implementation status

## FE-00 — repository audit and implementation plan

**Status:** complete

- Reviewed AGENTS, README, Python/frontend manifests, environment template, migrations, FastAPI registration, schemas, R1/R2 records, frontend source tree, current git status and visual reference.
- Verified current frontend is Vue 3 + TypeScript + Vite + Vue Router + Vitest using npm. Pinia, Tailwind, a store directory, and formal design tokens are not currently present.
- Inspected `docs/design/医学科研智能平台界面总览.png`: the intended composition is stable left navigation, central paper-like workspace, and a shared right evidence/context rail.
- Recorded verified APIs in `FRONTEND_API_INVENTORY.md`, state boundaries in `FRONTEND_FEATURE_MATRIX.md`, and FE-01—FE-08 scope in `FRONTEND_IMPLEMENTATION_PLAN.md`.

### Deliberately not done

- No business page, backend route, database migration, mock medical record, or dependency installation was added.
- No browser end-to-end interaction was performed because FE-00 is a repository audit/documentation task.

### Next task

FE-01 only.

## FE-01 — Design system and application shell

**Status:** complete

- Added reusable tokens and base styles for the deep-navy navigation, paper-like workspace, evidence colours, focus states, and reduced-motion preference.
- Added a componentized app shell: collapsible desktop sidebar, top tool bar, breadcrumbs, global-search entry, quick-create menu, mobile drawer, and route-aware context rail.
- Added typed feature registry and route metadata with honest `LIVE`, `MOCK`, and `UNAVAILABLE` labels. Future paths use a single explicit unavailable shell rather than fabricated business pages.
- Kept existing business views and backend APIs intact; no database, backend, or dependency changes were made.

### Verification

- `npm run typecheck` passed.
- `npm test -- --run` passed (14 tests).
- `npm run build` passed.

### Next task

FE-02 only.

## FE-02 — workbench, knowledge sources, and document workflows

**Status:** complete

- Reworked the workbench into a clear next-action surface. Live knowledge-source health is separated from explicitly labelled MOCK task and UNAVAILABLE research-question capability; no fabricated papers or task progress are shown.
- Connected knowledge-source list, enablement, removal, and manual synchronization to the existing LIVE API. Source path, type, synchronization state, time, and returned errors remain visible; removing a record is stated not to remove original files.
- Connected document filtering and retry operations to the existing LIVE API, added typed batch-index calls and selection, and added a route to a real document-detail record.
- Added a document-detail state surface for returned metadata, parse/index retries, summaries, scanned-PDF OCR limitation, errors, and original-file safety. Original-file opening is explicitly UNAVAILABLE.
- Tightened page title density after visual comparison with the supplied product board while retaining the deep-navy navigation, paper workspace, primary blue, and restrained evidence status colours.

### Verification

- `npm test -- --run` passed (14 tests).
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev --audit-level=high` found 0 vulnerabilities.
- Browser visual inspection completed for the workbench and document library at the local preview URL.

### Next task

FE-03 only.

## FE-05 — multi-paper comparison and evidence-matrix prototypes

**Status:** complete

- Added the `/comparisons` and `/evidence-matrix` prototype pages through one typed front-end mock adapter. They use only 演示论文 A/B/C; no DOI, PMID, authors, statistics, or real medical conclusions are represented.
- Comparison supports the requested study fields, horizontal scrolling, a frozen field column, missing-value warning, and local manual cell edits. Manual edits remain visibly distinct from unavailable source evidence.
- Evidence matrix supports prototype version/actions, current-cell context, source status, and local user notes. No data is sent to or read from a backend.
- Both pages use their own context area rather than duplicating the application-level evidence rail, and retain the established deep-navy navigation, paper workspace, primary blue, and restrained warning treatment.

### Verification

- `npm run typecheck` passed.
- `npm test -- --run` passed (15 tests).
- `npm run build` passed.
- Browser visual inspection completed for the comparison and evidence-matrix pages at the local preview URL.

### Next task

FE-06 only.

## FE-06 — research directions, presentations, and writing prototypes

**Status:** complete

- Added the research-context and candidate-direction prototype at `/research-directions`. All twelve unknown conditions remain explicit, and candidates are framed as discussion inputs rather than authoritative decisions.
- Added a standalone high-frequency presentation workspace at `/presentations`, including five new-draft types, local draft list actions, candidate-direction handoff, and `/presentations/:id` editor with outline, speaker notes, discussion questions, source status, and explicit evidence gaps.
- Added writing-project and writing-editor prototypes at `/writing` and `/writing/:id`, including local draft/version surfaces, content-origin markers, and visibly unavailable citation/original-text/AI-usage states.
- All FE-06 records are type-safe front-end mocks; no backend route, fabricated paper, DOI/PMID, experiment result, ethical approval, or claim of generated academic content was added.

### Verification

- `npm run typecheck` passed.
- `npm test -- --run` passed (18 tests).
- `npm run build` passed.
- Browser visual inspection completed for research directions, presentations, and writing pages at the local preview URL.

### Next task

FE-07 only.

## FE-07 — tasks, settings, Agent lab, and evaluation center

**Status:** complete

- Added `/tasks` as a bounded LIVE task view backed exclusively by the existing document-list and retry APIs. It shows parse/index state, timestamps, retry count, and returned errors; it does not claim a generic background queue.
- Reworked `/models` into a settings center using the existing model-config and health APIs. Cloud authorization remains explicit and API keys are password-input only, cleared after saving, and only server-provided masked values are rendered.
- Added `/agent` and `/evaluation` as R4 MOCK prototypes. Both visibly state that no runner is connected and contain no model, tool, evaluation, or medical-result execution.
- Added feature-state coverage for LIVE task boundary and MOCK Agent/evaluation boundary. No LangGraph, evaluation backend, or new API endpoint was added.

### Verification

- `npm run typecheck` passed.
- `npm test -- --run` passed (19 tests).
- `npm run build` passed.
- `npm audit --omit=dev --audit-level=high` found 0 vulnerabilities.
- Browser visual inspection completed for task center, settings, Agent lab, and evaluation center at the local preview URL.

### Next task

FE-08 only.

## FE-08 — mobile, validation, build, and delivery documentation

**Status:** complete

- Added a keyboard-visible skip link to the application shell, unified focus-visible treatment across controls, and retained reduced-motion support.
- Converted route components to lazy imports. The production build now emits route-level chunks and keeps the initial script separate from individual feature pages.
- Audited existing responsive behavior: navigation uses the mobile drawer below 900px; context rails and three-column workspaces collapse at their declared breakpoints; comparison/matrix preserve horizontal table access rather than compressing data into misleading cards.
- Added the delivery README, architecture, route map, mock-boundary, test, and accessibility reports; updated feature-state and API inventories to match the final FE-01—FE-07 implementation.

### Verification

- `npm run typecheck` passed.
- `npm test -- --run` passed (19 tests).
- `npm run build` passed with route-level chunks.
- `npm audit --omit=dev --audit-level=high` found 0 vulnerabilities.
- Browser visual inspection completed. The current browser-control surface does not expose programmable viewport sizing, so the five requested independent device screenshots remain documented as a follow-up instead of being misreported as completed.

### Final status

FE-01 through FE-08 front-end scope is complete. No additional front-end or backend phase was started.
