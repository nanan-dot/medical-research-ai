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
