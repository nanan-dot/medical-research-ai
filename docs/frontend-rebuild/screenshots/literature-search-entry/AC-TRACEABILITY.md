# Literature search entry acceptance traceability

| AC | Executable evidence | Result |
| --- | --- | --- |
| 01 | `SearchEntryView.test.ts`: renders entry | pass |
| 02 | `SearchEntryRoutes.test.ts`: workspace route | pass |
| 03 | `SearchEntryView.test.ts`: blank disables CTA | pass |
| 04 | `SearchEntryView.test.ts`: 500-character bound | pass |
| 05 | `SearchEntryView.test.ts`: mode preserves question | pass |
| 06 | `SearchEntryView.test.ts`: example fills only | pass |
| 07 | `SearchEntryView.test.ts`: template fills only | pass |
| 08 | `SearchEntryView.test.ts`: one sequential pipeline | pass |
| 09 | `SearchEntryView.test.ts`: parse/expand/build URL order | pass |
| 10 | `SearchEntryView.test.ts`: failure retains input and retry | pass |
| 11 | `SearchEntryView.test.ts`: handoff to workspace | pass |
| 12 | `SearchEntryRoutes.test.ts`: URL raw topic restoration | pass |
| 13 | `SearchEntryRoutes.test.ts`: history/results deep links | pass |
| 14 | `SearchEntryView.test.ts`: Ctrl+Enter only | pass |
| 15 | `capture-literature-search-entry.mjs`: six viewport capture and locators | pass |
| 16 | `capture-literature-search-entry.mjs`: console/page/network failures cause nonzero exit | pass |

The browser acceptance script was run successfully against the local Vite server and recorded the six viewport PNGs and geometry report beside this file.
