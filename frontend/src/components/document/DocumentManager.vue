<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  documentsApi,
  type BatchIndexResult,
  type DocumentFilters,
  type DocumentRecord,
  type DocumentStatistics,
} from "../../api/documents";
import { useDocuments } from "../../composables/useDocuments";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";
import DocumentDetailsDrawer from "./DocumentDetailsDrawer.vue";
import DocumentFilterControls from "./DocumentFilters.vue";
import DocumentScopeNav from "./DocumentScopeNav.vue";
import DocumentSummaryCards from "./DocumentSummaryCards.vue";
import DocumentTable from "./DocumentTable.vue";

const route = useRoute();
const router = useRouter();
const {
  documents,
  filters,
  total,
  loading,
  error,
  pageNumber,
  hasPrevious,
  hasNext,
  load,
  applyFilters,
  retryParse,
  retryIndex,
  goToPage,
} = useDocuments();
const { sources, error: sourceError, load: loadSources } = useKnowledgeSources();

const selectedIds = shallowRef<number[]>([]);
const selectedDocument = shallowRef<DocumentRecord | null>(null);
const summary = shallowRef<DocumentStatistics | null>(null);
const summaryError = shallowRef(false);
const summaryLoading = shallowRef(true);
const batchResult = shallowRef<BatchIndexResult | null>(null);
const batchError = shallowRef<string | null>(null);
const recentSourceIds = shallowRef<number[]>([]);
const RECENT_SOURCE_STORAGE_KEY = "rag-medicine.document-library.recent-source-ids";

const sourceId = computed(() => parsePositiveInteger(route?.query?.sourceId));
const currentSource = computed(() => sources.value.find((source) => source.id === sourceId.value) ?? null);
const sourceNames = computed<Record<number, string>>(() => Object.fromEntries(sources.value.map((source) => [source.id, source.name])));
const activeSummary = computed<"all" | "available" | "processing" | "needs_attention">(() => filters.healthStatus || "all");
const canBatchIndex = computed(() => selectedIds.value.length > 0 && !loading.value);
const requestError = computed(() => error.value ?? batchError.value);
const contextName = computed(() => currentSource.value?.name ?? "全部文档");
const emptyMessage = computed(() => {
  if (filters.query || filters.fileType || filters.healthStatus) return "没有找到匹配文档。请调整搜索词或筛选条件。";
  return sourceId.value ? "该知识来源暂无同步文档。" : "还没有可浏览的科研文档。请先在知识库中同步资料来源。";
});

function parsePositiveInteger(value: unknown): number | null {
  const parsed = typeof value === "string" ? Number(value) : Number.NaN;
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function queryFor(next: DocumentFilters = filters, page = 1): Record<string, string> {
  const query: Record<string, string> = {
    view: next.knowledgeSourceId ? "source" : "all",
    sort: `${next.sortBy}_${next.sortOrder}`,
    page: String(Math.max(page, 1)),
    pageSize: "25",
  };
  if (next.knowledgeSourceId) query.sourceId = String(next.knowledgeSourceId);
  if (next.query.trim()) query.q = next.query.trim();
  if (next.fileType) query.type = next.fileType;
  if (next.healthStatus) query.status = next.healthStatus;
  return query;
}

function rememberSource(sourceId: number): void {
  const nextIds = [sourceId, ...recentSourceIds.value.filter((id) => id !== sourceId)].slice(0, 4);
  recentSourceIds.value = nextIds;
  try {
    globalThis.localStorage.setItem(RECENT_SOURCE_STORAGE_KEY, JSON.stringify(nextIds));
  } catch {
    // 隐私模式或受限浏览器无法持久化时，当前会话内的真实选择仍可显示。
  }
}

function selectSource(nextSourceId: number | null): void {
  if (nextSourceId) rememberSource(nextSourceId);
  void router.push({ path: "/documents", query: queryFor({ ...filters, knowledgeSourceId: nextSourceId }, 1) });
}

function applyLibraryFilters(next: DocumentFilters): void {
  void router.replace({ path: "/documents", query: queryFor(next, 1) });
}

function toggleSelect(id: number, selected: boolean): void {
  selectedIds.value = selected ? [...new Set([...selectedIds.value, id])] : selectedIds.value.filter((item) => item !== id);
}

async function loadSummary(): Promise<void> {
  summaryLoading.value = true;
  summaryError.value = false;
  try {
    summary.value = await documentsApi.statistics();
  } catch {
    summary.value = null;
    summaryError.value = true;
  } finally {
    summaryLoading.value = false;
  }
}

function selectSummary(status: "all" | "available" | "processing" | "needs_attention"): void {
  applyLibraryFilters({ ...filters, healthStatus: status === "all" ? "" : status });
}

async function batchIndex(): Promise<void> {
  if (!canBatchIndex.value) return;
  batchError.value = null;
  try {
    batchResult.value = await documentsApi.batchIndex(selectedIds.value);
    selectedIds.value = [];
    await Promise.all([load(), loadSummary()]);
  } catch (caught) {
    batchError.value = caught instanceof Error ? caught.message : "批量建立索引失败";
  }
}

async function repair(document: DocumentRecord): Promise<void> {
  try {
    await documentsApi.repair(document.id);
    await Promise.all([load(), loadSummary()]);
  } catch (caught) {
    batchError.value = caught instanceof Error ? caught.message : "修复任务提交失败";
  }
}

function changePage(direction: "previous" | "next"): void {
  if (direction === "previous" && hasPrevious.value) void router.push({ path: "/documents", query: queryFor(filters, pageNumber.value - 1) });
  if (direction === "next" && hasNext.value) void router.push({ path: "/documents", query: queryFor(filters, pageNumber.value + 1) });
}

watch(() => route?.query ?? {}, (query) => {
  const sort = typeof query.sort === "string" ? query.sort.split("_") : ["updated_at", "desc"];
  const next: DocumentFilters = {
    ...filters,
    mode: "document",
    knowledgeSourceId: parsePositiveInteger(query.sourceId),
    query: typeof query.q === "string" ? query.q.slice(0, 200) : "",
    fileType: ["pdf", "pptx", "docx", "markdown", "txt", "other"].includes(String(query.type)) ? query.type as DocumentFilters["fileType"] : "",
    healthStatus: ["available", "processing", "needs_attention"].includes(String(query.status)) ? query.status as DocumentFilters["healthStatus"] : "",
    sortBy: ["updated_at", "name", "file_size"].includes(sort[0]) ? sort[0] as DocumentFilters["sortBy"] : "updated_at",
    sortOrder: sort[1] === "asc" ? "asc" : "desc",
  };
  const page = Math.max(1, Number(query.page) || 1);
  selectedIds.value = [];
  selectedDocument.value = null;
  void applyFilters(next).then(() => page > 1 ? goToPage(page) : undefined);
}, { immediate: true, deep: true });

watch([sources, sourceId], ([items, id]) => {
  if (id && items.length && !items.some((source) => source.id === id)) selectSource(null);
});

onMounted(async () => {
  try {
    const stored = JSON.parse(globalThis.localStorage.getItem(RECENT_SOURCE_STORAGE_KEY) ?? "[]") as unknown;
    recentSourceIds.value = Array.isArray(stored)
      ? stored.filter((id): id is number => Number.isSafeInteger(id) && id > 0).slice(0, 4)
      : [];
  } catch {
    recentSourceIds.value = [];
  }
  await loadSources();
  // 首次进入使用真实来源作为工作台上下文；来源树内的“全部文档”仍可选择。
  if (!sourceId.value && sources.value[0]) selectSource(recentSourceIds.value.find((id) => sources.value.some((source) => source.id === id)) ?? sources.value[0].id);
  void loadSummary();
});
</script>

<template>
  <section class="document-library">
    <DocumentSummaryCards :summary="summary" :loading="summaryLoading" :error="summaryError" :active="activeSummary" @select="selectSummary" />
    <p v-if="summaryError" class="notice notice-warning" role="alert">统计暂时无法加载。<button type="button" @click="loadSummary">重新加载</button></p>

    <div class="workbench has-source-nav">
      <aside class="source-nav"><DocumentScopeNav :sources="sources" :selected-source-id="sourceId" :recent-source-ids="recentSourceIds" :total="summary?.total ?? total" @select="selectSource" /></aside>
      <main class="document-pane" aria-label="文档工作区">
        <header class="pane-heading">
          <div><span class="context-mark" aria-hidden="true">▰</span><h3>{{ contextName }}</h3><small>{{ total }} 篇文档</small></div>
          <div class="pane-actions"><RouterLink v-if="currentSource" to="/sources">查看知识来源</RouterLink></div>
        </header>
        <DocumentFilterControls :filters="filters" :disabled="loading" @change="applyLibraryFilters" />
        <div v-if="selectedIds.length" class="bulk-toolbar"><span>已选择 {{ selectedIds.length }} 篇文档</span><button :disabled="!canBatchIndex" type="button" @click="batchIndex">建立索引</button></div>
        <p v-if="batchResult" class="notice">批量处理完成：{{ batchResult.succeeded }} 成功，{{ batchResult.failed }} 失败。</p>
        <p v-if="sourceError" class="notice notice-warning" role="alert">知识来源暂时无法加载。<button type="button" @click="loadSources">重新加载</button></p>
        <p v-if="requestError" class="notice notice-error" role="alert">{{ requestError }} <button type="button" @click="load">重试</button></p>

        <DocumentTable :documents="documents" :disabled="loading" :selected-ids="selectedIds" :selected-document-id="selectedDocument?.id ?? null" :source-names="sourceNames" :empty-message="emptyMessage" @toggle-select="toggleSelect" @select-document="selectedDocument = $event" @repair="repair" @retry-parse="retryParse" @retry-index="retryIndex" />

        <footer class="pagination"><button :disabled="loading || !hasPrevious" type="button" @click="changePage('previous')">上一页</button><span>第 {{ pageNumber }} 页 / 共 {{ total }} 篇</span><button :disabled="loading || !hasNext" type="button" @click="changePage('next')">下一页</button></footer>
      </main>
    </div>

    <DocumentDetailsDrawer :document="selectedDocument" :disabled="loading" :source-name="selectedDocument ? sourceNames[selectedDocument.knowledge_source_id] ?? null : null" :scope-name="contextName" :total="total" @close="selectedDocument = null" @retry-index="retryIndex" @retry-parse="retryParse" />
  </section>
</template>

<style scoped>
.document-library { padding: 2px 0 32px; }
.workbench { display: grid; grid-template-columns: 224px minmax(0, 1fr); overflow: hidden; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--surface); box-shadow: var(--shadow); }.source-nav { min-width: 0; background: #fcfdff; border-right: 1px solid var(--border-subtle); }.document-pane { min-width: 0; }.pane-heading { display: flex; align-items: center; justify-content: space-between; min-height: 56px; padding: 0 16px; border-bottom: 1px solid var(--border-subtle); }.pane-heading > div { display: flex; align-items: center; gap: 8px; min-width: 0; }.pane-actions { display: flex; align-items: center; gap: 10px; }.context-mark { display: grid; width: 25px; height: 25px; place-items: center; border-radius: 7px; background: var(--color-primary-soft); color: var(--color-primary); font-size: .78rem; }.pane-heading h3 { overflow: hidden; margin: 0; color: var(--text-primary); font-size: .92rem; text-overflow: ellipsis; white-space: nowrap; }.pane-heading small { color: var(--text-muted); font-size: .72rem; white-space: nowrap; }.pane-heading a { color: var(--color-primary); font-size: .74rem; font-weight: 700; text-decoration: none; }
.notice { margin: 0; padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); font-size: .75rem; }.notice button { margin-left: 5px; border: 0; background: transparent; color: inherit; font: inherit; font-weight: 800; text-decoration: underline; cursor: pointer; }.notice-warning { background: #fffaf0; color: #9a6700; }.notice-error { background: var(--color-danger-soft); color: var(--color-danger); }.bulk-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); background: var(--color-primary-soft); color: var(--color-primary); font-size: .75rem; font-weight: 700; }.bulk-toolbar button { border: 1px solid currentColor; border-radius: 6px; padding: 4px 8px; background: var(--surface); color: inherit; font: inherit; font-weight: 800; cursor: pointer; }
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-top: 1px solid var(--border-subtle); color: var(--text-muted); font-size: .73rem; font-variant-numeric: tabular-nums; }.pagination button { border: 1px solid var(--border-subtle); border-radius: 6px; padding: 5px 8px; background: var(--surface); color: var(--color-primary); font: inherit; font-weight: 700; cursor: pointer; }.pagination button:disabled { color: var(--text-faint); cursor: not-allowed; }
@media (max-width: 900px) { .workbench.has-source-nav { grid-template-columns: minmax(0, 1fr); }.source-nav { display: none; } }
@media (max-width: 640px) { .document-library { margin: 0 -1rem; }.workbench { border-right: 0; border-left: 0; border-radius: 0; }.pane-heading { padding: 0 12px; }.pane-heading a { display: none; }.pagination { font-size: .68rem; } }
</style>
