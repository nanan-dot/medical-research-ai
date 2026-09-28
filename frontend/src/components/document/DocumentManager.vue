<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  DEFAULT_RESOURCE_LIBRARY_FILTERS,
  resourceLibraryApi,
  type ResourceLibraryFilters,
  type ResourceLibraryItem,
  type ResourceLibrarySummary,
  type ResourceSourceTree,
  type ResourceStorageSummary,
  type ResourceTreeNode,
} from "../../api/resourceLibrary";
import { useResourceLibrary } from "../../composables/useResourceLibrary";
import DocumentDetailsDrawer from "./DocumentDetailsDrawer.vue";
import DocumentFilterControls from "./DocumentFilters.vue";
import ResourceImportDialog from "./ResourceImportDialog.vue";
import DocumentScopeNav from "./DocumentScopeNav.vue";
import DocumentSummaryCards from "./DocumentSummaryCards.vue";
import ResourceTaskBanner from "./ResourceTaskBanner.vue";
import DocumentTable from "./DocumentTable.vue";

type SummarySelection = "all" | "processed" | "ai_available" | "processing" | "needs_attention";

const route = useRoute();
const router = useRouter();
const library = useResourceLibrary();
const summary = shallowRef<ResourceLibrarySummary | null>(null);
const sourceTree = shallowRef<ResourceSourceTree | null>(null);
const recentItems = shallowRef<ResourceLibraryItem[]>([]);
const storage = shallowRef<ResourceStorageSummary | null>(null);
const summaryLoading = shallowRef(true);
const railLoading = shallowRef(true);
const summaryError = shallowRef(false);
const railError = shallowRef(false);
const selectedIds = shallowRef<number[]>([]);
const highlightedDocumentId = shallowRef<number | null>(null);
const selectedDocument = shallowRef<ResourceLibraryItem | null>(null);
const actionMessage = shallowRef<string | null>(null);
const importOpen = shallowRef(false);
const sourceRailOpen = shallowRef(false);
let openIntentSequence = 0;
let processingRefreshTimer: ReturnType<typeof setInterval> | null = null;

const selectedSourceId = computed(() => sourceIdsFromRoute()[0] ?? null);
const selectedNodeId = computed(() => typeof route.query.nodeId === "string" ? route.query.nodeId : null);
const selectedTreeNode = computed(() => findTreeNode(sourceTree.value, selectedNodeId.value ?? (selectedSourceId.value ? `source:${selectedSourceId.value}` : null)));
const currentViewName = computed(() => selectedTreeNode.value?.name ?? (selectedSourceId.value ? `资料来源 #${selectedSourceId.value}` : "全部资料"));
const activeSummary = computed<SummarySelection>(() => {
  const status = library.filters.statuses[0];
  if (status === "ai_available" || status === "processing" || status === "needs_attention") return status;
  return "all";
});
const activeTasks = computed(() => library.items.value
  .filter((item) => item.task_status !== null)
  .map((item) => ({ id: item.id, displayName: item.display_name, taskStatus: item.task_status!, phase: item.phase, progress: item.progress })));
const hasProcessingItems = computed(() => library.items.value.some((item) => item.status === "processing"));
const hasSelectedItems = computed(() => selectedIds.value.length > 0);
const emptyMessage = computed(() => {
  if (library.filters.query || library.filters.sourceIds.length || library.filters.nodeId || library.filters.fileTypes.length || library.filters.statuses.length) return "没有找到符合当前条件的资料。可以清除搜索或筛选后重试。";
  return selectedSourceId.value ? "该资料来源暂无资料。" : "资料库为空。导入资料后可在这里查看处理状态。";
});

function positiveInteger(value: unknown): number | null {
  const parsed = typeof value === "string" ? Number(value) : Number.NaN;
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function csv(value: unknown, allowed: readonly string[]): string[] {
  if (typeof value !== "string") return [];
  return [...new Set(value.split(",").filter((entry) => allowed.includes(entry)))];
}

function sourceIdsFromRoute(): number[] {
  const raw = typeof route.query.sourceIds === "string" ? route.query.sourceIds : route.query.sourceId;
  if (typeof raw !== "string") return [];
  return [...new Set(raw.split(",").map(positiveInteger).filter((value): value is number => value !== null))];
}

function pageSize(value: unknown): 25 | 50 | 100 {
  return value === "50" || value === "100" ? Number(value) as 50 | 100 : 25;
}

function filtersFromRoute(): ResourceLibraryFilters {
  const sortBy = typeof route.query.sort === "string" && ["updated_at", "name", "file_size", "source_name", "status", "last_opened"].includes(route.query.sort)
    ? route.query.sort as ResourceLibraryFilters["sortBy"]
    : "updated_at";
  return {
    ...DEFAULT_RESOURCE_LIBRARY_FILTERS,
    query: typeof route.query.q === "string" ? route.query.q.slice(0, 200) : "",
    sourceIds: sourceIdsFromRoute(),
    nodeId: typeof route.query.nodeId === "string" && route.query.nodeId.startsWith("tree:") ? route.query.nodeId : null,
    fileTypes: csv(route.query.types, ["pdf", "pptx", "docx", "markdown", "txt", "other"]) as ResourceLibraryFilters["fileTypes"],
    statuses: csv(route.query.statuses, ["ai_available", "processing", "needs_processing", "outdated", "needs_attention", "metadata_only"]) as ResourceLibraryFilters["statuses"],
    updatedFrom: typeof route.query.updatedFrom === "string" && /^\d{4}-\d{2}-\d{2}$/.test(route.query.updatedFrom) ? route.query.updatedFrom : null,
    updatedTo: typeof route.query.updatedTo === "string" && /^\d{4}-\d{2}-\d{2}$/.test(route.query.updatedTo) ? route.query.updatedTo : null,
    sortBy,
    sortOrder: route.query.order === "asc" ? "asc" : "desc",
  };
}

function copyFilters(filters: {
  readonly query: string;
  readonly sourceIds: readonly number[];
  readonly nodeId: string | null;
  readonly fileTypes: readonly ResourceLibraryFilters["fileTypes"][number][];
  readonly statuses: readonly ResourceLibraryFilters["statuses"][number][];
  readonly updatedFrom: string | null;
  readonly updatedTo: string | null;
  readonly sortBy: ResourceLibraryFilters["sortBy"];
  readonly sortOrder: ResourceLibraryFilters["sortOrder"];
}): ResourceLibraryFilters {
  return {
    ...filters,
    sourceIds: [...filters.sourceIds],
    fileTypes: [...filters.fileTypes],
    statuses: [...filters.statuses],
  };
}

function routeQuery(filters: ResourceLibraryFilters, page = 1, nextDocumentId: number | null = positiveInteger(route.query.documentId)): Record<string, string> {
  const query: Record<string, string> = {
    sort: filters.sortBy,
    order: filters.sortOrder,
    page: String(Math.max(1, page)),
    pageSize: String(pageSize(route.query.pageSize)),
  };
  if (filters.sourceIds.length) query.sourceIds = filters.sourceIds.join(",");
  if (filters.nodeId) query.nodeId = filters.nodeId;
  if (filters.query) query.q = filters.query;
  if (filters.fileTypes.length) query.types = filters.fileTypes.join(",");
  if (filters.statuses.length) query.statuses = filters.statuses.join(",");
  if (filters.updatedFrom) query.updatedFrom = filters.updatedFrom;
  if (filters.updatedTo) query.updatedTo = filters.updatedTo;
  if (nextDocumentId) query.documentId = String(nextDocumentId);
  return query;
}

function findTreeNode(tree: ResourceSourceTree | null, nodeId: string | null): ResourceTreeNode | null {
  if (!tree || !nodeId) return null;
  const find = (nodes: readonly ResourceTreeNode[]): ResourceTreeNode | null => {
    for (const node of nodes) {
      if (node.node_id === nodeId) return node;
      const child = find(node.children);
      if (child) return child;
    }
    return null;
  };
  for (const group of tree.groups) {
    const found = find(group.children);
    if (found) return found;
  }
  return null;
}

async function loadChrome(): Promise<void> {
  summaryLoading.value = true;
  railLoading.value = true;
  summaryError.value = false;
  railError.value = false;
  const [summaryResult, treeResult, recentResult, storageResult] = await Promise.allSettled([
    resourceLibraryApi.summary(),
    resourceLibraryApi.sourceTree(),
    resourceLibraryApi.recent(5),
    resourceLibraryApi.storage(),
  ]);
  if (summaryResult.status === "fulfilled") summary.value = summaryResult.value;
  else summaryError.value = true;
  if (treeResult.status === "fulfilled") sourceTree.value = treeResult.value;
  if (recentResult.status === "fulfilled") recentItems.value = recentResult.value.items;
  if (storageResult.status === "fulfilled") storage.value = storageResult.value;
  if (treeResult.status === "rejected" || recentResult.status === "rejected" || storageResult.status === "rejected") railError.value = true;
  summaryLoading.value = false;
  railLoading.value = false;
}

async function loadFromRoute(): Promise<void> {
  const filters = filtersFromRoute();
  const requestedPage = Math.max(1, Number(route.query.page) || 1);
  const requestedPageSize = pageSize(route.query.pageSize);
  selectedIds.value = [];
  await library.loadPage(filters, (requestedPage - 1) * requestedPageSize, requestedPageSize);
}

function updateRoute(filters: ResourceLibraryFilters, page = 1, documentId: number | null = positiveInteger(route.query.documentId), replace = false): void {
  const destination = { path: "/documents", query: routeQuery(filters, page, documentId) };
  if (replace) void router.replace(destination);
  else void router.push(destination);
}

function changeFilters(filters: ResourceLibraryFilters): void {
  updateRoute(filters, 1, null);
}

function selectAll(): void {
  sourceRailOpen.value = false;
  updateRoute({ ...copyFilters(library.filters), sourceIds: [], nodeId: null }, 1, null);
}

function selectNode(node: ResourceTreeNode): void {
  const nodeId = node.node_id.startsWith("tree:") ? node.node_id : null;
  if (!node.source_id) return;
  sourceRailOpen.value = false;
  updateRoute({ ...copyFilters(library.filters), sourceIds: [node.source_id], nodeId }, 1, null);
}

function selectSummary(selection: SummarySelection): void {
  if (selection === "processed") {
    actionMessage.value = "已解析资料的服务端筛选暂未提供，当前保持原筛选条件。";
    return;
  }
  changeFilters({ ...copyFilters(library.filters), statuses: selection === "all" ? [] : [selection] });
}

function changePage(nextPage: number): void {
  updateRoute(copyFilters(library.filters), nextPage, null);
}

function changePageSize(event: Event): void {
  const nextPageSize = pageSize((event.target as HTMLSelectElement).value);
  void router.push({ path: "/documents", query: { ...routeQuery(copyFilters(library.filters), 1, null), pageSize: String(nextPageSize) } });
}

function toggleSelect(id: number, selected: boolean): void {
  selectedIds.value = selected ? [...new Set([...selectedIds.value, id])] : selectedIds.value.filter((item) => item !== id);
}

function mutableItem(document: Readonly<ResourceLibraryItem>): ResourceLibraryItem {
  return { ...document, match_fields: [...document.match_fields] };
}

async function openDocument(document: Readonly<ResourceLibraryItem>): Promise<void> {
  const intent = ++openIntentSequence;
  const selected = mutableItem(document);
  selectedDocument.value = selected;
  highlightedDocumentId.value = document.id;
  if (positiveInteger(route.query.documentId) !== document.id) updateRoute(copyFilters(library.filters), library.pageNumber.value, document.id);
  try {
    await resourceLibraryApi.markOpened(document.id, `resource-library-open-${document.id}-${Date.now()}`);
    const recent = await resourceLibraryApi.recent(5);
    if (intent === openIntentSequence) recentItems.value = recent.items;
  } catch {
    if (intent === openIntentSequence) {
      actionMessage.value = "已打开资料，但最近使用记录暂时无法更新。";
    }
  }
}

async function openDeepLinkedDocument(): Promise<void> {
  const documentId = positiveInteger(route.query.documentId);
  if (!documentId || selectedDocument.value?.id === documentId) return;
  const listed = library.items.value.find((item) => item.id === documentId);
  if (listed) await openDocument(listed);
  else {
    try {
      const item = await resourceLibraryApi.item(documentId);
      await openDocument(item);
    } catch {
      actionMessage.value = "请求的资料不存在或暂不可访问。";
      updateRoute(copyFilters(library.filters), library.pageNumber.value, null, true);
    }
  }
}

function closeDocument(): void {
  openIntentSequence += 1;
  selectedDocument.value = null;
  updateRoute(copyFilters(library.filters), library.pageNumber.value, null);
}

async function submitAction(document: Readonly<ResourceLibraryItem>, action: "repair" | "reprocess"): Promise<void> {
  actionMessage.value = "正在提交处理任务…";
  try {
    const result = action === "repair" ? await resourceLibraryApi.repair(document.id) : await resourceLibraryApi.reprocess(document.id);
    actionMessage.value = `已提交处理任务 #${result.task_id}。`;
    await Promise.all([loadFromRoute(), loadChrome()]);
  } catch (caught) {
    actionMessage.value = caught instanceof Error ? caught.message : "处理任务提交失败";
  }
}

function sort(sortBy: ResourceLibraryFilters["sortBy"]): void {
  const sortOrder = library.filters.sortBy === sortBy && library.filters.sortOrder === "desc" ? "asc" : "desc";
  changeFilters({ ...copyFilters(library.filters), sortBy, sortOrder });
}

function openTask(documentId: number): void {
  void router.push({ path: "/tasks", query: { documentId: String(documentId) } });
}

function manageSources(): void {
  void router.push("/sources");
}

function openImport(): void {
  importOpen.value = true;
}

watch(() => route.query, () => { void loadFromRoute(); }, { immediate: true, deep: true });
watch([() => route.query.documentId, library.items], () => { void openDeepLinkedDocument(); });
watch(hasProcessingItems, (isProcessing) => {
  if (processingRefreshTimer) clearInterval(processingRefreshTimer);
  processingRefreshTimer = isProcessing
    ? setInterval(() => { void Promise.all([loadFromRoute(), loadChrome()]); }, 3_000)
    : null;
}, { immediate: true });

onMounted(() => { void loadChrome(); });
onBeforeUnmount(() => {
  if (processingRefreshTimer) clearInterval(processingRefreshTimer);
  library.cancel();
});

defineExpose({ openImport, manageSources });
</script>

<template>
  <section class="document-library">
    <DocumentSummaryCards :summary="summary" :loading="summaryLoading" :error="summaryError" :active="activeSummary" @select="selectSummary" />
    <p v-if="summaryError" class="notice notice-warning" role="alert">统计暂不可用。<button type="button" @click="loadChrome">重新加载</button></p>

    <div class="workbench">
      <aside class="source-nav" :class="{ 'is-open': sourceRailOpen }"><button class="rail-close" type="button" aria-label="关闭资料来源" @click="sourceRailOpen = false">×</button><DocumentScopeNav :tree="sourceTree" :recent-items="recentItems" :selected-node-id="selectedNodeId ?? (selectedSourceId ? `source:${selectedSourceId}` : null)" :total="summary?.total ?? null" :loading="railLoading" :storage="storage" @select-all="selectAll" @select-node="selectNode" @open-recent="openDocument" @manage-sources="manageSources" /><p v-if="railError" class="rail-error" role="alert">部分资料来源暂不可用。</p></aside>
      <main class="document-pane" aria-label="资料工作区">
        <header class="pane-heading"><div><span class="context-mark" aria-hidden="true">▰</span><h2>当前视图：{{ currentViewName }}</h2><small>共 {{ library.total.value }} 份资料</small></div><div class="pane-actions"><button class="rail-toggle" type="button" :aria-expanded="sourceRailOpen" @click="sourceRailOpen = true">资料来源</button></div></header>
        <ResourceTaskBanner :tasks="activeTasks" :total="library.total.value" @open-task="openTask" />
        <DocumentFilterControls :filters="library.filters" :facets="library.facets.value" :disabled="library.loading.value" @change="changeFilters" />
        <p v-if="actionMessage" class="notice" role="status">{{ actionMessage }}</p>
        <div v-if="hasSelectedItems" class="bulk-toolbar"><span>已选择 {{ selectedIds.length }} 份</span><span>跨资料批量修复、重新处理和删除需要后端 selection token，当前不可用。</span><button type="button" disabled title="后端尚未提供批量操作语义">批量操作暂不可用</button></div>
        <p v-if="library.error.value" class="notice notice-error" role="alert">{{ library.error.value }} <button type="button" @click="loadFromRoute">重试</button></p>
        <DocumentTable :documents="library.items.value" :disabled="library.loading.value" :selected-ids="selectedIds" :selected-document-id="highlightedDocumentId" :empty-message="emptyMessage" :sort-by="library.filters.sortBy" :sort-order="library.filters.sortOrder" @toggle-select="toggleSelect" @highlight-document="highlightedDocumentId = $event.id" @select-document="openDocument" @repair="submitAction($event, 'repair')" @reprocess="submitAction($event, 'reprocess')" @sort="sort" />
        <footer class="pagination"><span>共 {{ library.total.value }} 份资料</span><div><button :disabled="library.loading.value || !library.hasPrevious.value" type="button" @click="changePage(library.pageNumber.value - 1)">上一页</button><span>第 {{ library.pageNumber.value }} 页</span><button :disabled="library.loading.value || !library.hasNext.value" type="button" @click="changePage(library.pageNumber.value + 1)">下一页</button></div><label>每页<select :value="library.limit.value" :disabled="library.loading.value" @change="changePageSize"><option value="25">25</option><option value="50">50</option><option value="100">100</option></select></label></footer>
      </main>
    </div>
    <DocumentDetailsDrawer :document="selectedDocument" :disabled="library.loading.value" :source-name="selectedDocument?.source_name ?? null" :scope-name="currentViewName" :total="library.total.value" @close="closeDocument" @retry-index="submitAction($event as ResourceLibraryItem, 'reprocess')" @retry-parse="submitAction($event as ResourceLibraryItem, 'repair')" />
    <ResourceImportDialog :open="importOpen" @close="importOpen = false" @imported="loadChrome(); loadFromRoute()" />
  </section>
</template>

<style scoped>
.document-library { padding:2px 0 32px; }.workbench { display:grid; grid-template-columns:280px minmax(0,1fr); min-height:calc(100vh - 300px); overflow:hidden; border:1px solid var(--border-subtle); border-radius:8px; background:var(--surface); box-shadow:var(--shadow-sm, 0 1px 2px rgb(15 23 42 / 4%)); }.source-nav { position:relative; min-width:0; border-right:1px solid var(--border-subtle); background:var(--elevated, #fbfcfe); }.rail-close,.rail-toggle { display:none; }.rail-error { position:absolute; right:10px; bottom:52px; left:10px; margin:0; color:var(--color-warning); font-size:11px; }.document-pane { min-width:0; }.pane-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:64px; padding:0 16px; border-bottom:1px solid var(--border-subtle); }.pane-heading > div { display:flex; min-width:0; align-items:center; gap:8px; }.context-mark { display:grid; width:26px; height:26px; flex:0 0 auto; place-items:center; border-radius:4px; background:var(--color-primary-soft); color:var(--color-primary); font-size:12px; }.pane-heading h2 { overflow:hidden; margin:0; color:var(--text-primary); font-size:16px; text-overflow:ellipsis; white-space:nowrap; }.pane-heading small { color:var(--text-muted); font-size:12px; font-variant-numeric:tabular-nums; white-space:nowrap; }.pane-actions { flex:0 0 auto; }.pane-actions button { min-height:34px; border-radius:4px; padding:0 10px; font:inherit; font-size:12px; font-weight:700; cursor:pointer; }.rail-toggle { border:1px solid var(--border-subtle); background:var(--surface); color:var(--text-primary); }.notice { margin:0; padding:8px 12px; border-bottom:1px solid var(--border-subtle); color:var(--text-muted); font-size:12px; }.notice button { margin-left:4px; border:0; background:transparent; color:inherit; font:inherit; font-weight:700; text-decoration:underline; cursor:pointer; }.notice-warning { background:var(--color-warning-soft); color:var(--color-warning); }.notice-error { background:var(--color-danger-soft); color:var(--color-danger); }.bulk-toolbar { position:sticky; z-index:30; top:0; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:8px 12px; border-bottom:1px solid var(--border-subtle); background:var(--color-primary-soft); color:var(--color-primary); font-size:12px; font-weight:650; }.bulk-toolbar button { border:1px solid currentColor; border-radius:4px; padding:4px 8px; background:var(--surface); color:inherit; font:inherit; font-size:12px; cursor:not-allowed; }.pagination { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 12px; border-top:1px solid var(--border-subtle); color:var(--text-muted); font-size:12px; font-variant-numeric:tabular-nums; }.pagination > div { display:flex; align-items:center; gap:8px; }.pagination button,.pagination select { min-height:30px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); color:var(--text-primary); font:inherit; font-size:12px; }.pagination button { padding:0 8px; cursor:pointer; }.pagination button:disabled { color:var(--text-faint); cursor:not-allowed; }.pagination label { display:flex; align-items:center; gap:4px; }.pagination select { padding:0 4px; }@media(max-width:1439px){.workbench{grid-template-columns:248px minmax(0,1fr)}}@media(max-width:1023px){.workbench{grid-template-columns:minmax(0,1fr)}.source-nav{display:none}.source-nav.is-open{position:fixed;z-index:50;top:0;bottom:0;left:0;display:block;width:min(360px,calc(100vw - 48px));overflow:auto;box-shadow:var(--shadow-md, 8px 0 24px rgb(15 23 42 / 8%));}.rail-close{position:absolute;z-index:1;top:10px;right:10px;display:grid;width:32px;height:32px;place-items:center;border:1px solid var(--border-subtle);border-radius:4px;background:var(--surface);font:inherit;cursor:pointer}.rail-toggle{display:inline-flex;align-items:center}.pane-heading{min-height:60px}}@media(max-width:767px){.document-library{margin:0 -16px}.workbench{min-height:calc(100vh - 190px);border-right:0;border-left:0;border-radius:0}.pane-heading{align-items:flex-start;padding:12px}.pane-heading h2{font-size:14px}.pane-heading small{display:none}.rail-toggle{min-height:44px !important}.pagination{flex-wrap:wrap}.bulk-toolbar{align-items:flex-start;flex-direction:column}}@media(prefers-reduced-motion:reduce){.workbench{scroll-behavior:auto}}
.document-library { width:100%; min-width:0; }
.workbench { width:100%; min-width:0; min-height:0; }
@media(max-width:767px){.document-library{margin:0}.workbench{min-height:0;border:1px solid var(--border-subtle);border-radius:8px}}
</style>
