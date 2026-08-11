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
    <header class="manager-header"><div><h2 id="documents-title">文档处理</h2></div><p class="summary">{{ loading ? "正在读取文档" : `${total} 篇系统记录` }}</p></header>
    <div class="toolbar-row"><DocumentFilters :filters="filters" :disabled="loading" @change="applyFilters" /><DocumentUploadPanel :uploading="uploading" :error-message="uploadError" :uploaded-filename="uploadedFilename" @upload="uploadPdf" /></div>
    <p class="scope-note">仅显示系统已同步或上传的本地材料</p>
    <div v-if="selectedIds.length" class="bulk-bar"><span>已选择 {{ selectedIds.length }} 篇</span><button :disabled="!canBatchIndex" @click="batchIndex">批量建立索引</button></div>
    <p v-if="batchResult" class="batch-result">批量请求完成：{{ batchResult.succeeded }} 成功，{{ batchResult.failed }} 失败。请以列表状态为准。</p>
    <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p>
    <DocumentTable :documents="documents" :disabled="loading" :selected-ids="selectedIds" @toggle-select="toggleSelect" @retry-parse="retryParse" @retry-index="retryIndex" @delete-index="deleteIndex" />
    <footer class="pagination"><button :disabled="loading || !hasPrevious" @click="previousPage">上一页</button><span>第 {{ pageNumber }} 页</span><button :disabled="loading || !hasNext" @click="nextPage">下一页</button></footer><section class="evidence-note"><h3>文档何时可用于证据问答？</h3><p>解析成功并完成当前索引后，文档才可作为本地证据来源。</p></section>
  </section>
</template>

<style scoped>
.manager{display:grid;gap:.8rem}.manager-header{display:flex;align-items:end;justify-content:space-between}.manager-header h2{margin:0;color:#10213d;font-size:1.35rem}.summary,.scope-note{margin:0;color:var(--text-muted)}.toolbar-row{display:flex;align-items:center;justify-content:space-between;gap:.8rem}.toolbar-row :deep(.filters){flex:1}.request-error{margin:0;padding:.8rem;border:1px solid #fecaca;border-radius:8px;background:var(--color-danger-soft);color:var(--color-danger)}.bulk-bar{display:flex;align-items:center;gap:1rem;padding:.7rem 1rem;border:1px solid #bfdbfe;background:#eff6ff;color:var(--color-primary);font-weight:700}.bulk-bar button,.pagination button{border:1px solid var(--border-strong);border-radius:7px;padding:.45rem .75rem;background:#fff;color:var(--color-primary);font:inherit}.batch-result{margin:0;color:var(--text-muted)}.pagination{display:flex;align-items:center;justify-content:center;gap:1rem}.evidence-note{padding:1rem 1.25rem;border:1px solid var(--border-subtle);border-radius:10px;background:#f8fbff}.evidence-note h3,.evidence-note p{margin:0}.evidence-note p{margin-top:.3rem;color:var(--text-muted)}@media(max-width:760px){.toolbar-row{align-items:stretch;flex-direction:column}.manager-header,.bulk-bar{align-items:flex-start;flex-direction:column}}
</style>
