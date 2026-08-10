import { onScopeDispose, readonly, shallowRef, watch } from "vue";

import { documentOcrApi, type OcrJob } from "../api/documentOcr";

const POLL_INTERVAL_MS = 2000;

export function useDocumentOcr(documentId: number, isScanned: () => boolean) {
  const job = shallowRef<OcrJob | null>(null);
  const loading = shallowRef(false);
  const submitting = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let pollTimer: ReturnType<typeof setInterval> | undefined;

  async function load(): Promise<void> {
    if (!isScanned()) return;
    loading.value = true;
    error.value = null;
    try {
      job.value = await documentOcrApi.getLatest(documentId);
      syncPolling();
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法读取 OCR 状态";
    } finally {
      loading.value = false;
    }
  }

  async function request(): Promise<boolean> {
    if (submitting.value) return false;
    submitting.value = true;
    error.value = null;
    try {
      job.value = await documentOcrApi.request(documentId);
      syncPolling();
      return job.value.status !== "failed";
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法发起 OCR";
      return false;
    } finally {
      submitting.value = false;
    }
  }

  async function cancel(): Promise<void> {
    if (submitting.value) return;
    submitting.value = true;
    error.value = null;
    try {
      job.value = await documentOcrApi.cancel(documentId);
      stopPolling();
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法取消 OCR";
    } finally {
      submitting.value = false;
    }
  }

  function syncPolling(): void {
    if (job.value?.status === "queued" || job.value?.status === "processing") {
      if (!pollTimer) pollTimer = setInterval(load, POLL_INTERVAL_MS);
      return;
    }
    stopPolling();
  }

  function stopPolling(): void {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = undefined;
  }

  watch(isScanned, (nextIsScanned) => {
    if (nextIsScanned) void load();
    else stopPolling();
  }, { immediate: true });
  onScopeDispose(stopPolling);

  return {
    job: readonly(job),
    loading: readonly(loading),
    submitting: readonly(submitting),
    error: readonly(error),
    load,
    request,
    cancel,
  };
}
