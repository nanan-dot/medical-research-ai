export type PageLifecycleState = "rendered" | "parked" | "released";

export interface PageWindowInput {
  pageCount: number;
  visiblePages: readonly number[];
  scrollDirection: "forward" | "backward" | "idle";
  pinnedPages: readonly number[];
  bufferPages: number;
}

/**
 * Produces page lifecycle states without touching DOM or PDF.js objects.
 * `parked` preserves a stable shell; callers may independently release pixels
 * and text nodes after the user has moved away from that shell.
 */
export function calculatePageWindow(input: PageWindowInput): PageLifecycleState[] {
  const states = Array<PageLifecycleState>(input.pageCount).fill("released");
  const protectedPages = new Set(input.pinnedPages);
  for (const page of input.visiblePages) protectedPages.add(page);

  const firstVisible = Math.min(...input.visiblePages);
  const lastVisible = Math.max(...input.visiblePages);
  if (Number.isFinite(firstVisible) && Number.isFinite(lastVisible)) {
    const backwardBuffer = input.bufferPages + (input.scrollDirection === "backward" ? 1 : 0);
    const forwardBuffer = input.bufferPages + (input.scrollDirection === "forward" ? 1 : 0);
    for (let page = firstVisible - backwardBuffer; page <= lastVisible + forwardBuffer; page += 1) {
      if (page >= 1 && page <= input.pageCount) protectedPages.add(page);
    }
  }

  for (const page of protectedPages) {
    if (page < 1 || page > input.pageCount) continue;
    states[page - 1] = input.visiblePages.includes(page) ? "rendered" : "parked";
  }
  return states;
}
