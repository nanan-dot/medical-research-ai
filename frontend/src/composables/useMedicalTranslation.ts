import { computed, onScopeDispose, readonly, shallowRef, watch } from "vue";

import { medicalTranslationsApi, type TranslationJob, type TranslationRevision } from "../api/medicalTranslations";
import type { PdfTextSelection } from "../types/documentAnnotations";

const POLL_INTERVAL_MS = 800;
const ACTIVE_STATES = new Set(["queued", "running", "quality_checking"]);

export function useMedicalTranslation(
  documentId: () => number,
  fileHash: () => string,
  selection: () => PdfTextSelection | null,
) {
  const job = shallowRef<TranslationJob | null>(null);
  const revision = shallowRef<TranslationRevision | null>(null);
  const busy = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const editing = shallowRef(false);
  let generation = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const canTranslate = computed(() => Boolean(selection()?.anchorDescriptor) && !busy.value);

  function invalidate(): void {
    generation += 1;
    if (timer !== null) clearTimeout(timer);
    timer = null;
    job.value = null;
    revision.value = null;
    error.value = null;
    busy.value = false;
    editing.value = false;
  }

  async function loadRevision(current: number, revisionId: number): Promise<void> {
    const result = await medicalTranslationsApi.revision(revisionId);
    if (current === generation) revision.value = result;
  }

  async function poll(current: number, jobId: number): Promise<void> {
    try {
      const result = await medicalTranslationsApi.job(jobId);
      if (current !== generation) return;
      job.value = result;
      if (result.state === "succeeded" && result.result_revision_id !== null) {
        await loadRevision(current, result.result_revision_id);
        if (current === generation) busy.value = false;
      } else if (ACTIVE_STATES.has(result.state)) {
        timer = setTimeout(() => void poll(current, jobId), POLL_INTERVAL_MS);
      } else {
        busy.value = false;
      }
    } catch (cause) {
      if (current !== generation) return;
      error.value = cause instanceof Error ? cause.message : "无法读取翻译状态";
      busy.value = false;
    }
  }

  async function translate(): Promise<void> {
    const capturedSelection = selection();
    const descriptor = capturedSelection?.anchorDescriptor;
    if (!descriptor || busy.value) return;
    const current = ++generation;
    if (timer !== null) clearTimeout(timer);
    job.value = null;
    revision.value = null;
    error.value = null;
    busy.value = true;
    const capturedDocument = documentId();
    const capturedHash = fileHash();
    try {
      const result = await medicalTranslationsApi.create(capturedDocument, descriptor, crypto.randomUUID());
      if (current !== generation || capturedDocument !== documentId() || capturedHash !== fileHash()) return;
      job.value = result;
      if (result.state === "succeeded" && result.result_revision_id !== null) {
        await loadRevision(current, result.result_revision_id);
        if (current === generation) busy.value = false;
      } else if (ACTIVE_STATES.has(result.state)) {
        timer = setTimeout(() => void poll(current, result.id), POLL_INTERVAL_MS);
      } else busy.value = false;
    } catch (cause) {
      if (current !== generation) return;
      error.value = cause instanceof Error ? cause.message : "创建翻译任务失败";
      busy.value = false;
    }
  }

  async function openJob(nextJob: TranslationJob): Promise<void> {
    if (selection()) return;
    const current = ++generation;
    if (timer !== null) clearTimeout(timer);
    job.value = nextJob;
    revision.value = null;
    error.value = null;
    editing.value = false;
    busy.value = ACTIVE_STATES.has(nextJob.state);
    if (nextJob.state === "succeeded" && nextJob.result_revision_id !== null) {
      await loadRevision(current, nextJob.result_revision_id);
      if (current === generation) busy.value = false;
    } else if (ACTIVE_STATES.has(nextJob.state)) {
      timer = setTimeout(() => void poll(current, nextJob.id), POLL_INTERVAL_MS);
    }
  }

  async function cancel(): Promise<void> {
    if (!job.value || !ACTIVE_STATES.has(job.value.state)) return;
    const current = generation;
    try {
      const result = await medicalTranslationsApi.cancel(job.value.id);
      if (current === generation) { job.value = result; busy.value = false; }
    } catch (cause) {
      if (current === generation) error.value = cause instanceof Error ? cause.message : "取消翻译失败";
    }
  }

  async function retry(): Promise<void> {
    if (!job.value || !["failed", "cancelled"].includes(job.value.state)) return;
    const current = ++generation;
    error.value = null; revision.value = null; busy.value = true;
    try {
      const result = await medicalTranslationsApi.retry(job.value.id);
      if (current !== generation) return;
      job.value = result;
      timer = setTimeout(() => void poll(current, result.id), POLL_INTERVAL_MS);
    } catch (cause) {
      if (current === generation) { error.value = cause instanceof Error ? cause.message : "重试翻译失败"; busy.value = false; }
    }
  }

  async function saveCorrection(text: string, reason: string | null): Promise<boolean> {
    if (!revision.value || !text.trim()) return false;
    const current = generation;
    busy.value = true; error.value = null;
    try {
      const result = await medicalTranslationsApi.correct(revision.value.id, revision.value.version, text.trim(), reason);
      if (current !== generation) return false;
      revision.value = result; editing.value = false;
      return true;
    } catch (cause) {
      if (current === generation) error.value = cause instanceof Error ? cause.message : "保存人工修订失败";
      return false;
    } finally {
      if (current === generation) busy.value = false;
    }
  }

  watch(() => [documentId(), fileHash(), selection()?.anchorDescriptor], invalidate, { deep: false });
  onScopeDispose(invalidate);

  return { job: readonly(job), revision: readonly(revision), busy: readonly(busy), error: readonly(error), editing, canTranslate, translate, openJob, cancel, retry, saveCorrection };
}
