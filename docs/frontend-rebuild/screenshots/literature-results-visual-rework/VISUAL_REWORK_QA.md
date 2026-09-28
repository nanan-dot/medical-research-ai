# Literature Results visual rework QA

Run: 2026-08-26. Route: `/literature-search/results/26?task=16&from=history`.
The browser CSS viewport was explicitly set to 1600 × 1000. The browser image transport excludes its scrollbar/chrome pixels (1585 × 970), so `implementation-final-normalized-1600x1000.png` is a dimension-normalized copy of the direct capture for the required like-for-like comparison.

| Region | Target | Implementation | Delta | Gate |
| --- | ---: | ---: | ---: | --- |
| Viewport | 1600 × 1000 | 1600 × 1000 | 0 | pass |
| Left sidebar width | 188 px | 188 px | 0 px | pass |
| Topbar height | 62 px | 62 px | 0 px | pass |
| Context header | y=62, h=97 px | y=62, h=97 px | 0 px | pass |
| Main tabs | y=159, h=51 px | y=159, h=51 px | 0 px | pass |
| Sort toolbar + chips | y=210–296 px | y=210–296 px | 0 px | pass |
| List start | y≈304 px | y≈304 px | ≤8 px | pass |
| Result row height | ≈130 px | ≈128 px | 2 px | pass |
| Filter rail width | 267 px | 267 px | 0 px | pass |

Artifacts:

- `target-1600x1000.png` — supplied target
- `implementation-final-1600x1000.png` — direct browser capture
- `implementation-final-normalized-1600x1000.png` — 1600 × 1000 comparison capture
- `target-implementation-overlay-50pct.png` — 50% alpha overlay

Content totals and individual papers intentionally come from the tested local result snapshot and therefore differ from the supplied reference data; geometry and presentation are the comparison scope.
