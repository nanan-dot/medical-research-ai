# Literature search workspace V2 acceptance traceability

| AC | Verifiable evidence | Current result |
| --- | --- | --- |
| AC-V2-01 | `LiteratureSearchView.test.ts` restores `strategy_id`; `useSearchStrategy.ts` GET contract | automated pass |
| AC-V2-02 | `AppSidebar.test.ts`, `literature-search-navigation.test.ts` | existing automated coverage |
| AC-V2-03 | Capture runner, six viewport PNGs, `geometry-report.json` | captured; visual parity still iterative |
| AC-V2-04 | `StrategyWorkspaceV2.test.ts` header action test | automated pass |
| AC-V2-05 | `StrategyWorkspaceV2.test.ts` journey / `aria-current` test | automated pass |
| AC-V2-06 | `StrategyWorkspaceV2.test.ts` strategy-basis test | automated pass |
| AC-V2-07 | `StrategyTermsMeshSection.vue`; strategy API term tests | automated pass for component/API subsets |
| AC-V2-08 | `StrategyWorkspaceV2.test.ts` lock, delete, add, remap events | automated pass |
| AC-V2-09 | `StrategyTermsMeshSection.vue` state labels; API strategy tests | automated pass for data/status rendering |
| AC-V2-10 | `StrategyWorkspaceV2.test.ts` query edit/copy/validate events | automated pass |
| AC-V2-11 | query/count components and `useStrategyAutosave.test.ts` | automated pass for stale-facing contracts |
| AC-V2-12 | strategy API Count test; query section presents only returned count | backend/component subset pass |
| AC-V2-13 | `StrategyReadySection.vue` and `LiteratureSearchView.test.ts` execution guard | automated pass |
| AC-V2-14 | sticky bar component test and six viewport captures | automated/component pass |
| AC-V2-15 | `LiteratureSearchView.test.ts` duplicate execute guard | automated pass |
| AC-V2-16 | `StrategyVersionPanel.test.ts`, strategy API version tests | existing automated coverage |
| AC-V2-17 | six viewport capture runner | captured; manual mobile interaction remains pending |
| AC-V2-18 | semantic controls, labels and focus-visible styles; component tests | automated source/component check |
| AC-V2-19 | fixture and production import audit | static audit pending final command |
| AC-V2-20 | capture runner produces six images and captures browser exceptions | automated capture pass |
| AC-V2-21 | `geometry-report.json`, reference/actual overlay/diff | evidence generated; hard-anchor parity not yet met |
| AC-V2-22 | SFC structural implementation; no image/canvas imports | static audit pending final command |
| AC-V2-23 | scoped ESLint + typecheck commands | current scoped pass |
| AC-V2-24 | full test/build/diff gates | pending final full gate |

Visual fixtures are imported only by `frontend/scripts/capture-literature-search-workspace.mjs`; production source must not import them.
