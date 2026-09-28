<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { knowledgeSourcesApi, type CreateKnowledgeSource, type KnowledgeSource, type KnowledgeSourceHealth, type KnowledgeSourceSort } from "../../api/knowledgeSources";
import { useKnowledgeSourceActions } from "../../composables/useKnowledgeSourceActions";
import { KNOWLEDGE_SOURCE_SEARCH_DEBOUNCE_MS, useKnowledgeSources } from "../../composables/useKnowledgeSources";
import ConfirmDialog from "../ui/ConfirmDialog.vue";
import KnowledgeBaseHeader from "./KnowledgeBaseHeader.vue";
import KnowledgeIssueAlert from "./KnowledgeIssueAlert.vue";
import KnowledgeReadinessSummary from "./KnowledgeReadinessSummary.vue";
import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";
import KnowledgeSourceRow from "./KnowledgeSourceRow.vue";
import KnowledgeSourceToolbar from "./KnowledgeSourceToolbar.vue";

const PAGE_SIZE = 10;
const route = useRoute();
const router = useRouter();
const { items, summary, total, isLoading, error, load, replaceItem } = useKnowledgeSources();
const { pendingAction, actionError, togglePinned, toggleAutoSync, sync, remove } = useKnowledgeSourceActions(replaceItem);
const search = shallowRef("");
const sort = shallowRef<KnowledgeSourceSort>("last_opened");
const filter = shallowRef<"all" | "local" | "obsidian" | "issues">("all");
const page = shallowRef(1);
const isAddOpen = shallowRef(false);
const isDeleteOpen = shallowRef(false);
const isFilterOpen = shallowRef(false);
const selectedSource = shallowRef<KnowledgeSource | null>(null);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const sourceType = computed<"local_folder" | "obsidian_vault" | undefined>(() => filter.value === "local" ? "local_folder" : filter.value === "obsidian" ? "obsidian_vault" : undefined);
const healthStatus = computed<KnowledgeSourceHealth | undefined>(() => filter.value === "issues" ? "needs_attention" : undefined);
const query = computed(() => ({ q: search.value, sourceType: sourceType.value, healthStatus: healthStatus.value, sortBy: sort.value, sortOrder: "desc" as const, offset: (page.value - 1) * PAGE_SIZE, limit: PAGE_SIZE }));

function updateUrl(): void {
  void router.replace({ query: { ...(search.value ? { q: search.value } : {}), ...(filter.value !== "all" ? { filter: filter.value } : {}), ...(sort.value !== "last_opened" ? { sort: sort.value } : {}), ...(page.value > 1 ? { page: String(page.value) } : {}) } });
}
function reload(): void { void load(query.value); }
function scheduleSearch(): void { if (searchTimer) clearTimeout(searchTimer); searchTimer = setTimeout(() => { page.value = 1; updateUrl(); reload(); }, KNOWLEDGE_SOURCE_SEARCH_DEBOUNCE_MS); }
function changeFilter(next: typeof filter.value): void { filter.value = next; page.value = 1; updateUrl(); reload(); }
function changeSort(next: KnowledgeSourceSort): void { sort.value = next; page.value = 1; updateUrl(); reload(); }
function changePage(next: number): void { page.value = Math.min(Math.max(next, 1), totalPages.value); updateUrl(); reload(); }
function openDelete(source: KnowledgeSource): void { selectedSource.value = source; isDeleteOpen.value = true; }
async function confirmDelete(): Promise<void> { if (!selectedSource.value) return; if (await remove(selectedSource.value)) { isDeleteOpen.value = false; selectedSource.value = null; reload(); } }
function viewSource(source: KnowledgeSource): void { void router.push({ path: "/documents", query: { knowledge_source_id: String(source.id) } }); }
function viewIssues(): void { void router.push({ path: "/documents", query: { needs_attention: "true" } }); }
async function createSource(payload: CreateKnowledgeSource): Promise<void> {
  // 创建始终交给真实 API；失败时保留表单，避免把本地目录误显示为已接入。
  await knowledgeSourcesApi.create(payload);
  isAddOpen.value = false;
  reload();
}

watch(search, scheduleSearch);
onMounted(() => { search.value = typeof route.query.q === "string" ? route.query.q : ""; filter.value = ["all", "local", "obsidian", "issues"].includes(String(route.query.filter)) ? route.query.filter as typeof filter.value : "all"; sort.value = ["pinned", "last_sync", "last_opened", "name", "document_count"].includes(String(route.query.sort)) ? route.query.sort as KnowledgeSourceSort : "last_opened"; page.value = Math.max(1, Number(route.query.page) || 1); reload(); });
onBeforeUnmount(() => { if (searchTimer) clearTimeout(searchTimer); });
</script>
<template>
  <section data-testid="knowledge-source-manager">
    <KnowledgeBaseHeader @add="isAddOpen = true" />
    <KnowledgeReadinessSummary
      :summary="summary"
      :loading="isLoading"
    />
    <KnowledgeIssueAlert
      :summary="summary"
      @view="viewIssues"
    />
    <KnowledgeSourceToolbar
      v-model="search"
      :sort="sort"
      :total="total"
      :filter-open="isFilterOpen"
      @update:sort="changeSort"
      @toggle-filter="isFilterOpen = !isFilterOpen"
    />
    <nav
      v-if="isFilterOpen"
      class="filters"
      aria-label="快捷筛选"
    >
      <button
        v-for="item in [{ key: 'all', label: '全部' }, { key: 'local', label: '本地文件夹' }, { key: 'obsidian', label: 'Obsidian' }, { key: 'issues', label: '需要处理' }]"
        :key="item.key"
        type="button"
        :class="{ active: filter === item.key }"
        @click="changeFilter(item.key as typeof filter)"
      >
        {{ item.label }}
      </button>
    </nav>
    <p
      v-if="error || actionError"
      class="notice"
      role="alert"
    >
      {{ error ?? actionError }} <button
        type="button"
        @click="reload"
      >
        重试
      </button>
    </p>
    <div
      v-if="isLoading && !items.length"
      class="loading"
      role="status"
    >
      正在加载知识来源…
    </div>
    <div
      v-else-if="!items.length"
      class="empty"
    >
      <b>暂无匹配的知识来源</b><p>调整筛选条件，或添加一个资料来源开始使用。</p>
    </div>
    <div
      v-else
      class="rows"
    >
      <KnowledgeSourceRow
        v-for="source in items"
        :key="source.id"
        :source="source"
        :action-pending="pendingAction"
        @pin="togglePinned"
        @auto-sync="toggleAutoSync"
        @sync="sync"
        @view="viewSource"
        @menu="openDelete"
      />
    </div>
    <footer class="pagination">
      <span>共 {{ total }} 个来源</span><div>
        <button
          type="button"
          :disabled="page === 1"
          @click="changePage(page - 1)"
        >
          ‹
        </button><b>{{ page }}</b><button
          type="button"
          :disabled="page >= totalPages"
          @click="changePage(page + 1)"
        >
          ›
        </button>
      </div>
    </footer>
    <dialog :open="isAddOpen">
      <header>
        <h2>添加知识来源</h2><button
          type="button"
          aria-label="关闭添加知识来源"
          @click="isAddOpen = false"
        >
          ×
        </button>
      </header><KnowledgeSourceForm
        :disabled="pendingAction === 'create'"
        @submit="createSource"
      />
    </dialog>
    <ConfirmDialog
      :open="isDeleteOpen"
      :title="`移除 ${selectedSource?.name ?? '来源'}`"
      description="仅删除数据库记录，不会删除原始磁盘文件。此操作无法撤销。"
      confirm-label="移除来源"
      :pending="pendingAction === `remove-${selectedSource?.id}`"
      :error="actionError"
      @cancel="isDeleteOpen = false"
      @confirm="confirmDelete"
    />
  </section>
</template>
<style scoped>
.filters { display: flex; gap: 8px; margin: 8px 0 12px; }.filters button { min-height:32px; padding:0 12px; border:1px solid #e0e7f2; border-radius:7px; background:#fff; color:#23375f; font-size:12px; font-weight:700; }.filters .active { border-color:#dbe7ff; background:#edf3ff; color:#135dff; }.notice { padding:10px 14px; border-radius:8px; background:#fff5eb; color:#a64816; }.notice button { border:0; background:transparent; color:inherit; text-decoration:underline; }.loading, .empty { padding:42px; border:1px dashed #ced9ea; border-radius:12px; color:#5c6d8c; text-align:center; }.pagination { display:flex; align-items:center; justify-content:space-between; padding:10px 0; color:#52678e; font-size:12px; }.pagination div { display:flex; gap:7px; }.pagination button, .pagination b { display:grid; min-width:32px; min-height:32px; place-items:center; border:1px solid #e0e7f2; border-radius:7px; background:#fff; color:#1c5eff; }.pagination b { background:#195eff; color:#fff; } dialog { width:min(520px, calc(100% - 24px)); border:1px solid #dce5f2; border-radius:14px; padding:22px; } dialog header { display:flex; justify-content:space-between; } dialog header button { border:0; background:transparent; font-size:24px; }
</style>
