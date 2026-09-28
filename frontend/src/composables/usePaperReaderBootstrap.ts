import { computed, getCurrentInstance, onBeforeUnmount, shallowRef, watch, type MaybeRefOrGetter, toValue } from "vue";
import { paperReaderApi, type ReaderBootstrap, type ReaderSession } from "../api/paperReader";

/** 启动快照按 generation 隔离，避免切换论文后旧响应污染新 PDF/锚点代际。 */
export function usePaperReaderBootstrap(itemId: MaybeRefOrGetter<number | null>) {
  const bootstrap = shallowRef<ReaderBootstrap | null>(null);
  const session = shallowRef<ReaderSession | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let controller: AbortController | null = null;
  let generation = 0;

  async function load(): Promise<void> {
    controller?.abort();
    const currentId = toValue(itemId);
    const currentGeneration = ++generation;
    bootstrap.value = null; session.value = null; error.value = null;
    if (!currentId || !Number.isInteger(currentId) || currentId < 1) return;
    controller = new AbortController(); loading.value = true;
    try {
      const next = await paperReaderApi.bootstrap(currentId, controller.signal);
      if (currentGeneration !== generation) return;
      bootstrap.value = next;
      session.value = next.resume.session_id
        ? { id: next.resume.session_id, file_hash: next.document.file_hash, page: next.resume.page, viewport_offset_ratio: next.resume.viewport_offset_ratio, status: "active", version: 1 }
        : await paperReaderApi.createSession(currentId, "web-local-reader");
    } catch (cause) {
      if (currentGeneration === generation && !(cause instanceof DOMException && cause.name === "AbortError")) error.value = cause instanceof Error ? cause.message : "无法启动论文阅读工作区";
    } finally { if (currentGeneration === generation) loading.value = false; }
  }

  async function persistPosition(page: number): Promise<void> {
    if (!bootstrap.value || !session.value) return;
    session.value = await paperReaderApi.updatePosition(session.value.id, { page, viewport_offset_ratio: 0, expected_version: session.value.version, expected_file_hash: bootstrap.value.document.file_hash });
  }
  async function close(): Promise<void> { if (session.value) await paperReaderApi.closeSession(session.value.id).catch(() => undefined); }
  watch(() => toValue(itemId), () => { void load(); }, { immediate: true });
  if (getCurrentInstance()) onBeforeUnmount(() => { controller?.abort(); void close(); });
  return { bootstrap, session, loading, error, load, persistPosition, close, ready: computed(() => Boolean(bootstrap.value && session.value)) };
}
