<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { documentsApi, type BatchIndexResult, type DocumentRecord } from "../../api/documents";
import { useDocumentNavigation } from "../../composables/useDocumentNavigation";
import { useDocuments } from "../../composables/useDocuments";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";
import DocumentNavigationPanel from "../document-navigation/DocumentNavigationPanel.vue";
import DocumentNavigationResults from "../document-navigation/DocumentNavigationResults.vue";
import DocumentFilters from "./DocumentFilters.vue";
import DocumentInspector from "./DocumentInspector.vue";
import DocumentScopeNav from "./DocumentScopeNav.vue";
import DocumentTable from "./DocumentTable.vue";
import DocumentWorkspaceSummary from "./DocumentWorkspaceSummary.vue";

const route = useRoute();
const router = useRouter();
const { documents, filters, total, loading, error, pageNumber, hasPrevious, hasNext, load, applyFilters, retryParse, retryIndex, deleteIndex, previousPage, nextPage } = useDocuments();
const { sources, load: loadSources } = useKnowledgeSources();
const { result: navigationResult, loading: navigationLoading, error: navigationError, search: navigationSearch, retry: navigationRetry } = useDocumentNavigation();
const selectedIds = shallowRef<number[]>([]);
const selectedDocument = shallowRef<DocumentRecord | null>(null);
const batchResult = shallowRef<BatchIndexResult | null>(null);
const batchError = shallowRef<string | null>(null);
const inspectorOpen = shallowRef(true);
const sourceId = computed(() => { const value = route?.query?.sourceId; const parsed = typeof value === "string" ? Number(value) : Number.NaN; return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null; });
const sourceNames = computed<Record<number, string>>(() => Object.fromEntries(sources.value.map((source) => [source.id, source.name])));
const currentSource = computed(() => sources.value.find((source) => source.id === sourceId.value) ?? null);
const canBatchIndex = computed(() => selectedIds.value.length > 0 && !loading.value);
const requestError = computed(() => error.value ?? batchError.value);
function selectSource(id: number | null): void { void router?.push({ path: "/documents", query: id ? { sourceId: String(id) } : {} }); }
function toggleSelect(id: number, selected: boolean): void { selectedIds.value = selected ? [...new Set([...selectedIds.value, id])] : selectedIds.value.filter((item) => item !== id); }
function selectDocument(document: DocumentRecord): void { selectedDocument.value = document; inspectorOpen.value = true; }
async function batchIndex(): Promise<void> { if (!canBatchIndex.value) return; batchError.value = null; try { batchResult.value = await documentsApi.batchIndex(selectedIds.value); selectedIds.value = []; await load(); } catch (cause) { batchError.value = cause instanceof Error ? cause.message : "批量建立索引失败"; } }
watch(sourceId, (nextSourceId) => { selectedIds.value = []; selectedDocument.value = null; void applyFilters({ ...filters, knowledgeSourceId: nextSourceId }); }, { immediate: true });
onMounted(() => { void loadSources(); });
</script>
<template>
  <section class="document-workspace">
    <DocumentWorkspaceSummary :source-name="currentSource?.name ?? null" :total="currentSource?.stats.total_files ?? total" :stats="currentSource?.stats ?? null" />
    <div class="workspace-grid">
      <div class="scope-surface"><DocumentScopeNav :sources="sources" :selected-source-id="sourceId" :total="total" @select="selectSource" /></div>
      <section class="main-surface" aria-label="文档列表">
        <DocumentNavigationPanel :sources="sources" :default-source-id="sourceId" :loading="navigationLoading" @search="navigationSearch" />
        <DocumentNavigationResults :result="navigationResult" :loading="navigationLoading" :error="navigationError" @retry="navigationRetry" />
        <DocumentFilters :filters="filters" :disabled="loading" @change="applyFilters" />
        <div v-if="selectedIds.length" class="bulk-toolbar"><span>已选择 {{ selectedIds.length }} 篇</span><button :disabled="!canBatchIndex" type="button" @click="batchIndex">批量建立索引</button></div>
        <p v-if="batchResult" class="result-message">批量结果：{{ batchResult.succeeded }} 成功，{{ batchResult.failed }} 失败。</p>
        <p v-if="requestError" class="error-message" role="alert">{{ requestError }} <button type="button" @click="load">重试</button></p>
        <DocumentTable :documents="documents" :disabled="loading" :selected-ids="selectedIds" :selected-document-id="selectedDocument?.id ?? null" :source-names="sourceNames" @toggle-select="toggleSelect" @select-document="selectDocument" @retry-parse="retryParse" @retry-index="retryIndex" @delete-index="deleteIndex" />
        <p v-if="documents.some((document) => document.error_message)" class="screen-reader-errors">{{ documents.map((document) => document.error_message).filter(Boolean).join(" ") }}</p>
        <footer class="pagination"><button :disabled="loading || !hasPrevious" type="button" @click="previousPage">上一页</button><span>第 {{ pageNumber }} 页 · 共 {{ total }} 篇</span><button :disabled="loading || !hasNext" type="button" @click="nextPage">下一页</button></footer>
      </section>
      <aside class="inspector-surface" :class="{ 'is-collapsed': !inspectorOpen }"><button class="inspector-toggle" type="button" :aria-expanded="inspectorOpen" @click="inspectorOpen = !inspectorOpen">{{ inspectorOpen ? "收起文档详情" : "展开文档详情" }}</button><DocumentInspector :disabled="loading" :document="selectedDocument" :source-name="selectedDocument ? sourceNames[selectedDocument.knowledge_source_id] ?? null : null" :scope-name="currentSource?.name ?? '全部文档'" :total="currentSource?.stats.total_files ?? total" @retry-index="retryIndex" @retry-parse="retryParse" /></aside>
    </div>
  </section>
</template>
<style scoped>
.document-workspace { padding: 4px 0 32px; }
.workspace-grid { display: grid; grid-template-columns: 244px minmax(640px, 1fr) 300px; align-items: start; border: 1px solid var(--border-subtle); border-top: 0; border-radius: 0 0 8px 8px; background: #fff; box-shadow: 0 10px 28px rgb(33 64 101 / 5%); }
.scope-surface, .main-surface, .inspector-surface { min-width: 0; }
.scope-surface, .inspector-surface { background: #fcfdff; }
.main-surface { border-left: 1px solid var(--border-subtle); border-right: 1px solid var(--border-subtle); }
.bulk-toolbar, .result-message, .error-message { display: flex; align-items: center; gap: 8px; margin: 0; padding: 8px 12px; font-size: 0.76rem; }
.bulk-toolbar { justify-content: space-between; border-bottom: 1px solid var(--border-subtle); background: var(--color-primary-soft); color: var(--color-primary); }
.bulk-toolbar button, .error-message button, .pagination button { border: 0; background: transparent; color: inherit; font: inherit; font-weight: 700; }
.result-message { color: var(--text-muted); }
.error-message { color: var(--color-danger); background: var(--color-danger-soft); }
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-top: 1px solid var(--border-subtle); color: var(--text-muted); font-size: 0.74rem; font-variant-numeric: tabular-nums; }
.pagination button { padding: 5px 8px; border: 1px solid var(--border-subtle); border-radius: 5px; background: #fff; color: var(--color-primary); }
.screen-reader-errors { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.inspector-toggle { display: none; }
@media (min-width: 1024px) and (max-width: 1199px) { .workspace-grid { grid-template-columns: 244px minmax(0, 1fr); } .inspector-surface { grid-column: 1 / -1; border-top: 1px solid var(--border-subtle); } .inspector-toggle { display: flex; justify-content: space-between; width: 100%; padding: 10px 12px; border: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: 0.78rem; font-weight: 700; text-align: left; } .inspector-surface.is-collapsed :deep(.inspector) { display: none; } }
@media (max-width: 1023px) { .workspace-grid { grid-template-columns: minmax(0, 1fr); border-top: 1px solid var(--border-subtle); } .scope-surface { border-bottom: 1px solid var(--border-subtle); } .main-surface { border: 0; } .inspector-surface { border-top: 1px solid var(--border-subtle); } .inspector-toggle { display: flex; justify-content: space-between; width: 100%; padding: 10px 12px; border: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: 0.78rem; font-weight: 700; text-align: left; } .inspector-surface.is-collapsed :deep(.inspector) { display: none; } }
@media (max-width: 700px) { .document-workspace { padding-top: 0; } .pagination { font-size: 0.7rem; } .bulk-toolbar { align-items: flex-start; flex-direction: column; } .workspace-grid { border-right: 0; border-left: 0; border-radius: 0; } .scope-surface { padding-left: 12px; } .main-surface { overflow: hidden; } }
@media (prefers-reduced-motion: no-preference) { .scope-surface :deep(.scope-item), .main-surface :deep(tbody tr) { transition: background-color 0.12s ease; } }
</style>
