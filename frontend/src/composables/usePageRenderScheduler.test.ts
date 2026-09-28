import { describe, expect, it, vi } from "vitest";

import { usePageRenderScheduler } from "./usePageRenderScheduler";

describe("usePageRenderScheduler", () => {
  it("reports a failed page and continues rendering other pages", async () => {
    const onError = vi.fn();
    const started: number[] = [];
    const scheduler = usePageRenderScheduler({ concurrency: 1, onError,
      render: async (page) => { started.push(page); if (page === 1) throw new Error("canvas failure"); } });
    scheduler.enqueue({ pageNumber: 1, generation: 1, priority: "visible" });
    scheduler.enqueue({ pageNumber: 2, generation: 1, priority: "buffer" });
    await scheduler.whenIdle();
    expect(started).toEqual([1, 2]);
    expect(onError).toHaveBeenCalledOnce();
    expect(scheduler.failures.value.map(item => item.pageNumber)).toEqual([1]);
  });

  it("deduplicates running pages and removes scroll-past queued work", async () => {
    let complete!: () => void;
    const render = vi.fn(() => new Promise<void>(resolve => { complete = resolve; }));
    const scheduler = usePageRenderScheduler({ concurrency: 1, render });
    scheduler.enqueue({ pageNumber: 1, generation: 1, priority: "visible" });
    await Promise.resolve();
    scheduler.enqueue({ pageNumber: 1, generation: 1, priority: "navigation" });
    scheduler.enqueue({ pageNumber: 2, generation: 1, priority: "buffer" });
    scheduler.retainPages(new Set([1]));
    complete(); await scheduler.whenIdle();
    expect(render).toHaveBeenCalledOnce();
    expect(scheduler.queueLength.value).toBe(0);
  });
  it("runs a navigation target before queued visible and buffer pages", async () => {
    const started: number[] = [];
    const scheduler = usePageRenderScheduler({
      concurrency: 1,
      render: async (pageNumber) => { started.push(pageNumber); },
    });

    scheduler.enqueue({ pageNumber: 3, generation: 1, priority: "buffer" });
    scheduler.enqueue({ pageNumber: 2, generation: 1, priority: "visible" });
    scheduler.enqueue({ pageNumber: 9, generation: 1, priority: "navigation" });
    await scheduler.whenIdle();

    expect(started).toEqual([9, 2, 3]);
  });

  it("cancels queued work and drops late results from an obsolete generation", async () => {
    let releaseFirst!: () => void;
    const render = vi.fn(async () => new Promise<void>((resolve) => { releaseFirst = resolve; }));
    const scheduler = usePageRenderScheduler({ concurrency: 1, render });

    scheduler.enqueue({ pageNumber: 1, generation: 1, priority: "visible" });
    await Promise.resolve();
    scheduler.enqueue({ pageNumber: 2, generation: 1, priority: "buffer" });
    scheduler.invalidate(2);
    releaseFirst();
    await scheduler.whenIdle();

    expect(render).toHaveBeenCalledTimes(1);
    expect(scheduler.droppedLateResults.value).toBe(2);
    expect(scheduler.queueLength.value).toBe(0);
  });
});
