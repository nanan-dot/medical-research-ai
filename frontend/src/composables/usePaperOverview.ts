import { readonly, shallowRef } from "vue";

import { paperLibraryApi, type PaperOverview } from "../api/paperLibrary";

/** 用户快速切换论文时只保留最后一次响应，避免慢请求把右栏回滚到旧论文。 */
export function usePaperOverview() {
  const paper = shallowRef<PaperOverview | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let controller: AbortController | null = null;
  let requestSequence = 0;

  async function load(id: number): Promise<void> {
    const sequence = ++requestSequence;
    controller?.abort();
    controller = new AbortController();
    loading.value = true;
    error.value = null;
    try {
      const nextPaper = await paperLibraryApi.overview(id, controller.signal);
      if (sequence === requestSequence) paper.value = nextPaper;
    } catch (cause) {
      if (sequence !== requestSequence || (cause instanceof DOMException && cause.name === "AbortError")) return;
      paper.value = null;
      error.value = cause instanceof Error ? cause.message : "论文概览暂时无法加载";
    } finally {
      if (sequence === requestSequence) loading.value = false;
    }
  }

  function clear(): void { requestSequence += 1; controller?.abort(); paper.value = null; error.value = null; loading.value = false; }
  function cancel(): void { requestSequence += 1; controller?.abort(); }
  return { paper: readonly(paper), loading: readonly(loading), error: readonly(error), load, clear, cancel };
}
