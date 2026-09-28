import { readonly, shallowRef } from "vue";

export type PageRenderPriority = "navigation" | "visible" | "canvas" | "buffer";

export interface PageRenderRequest {
  pageNumber: number;
  generation: number;
  priority: PageRenderPriority;
}

interface SchedulerOptions {
  concurrency: number;
  render: (pageNumber: number, generation: number) => Promise<void>;
  onError?: (cause: unknown, request: PageRenderRequest) => void;
}

const priorityWeight: Record<PageRenderPriority, number> = {
  navigation: 0,
  visible: 1,
  canvas: 2,
  buffer: 3,
};

/**
 * A4 render queue: only the current document/zoom generation may publish work.
 * PDF.js task cancellation belongs to the caller; this queue also prevents queued
 * scroll-past pages and delayed completions from contaminating the new document.
 */
export function usePageRenderScheduler(options: SchedulerOptions) {
  if (!Number.isInteger(options.concurrency) || options.concurrency < 1) {
    throw new RangeError("渲染并发数必须是正整数");
  }
  const queue: PageRenderRequest[] = [];
  const activeKeys = new Set<string>();
  const failures = shallowRef<readonly PageRenderRequest[]>([]);
  const queueLength = shallowRef(0);
  const droppedLateResults = shallowRef(0);
  let activeGeneration = 0;
  let running = 0;
  let idleWaiters: Array<() => void> = [];

  function publishQueueLength(): void {
    queueLength.value = queue.length;
  }

  function resolveIdle(): void {
    if (running || queue.length) return;
    const waiters = idleWaiters;
    idleWaiters = [];
    waiters.forEach((resolve) => resolve());
  }

  function schedule(): void {
    while (running < options.concurrency && queue.length) {
      const request = queue.shift()!;
      publishQueueLength();
      if (request.generation !== activeGeneration) {
        droppedLateResults.value += 1;
        continue;
      }
      running += 1;
      activeKeys.add(`${request.generation}:${request.pageNumber}`);
      void run(request);
    }
    resolveIdle();
  }

  async function run(request: PageRenderRequest): Promise<void> {
    try {
      await options.render(request.pageNumber, request.generation);
    } catch (cause) {
      // 旧代际取消属于正常清理；当前页失败需要可见状态，不能泄漏未处理的 Promise。
      if (request.generation === activeGeneration) {
        failures.value = [...failures.value, request];
        options.onError?.(cause, request);
      }
    } finally {
      if (request.generation !== activeGeneration) droppedLateResults.value += 1;
      activeKeys.delete(`${request.generation}:${request.pageNumber}`);
      running -= 1;
      schedule();
      resolveIdle();
    }
  }

  function enqueue(request: PageRenderRequest): void {
    if (request.generation < activeGeneration) return;
    if (activeKeys.has(`${request.generation}:${request.pageNumber}`)) return;
    activeGeneration = Math.max(activeGeneration, request.generation);
    const duplicate = queue.findIndex((item) => item.pageNumber === request.pageNumber && item.generation === request.generation);
    if (duplicate >= 0) queue.splice(duplicate, 1);
    queue.push(request);
    queue.sort((left, right) => priorityWeight[left.priority] - priorityWeight[right.priority]);
    publishQueueLength();
    queueMicrotask(schedule);
  }

  function invalidate(nextGeneration: number): void {
    if (nextGeneration < activeGeneration) return;
    activeGeneration = nextGeneration;
    failures.value = [];
    const obsolete = queue.filter((item) => item.generation !== nextGeneration).length;
    if (obsolete) droppedLateResults.value += obsolete;
    for (let index = queue.length - 1; index >= 0; index -= 1) {
      if (queue[index]!.generation !== nextGeneration) queue.splice(index, 1);
    }
    publishQueueLength();
    resolveIdle();
  }

  function retainPages(pages: ReadonlySet<number>): void {
    for (let index = queue.length - 1; index >= 0; index -= 1) {
      if (!pages.has(queue[index]!.pageNumber)) queue.splice(index, 1);
    }
    publishQueueLength();
    resolveIdle();
  }

  function whenIdle(): Promise<void> {
    if (!running && !queue.length) return Promise.resolve();
    return new Promise((resolve) => idleWaiters.push(resolve));
  }

  return {
    droppedLateResults: readonly(droppedLateResults),
    failures: readonly(failures),
    enqueue,
    invalidate,
    queueLength: readonly(queueLength),
    retainPages,
    whenIdle,
  };
}
