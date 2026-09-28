# Literature search workspace V2 visual acceptance

Visual fixture only: `frontend/scripts/visual-test-only/workspace-v2.fixture.mjs`.
Production code does not import this fixture.

1536×1024 measured anchors from `geometry-report.json`:

| Region | Actual | Target | Delta |
| --- | --- | --- | --- |
| Sidebar/Main | 229px | 229px | 0px |
| Viewport document | 1536×1024; scroll 1536×1024 | no page scrolling | pass |
| Header | y=0, h=75 | y=0, h=75 | 0px |
| Journey | y=75, h=62 | y=75, h=62 | 0px |
| Basis | y=137, h=196 | y=138, h=196 | 1px |
| Terms/MeSH | y=343, h=386 | y=344, h=386 | 1px |
| Query | y=739, h=98 | y=739, h=98 | 0px |
| Limits/Ready | y=857, h=80 | y=848, h=80 | 9px vertical |
| Sticky | y=937, h=79 | y=939, h=79 | 2px vertical |

The 1536 implementation, overlay and pixel diff were regenerated after the fourth-round single-action change and manually viewed. The review confirmed: three grouped term rows using the target fixture vocabulary, five complete MeSH rows with linear lock icons, the complete warning action row, four colored PICO markers, four limits, four readiness checks, and a version/save/count sticky summary.

Approved intentional difference: the Header has no “开始检索” action. The bottom Sticky bar is the page's only executable search action, per the current product decision.

The latest sixth-round `visual-acceptance.json` reports `changed_pixel_ratio: 0.935596`. This is a high whole-image difference, so the implementation is **not** visually equivalent to the reference. See `sixth-round-real-flow-audit.md` for separate Sidebar/Header/Journey/Basis/Terms/Query/LimitsReady/Sticky geometry, pixel and manual findings, plus the independent-profile production flow. Remaining material differences include the sidebar's logo/navigation icon family and density, typography/rendering, Journey line/text alignment, PICO internals, and several internal layouts in the Terms, Limits, Ready and Sticky regions. Pixel diff remains an iteration signal; no 100% visual identity claim is made.

The latest six-viewport geometry run also verifies that the 1440×900 and 1280×800 documents have no horizontal overflow (`scrollWidth = clientWidth`).
