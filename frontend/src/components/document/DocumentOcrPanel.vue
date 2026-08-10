<script setup lang="ts">
import { watch } from "vue";

import type { OcrJobStatus } from "../../api/documentOcr";
import { useDocumentOcr } from "../../composables/useDocumentOcr";

const props = defineProps<{
  documentId: number;
  isScanned: boolean;
}>();

const emit = defineEmits<{
  completed: [];
}>();

const { job, loading, submitting, error, request, cancel } = useDocumentOcr(
  props.documentId,
  () => props.isScanned,
);

const statusLabels: Record<OcrJobStatus, string> = {
  queued: "等待处理",
  processing: "正在识别",
  succeeded: "识别完成",
  partial_failed: "部分页面失败",
  failed: "识别失败",
  cancelled: "已取消",
};

function canRequest(): boolean {
  return !job.value || ["succeeded", "partial_failed", "failed", "cancelled"].includes(job.value.status);
}

function isRunning(): boolean {
  return job.value?.status === "queued" || job.value?.status === "processing";
}

watch(() => job.value?.status, (nextStatus, previousStatus) => {
  if (
    previousStatus &&
    previousStatus !== nextStatus &&
    (nextStatus === "succeeded" || nextStatus === "partial_failed")
  ) emit("completed");
});
</script>

<template>
  <section v-if="props.isScanned" class="ocr-panel" aria-labelledby="ocr-title">
    <div>
      <p class="eyebrow">SCAN DETECTED</p>
      <h3 id="ocr-title" class="ocr-title">识别文字（OCR）</h3>
      <p class="description">仅在本机 OCR 引擎可用时执行；原始 PDF 不会被修改。</p>
    </div>
    <p v-if="loading" class="status" role="status">正在读取 OCR 状态…</p>
    <template v-else>
      <p v-if="job" class="status" role="status">
        {{ statusLabels[job.status] }}
        <span v-if="job.page_count !== null">：已完成 {{ job.completed_pages }} / {{ job.page_count }} 页</span>
        <span v-if="job.failed_pages">，失败 {{ job.failed_pages }} 页</span>
      </p>
      <p v-if="job?.error_message || error" class="error" role="alert">{{ job?.error_message ?? error }}</p>
      <div class="actions">
        <button v-if="canRequest()" :disabled="submitting" @click="request">
          {{ submitting ? "正在提交…" : "开始 OCR" }}
        </button>
        <button v-if="isRunning()" class="secondary" :disabled="submitting" @click="cancel">取消</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.ocr-panel { display: grid; gap: .65rem; padding: .9rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface-muted); }
.eyebrow { margin: 0; color: var(--color-primary); font-size: .72rem; font-weight: 900; letter-spacing: .12em; }
.ocr-title { margin: .2rem 0 0; font-size: 1rem; }.description, .status, .error { margin: .35rem 0 0; font-size: .84rem; line-height: 1.5; }.description, .status { color: var(--text-muted); }.error { color: var(--color-danger); }
.actions { display: flex; gap: .5rem; }.actions button { border: 0; border-radius: 7px; padding: .5rem .7rem; background: var(--color-primary); color: #fff; font: inherit; font-weight: 750; }.actions .secondary { border: 1px solid var(--border-strong); background: var(--paper); color: var(--text-primary); }
</style>
