<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { documentsApi, type BatchIndexResult } from "../../api/documents";
import { useDocuments } from "../../composables/useDocuments";
import { useDocumentUpload } from "../../composables/useDocumentUpload";
import DocumentFilters from "./DocumentFilters.vue";
import DocumentTable from "./DocumentTable.vue";
import DocumentUploadPanel from "./DocumentUploadPanel.vue";

const { documents, filters, total, loading, error, pageNumber, hasPrevious, hasNext, load, applyFilters, retryParse, retryIndex, deleteIndex, previousPage, nextPage } = useDocuments();
const selectedIds = shallowRef<number[]>([]);
const batchResult = shallowRef<BatchIndexResult | null>(null);
const batchError = shallowRef<string | null>(null);
const { uploading, error: uploadError, uploadedFilename, upload } = useDocumentUpload();
const canBatchIndex = computed(() => selectedIds.value.length > 0 && !loading.value);
const requestError = computed(() => error.value ?? batchError.value ?? uploadError.value);

function toggleSelect(documentId: number, selected: boolean) {
  selectedIds.value = selected ? [...new Set([...selectedIds.value, documentId])] : selectedIds.value.filter((id) => id !== documentId);
}

async function batchIndex() {
  if (!canBatchIndex.value) return;
  batchError.value = null;
  try {
    batchResult.value = await documentsApi.batchIndex(selectedIds.value);
    selectedIds.value = [];
    await load();
  } catch (cause) {
    batchError.value = cause instanceof Error ? cause.message : "批量索引请求失败";
  }
}

async function uploadPdf(file: File): Promise<void> {
  if (await upload(file)) await load();
}

onMounted(load);
</script>

<template>
  <section class="manager" aria-labelledby="documents-title">
    <header class="manager-header"><div><p class="eyebrow">DOCUMENT PIPELINE · LIVE</p><h2 id="documents-title">文档库</h2></div><p class="summary">{{ total }} 篇系统记录</p></header>
    <DocumentUploadPanel :uploading="uploading" :error-message="uploadError" :uploaded-filename="uploadedFilename" @upload="uploadPdf" />
    <DocumentFilters :filters="filters" :disabled="loading" @change="applyFilters" />
    <div v-if="selectedIds.length" class="bulk-bar"><span>已选择 {{ selectedIds.length }} 篇</span><button :disabled="!canBatchIndex" @click="batchIndex">批量建立索引</button></div>
    <p v-if="batchResult" class="batch-result">批量请求完成：{{ batchResult.succeeded }} 成功，{{ batchResult.failed }} 失败。请以列表状态为准。</p>
    <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p>
    <DocumentTable :documents="documents" :disabled="loading" :selected-ids="selectedIds" @toggle-select="toggleSelect" @retry-parse="retryParse" @retry-index="retryIndex" @delete-index="deleteIndex" />
    <footer class="pagination"><button :disabled="loading || !hasPrevious" @click="previousPage">上一页</button><span>第 {{ pageNumber }} 页</span><button :disabled="loading || !hasNext" @click="nextPage">下一页</button></footer>
  </section>
</template>

<style scoped>
.manager { display: grid; gap: 1.1rem; padding: 1.35rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); background: var(--surface-raised); box-shadow: var(--shadow-card); }
.manager-header { display: flex; align-items: end; justify-content: space-between; gap: 1rem; }.manager-header h2 { margin: .1rem 0 0; font-size: 1.7rem; }.eyebrow { margin: 0; color: var(--color-primary); font-size: .72rem; font-weight: 900; letter-spacing: .14em; }.summary { color: var(--text-muted); }.request-error { margin: 0; padding: .8rem; border-radius: 10px; background: var(--color-danger-soft); color: var(--color-danger); }.bulk-bar { display: flex; align-items: center; justify-content: space-between; gap: .8rem; padding: .75rem .9rem; border-radius: var(--radius-md); background: var(--color-primary-soft); color: var(--color-primary); font-weight: 750; }.bulk-bar button, .pagination button { border: 1px solid var(--border-strong); border-radius: 8px; padding: .5rem .8rem; background: var(--paper); color: var(--text-primary); font: inherit; }.batch-result { margin: 0; color: var(--text-muted); font-size: .88rem; }.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; }@media (max-width: 640px) { .manager-header, .bulk-bar { align-items: flex-start; flex-direction: column; } }
</style>
