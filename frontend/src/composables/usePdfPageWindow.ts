import type { Ref } from "vue";
import { calculatePageWindow } from "./usePageVirtualization";

interface PageWindowOptions {
  root: Readonly<Ref<HTMLElement | null>>;
  pinnedPages: () => readonly number[];
  onChange: (wanted: ReadonlySet<number>, visible: ReadonlySet<number>) => void;
}

/** 观测真实可视页；焦点、草稿及正在拖选的页面始终保留文本 DOM。 */
export function usePdfPageWindow(options: PageWindowOptions) {
  let observer: IntersectionObserver | null = null;
  let visible = new Set<number>();
  let wanted = new Set<number>();
  let count = 0;
  let previousTop = 0;
  let generation = 0;

  function refresh(): void {
    const root = options.root.value;
    if (!root || !count) return;
    const pinned = new Set(options.pinnedPages());
    const focused = document.activeElement?.closest<HTMLElement>(".pdf-page");
    if (focused && root.contains(focused)) pinned.add(Number(focused.dataset.pageNumber));
    const selection = window.getSelection();
    if (selection?.rangeCount && !selection.isCollapsed) {
      const range = selection.getRangeAt(0);
      // 拖选期间尚未形成持久化草稿，需要直接保护 Range 跨过的所有页。
      for (const page of root.querySelectorAll<HTMLElement>(".pdf-page")) {
        if (range.intersectsNode(page)) pinned.add(Number(page.dataset.pageNumber));
      }
    }
    const scrollDirection = root.scrollTop > previousTop ? "forward" : root.scrollTop < previousTop ? "backward" : "idle";
    previousTop = root.scrollTop;
    const states = calculatePageWindow({ pageCount: count, visiblePages: [...visible],
      pinnedPages: [...pinned], bufferPages: 1, scrollDirection });
    wanted = new Set(states.flatMap((state, index) => state === "released" ? [] : [index + 1]));
    options.onChange(wanted, visible);
  }

  function disconnect(): void {
    generation += 1;
    observer?.disconnect(); observer = null;
    visible = new Set(); wanted = new Set(); count = 0;
  }

  function connect(pageCount: number, initialPages: readonly number[] = [1]): void {
    disconnect(); count = pageCount; previousTop = 0;
    visible = new Set(pageCount ? initialPages : []);
    refresh();
    if (typeof IntersectionObserver === "undefined") return;
    const currentGeneration = generation;
    observer = new IntersectionObserver((entries) => {
      if (currentGeneration !== generation) return;
      for (const entry of entries) {
        const page = Number((entry.target as HTMLElement).dataset.pageNumber);
        if (entry.isIntersecting) visible.add(page); else visible.delete(page);
      }
      refresh();
    }, { root: options.root.value, threshold: 0 });
    options.root.value?.querySelectorAll(".pdf-page").forEach((page) => observer!.observe(page));
  }

  function reconnect(): void {
    connect(count, [...visible]);
  }

  return { connect, disconnect, reconnect, refresh, wants: (page: number) => wanted.has(page) };
}
