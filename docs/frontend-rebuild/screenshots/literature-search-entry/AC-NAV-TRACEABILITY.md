# Literature-search navigation acceptance traceability

| AC | Executable evidence |
| --- | --- |
| AC-NAV-01 | `AppSidebar.test.ts`: dedicated literature expand control |
| AC-NAV-02 | `AppSidebar.test.ts`: center text link routes to `/literature-search` |
| AC-NAV-03 | `AppSidebar.test.ts`: expand control hides/shows menu without changing route |
| AC-NAV-04 | `AppSidebar.test.ts`: exact four-item label order |
| AC-NAV-05 | `AppSidebar.test.ts`: workspace maps to active search center |
| AC-NAV-06 | `AppSidebar.test.ts`: history active mapping |
| AC-NAV-07 | `AppSidebar.test.ts`: results index/detail active mapping |
| AC-NAV-08 | `AppSidebar.test.ts`: recommendation active mapping |
| AC-NAV-09 | `AppSidebar.test.ts`: every active child has `aria-current=page` |
| AC-NAV-10 | `AppSidebar.test.ts`: collapsed sidebar hides and restores secondary navigation |
| AC-NAV-11 | `literature-search-navigation.test.ts`: stable entry route resolution |
| AC-NAV-12 | `SearchEntryView.test.ts`: successful creation hands off to workspace |
| AC-NAV-13 | `literature-search-navigation.test.ts`: dedicated workspace route resolution |
| AC-NAV-14 | `ResultsIndexView.test.ts`: honest no-ID state and recovery links |
| AC-NAV-15 | `literature-search-navigation.test.ts`: legacy history-tab redirect, query preservation, no loop |
| AC-NAV-16 | `History.test.ts`: rerun event returns a real task/result selection; `LiteratureSearchView.vue` handles it in the workspace |
| AC-NAV-17 | `Breadcrumbs.test.ts`: history-origin and fallback results breadcrumb links |
| AC-NAV-18 | Component tests verify semantic buttons/links and visible focus styles are implemented; browser capture checks page rendering |
| AC-NAV-19 | `capture-literature-search-entry.mjs`: desktop and mobile screenshots with required locators |
| AC-NAV-20 | `capture-literature-search-entry.mjs`: console errors, page errors, and request failures make the run fail |

The traceability references executable tests or the browser acceptance script. Results are recorded only after the commands in the delivery report have been run.
