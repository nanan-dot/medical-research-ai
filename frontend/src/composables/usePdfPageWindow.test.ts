import { shallowRef } from "vue";
import { afterEach, expect, it, vi } from "vitest";
import { usePdfPageWindow } from "./usePdfPageWindow";

afterEach(() => { document.body.replaceChildren(); vi.unstubAllGlobals(); });

it("releases distant pages, retains focused and selected pages, and ignores an old observer", () => {
  const callbacks: IntersectionObserverCallback[] = [];
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: IntersectionObserverCallback) { callbacks.push(callback); }
    observe() {} disconnect() {}
  });
  const root = document.createElement("div");
  for (let number = 1; number <= 20; number++) {
    const page = document.createElement("div"); page.className = "pdf-page"; page.dataset.pageNumber = String(number);
    const button = document.createElement("button"); button.textContent = String(number); page.append(button); root.append(page);
  }
  document.body.append(root);
  let wanted: ReadonlySet<number> = new Set();
  let pinned = [3];
  const window = usePdfPageWindow({ root: shallowRef(root), pinnedPages: () => pinned,
    onChange: (pages) => { wanted = pages; } });
  window.connect(20);
  (root.children[4]!.firstChild as HTMLElement).focus();
  callbacks[0]!([
    { target: root.children[0]!, isIntersecting: false },
    { target: root.children[14]!, isIntersecting: true },
  ] as IntersectionObserverEntry[], {} as IntersectionObserver);
  expect(wanted.has(1)).toBe(false);
  expect(wanted.has(15)).toBe(true);
  expect(wanted.has(3)).toBe(true);
  expect(wanted.has(5)).toBe(true);
  pinned = []; (document.activeElement as HTMLElement).blur(); window.refresh();
  expect(wanted.has(3)).toBe(false);
  expect(wanted.has(5)).toBe(false);
  window.connect(20);
  callbacks[0]!([{ target: root.children[14]!, isIntersecting: true }] as IntersectionObserverEntry[], {} as IntersectionObserver);
  expect(wanted.has(15)).toBe(false);
  window.disconnect();
});
