# Workspace V2 current-difference remediation traceability

| AC | Evidence | Result |
| --- | --- | --- |
| AC-FIX-01 | `SearchEntryView.test.ts`; running API pipeline test | covered |
| AC-FIX-02 | `failure-baseline.png` retained separately from target fixture | covered |
| AC-FIX-03 | `geometry-report.json`: Sidebar 229px, Header x=229 | covered |
| AC-FIX-04 | 1536 screenshot and geometry sections | covered |
| AC-FIX-05 | `StrategyWorkspaceV2.test.ts`; fixture screenshot step 3 | covered |
| AC-FIX-06 | `SearchCenterHeader.vue` derives real version list | covered |
| AC-FIX-07 | `StrategyTermsMeshSection.vue`: three compact concept-group rows, action menu/dialog, warning and five MeSH split rows | covered |
| AC-FIX-08 | `visual-test-only/workspace-v2.fixture.mjs` 24 terms / 10 MeSH / v3 | covered |
| AC-FIX-09 | geometry report Query y=739, status panels y=857 | covered |
| AC-FIX-10 | geometry report Sticky y=937, h=79 | covered |
| AC-FIX-11 | manual view of regenerated 1536 screenshot + overlay | covered; internal spacing differences disclosed |
| AC-FIX-12 | running local API parse/expand/build/create/recover verified | covered |
| AC-FIX-13 | six viewport capture runner | captured |
| AC-FIX-14 | static import scope: fixture only imported by capture script | covered |
| AC-FIX-15 | screenshots, overlay, diff, geometry files and manual image view | covered |
| AC-FIX-16 | 2026-08-23 final rerun: 60 frontend test files / 157 tests, typecheck, scoped ESLint, build, `git diff --check` | covered |
