<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { literatureSearchApi, type ReadingOrder } from "../../api/literatureSearch";
import DuplicateReviewDrawer from "../../components/literature/DuplicateReviewDrawer.vue";
import ReadingPlan from "../../components/ReadingPlan/ReadingPlan.vue";
import { DEFAULT_PAGE_SIZE, useLiteratureResults } from "../../composables/useLiteratureResults";
import { useResultDeduplication } from "../../composables/useResultDeduplication";
import LiteratureFilters from "../../components/LiteratureFilters/LiteratureFilters.vue";
import PaperResults from "../../components/PaperResults/PaperResults.vue";
import { libraryStatusMessage } from "../../utils/libraryStatusMessage";

const props = withDefaults(defineProps<{ resultId?: number; taskId?: number; embedded?: boolean }>(), { embedded: false });
const route = useRoute();
const router = useRouter();
const resultId = props.resultId ?? Number(route.params.id);
// 研究主题仍来自任务；结果级去重和阅读计划始终使用不可变结果快照 id。
const routeTaskId = route.query.task !== undefined && !Array.isArray(route.query.task)
  ? Number(route.query.task)
  : resultId;
const taskId = props.taskId ?? routeTaskId;
const isDuplicateReviewOpen = shallowRef(false);
const libraryStatus = shallowRef("");
const researchTopic = shallowRef("");

const readingOrder = shallowRef<ReadingOrder | null>(null);
const readingOrdersByMode = shallowRef<Partial<Record<"all" | "consolidated", ReadingOrder>>>({});
const readingLoading = shallowRef(false);
const readingSaving = shallowRef(false);
const readingError = shallowRef("");
const readingRestoreNotice = shallowRef("");
const activeView = computed(() => route.query.view === "reading-plan" ? "reading-plan" : "results");


async function loadReadingOrder(force = false): Promise<void> {
  const duplicateMode = filters.value.duplicate_mode;
  if (!force && readingOrdersByMode.value[duplicateMode]) {
    readingOrder.value = readingOrdersByMode.value[duplicateMode] ?? null;
    return;
  }
  readingLoading.value = true;
  readingError.value = "";
  try {
    const order = await literatureSearchApi.generateReadingOrder(resultId, { manual_order: [], duplicate_mode: duplicateMode });
    readingOrdersByMode.value = { ...readingOrdersByMode.value, [duplicateMode]: order };
    readingOrder.value = order;
    readingRestoreNotice.value = readingOrder.value.order_source === "manual"
      ? "已恢复您保存的人工阅读顺序"
      : "";
  } catch (error) {
    readingError.value = error instanceof Error ? error.message : "阅读顺序生成失败";
  } finally {
    readingLoading.value = false;
  }
}

async function loadResearchTopic(): Promise<void> {
  try {
    researchTopic.value = (await literatureSearchApi.getTask(taskId)).original_query;
  } catch {
    researchTopic.value = "";
  }
}

async function saveReadingOrder(manualOrder: string[]): Promise<void> {
  readingSaving.value = true;
  readingError.value = "";
  try {
    const order = await literatureSearchApi.saveReadingOrder(resultId, manualOrder, filters.value.duplicate_mode);
    readingOrdersByMode.value = { ...readingOrdersByMode.value, [filters.value.duplicate_mode]: order };
    readingOrder.value = order;
  } catch (error) {
    readingError.value = error instanceof Error ? error.message : "人工顺序保存失败";
  } finally {
    readingSaving.value = false;
  }
}

const {
  page,
  filters,
  loading,
  error,
  updating,
  filteredTotal,
  totalPages,
  currentPage,
  hasPrevious,
  hasNext,
  applyFilters,
  goToPage,
  previousPage,
  nextPage,
  setDuplicateMode,
  updateState,
  reload,
} = useLiteratureResults(resultId);
const deduplication = useResultDeduplication(resultId, () => { void reload(); });
// 扫描后（has_scan=true）才开放 consolidated 视图切换；未扫描时控件置灰并提示。
const hasScannedDuplicates = computed(() => deduplication.summary.value?.has_scan ?? false);
async function openDuplicateReview(): Promise<void> {
  isDuplicateReviewOpen.value = true;
  await deduplication.loadSummary();
  if (deduplication.summary.value?.has_scan) await deduplication.loadGroups("pending_resolution", 0);
}

function loadDuplicateGroups(status: "pending_resolution" | "all", pageNumber: number): void {
  void deduplication.loadGroups(status, (pageNumber - 1) * 10);
}

function setView(view: "results" | "reading-plan"): void {
  void router.replace({ query: { ...route.query, view: view === "results" ? undefined : view } });
}

onMounted(() => {
  // 初次进入读取一次；主视图切换使用 v-show 保留组件和该结果，绝不重复请求。
  void loadReadingOrder();
  void loadResearchTopic();
  // 页面加载即读去重摘要（GET 只读），让「显示」控件从一开始反映真实扫描状态。
  void deduplication.loadSummary().catch(() => undefined);
});

watch(
  () => filters.value.duplicate_mode,
  () => { void loadReadingOrder(); },
);
</script>

<template>
  <main
    class="results-view"
    :class="{ embedded: props.embedded }"
  >
    <header
      v-if="!props.embedded"
      class="page-header"
    >
      <p class="eyebrow">LITERATURE RESULTS · LIVE</p>
      <h1 class="page-title">检索结果</h1>
      <p class="task-reference">任务 #{{ resultId }}</p>
      <p
        v-if="page"
        class="page-copy"
      >
        检索式：{{ page.query }}。结果来自真实 PubMed 检索快照；本页只展示服务端已返回的数据。
      </p>
      <p
        v-else
        class="page-copy"
      >
        正在按服务端返回的检索快照展示筛选、排序与分页。
      </p>
    </header>

    <section
      class="results-workspace"
      aria-label="检索结果工作区"
    >
      <section
        class="research-brief"
        aria-labelledby="research-brief-title"
      >
        <div>
          <p class="brief-kicker">CURRENT RESEARCH</p>
          <h2 id="research-brief-title">{{ researchTopic || "本次检索结果" }}</h2>
        </div>
        <div
          class="brief-facts"
          role="status"
          aria-live="polite"
        >
          <span>PubMed</span>
          <span v-if="filteredTotal">{{ filteredTotal }} 篇结果</span>
        </div>
      </section>
      <LiteratureFilters
        v-show="activeView === 'results'"
        :filters="filters"
        :disabled="loading"
        @apply="applyFilters"
      />
      <nav
        class="result-view-tabs"
        aria-label="结果主视图"
      >
        <button
          type="button"
          :class="{ active: activeView === 'results' }"
          @click="setView('results')"
        >
          全部文献
        </button>
        <button
          type="button"
          :class="{ active: activeView === 'reading-plan' }"
          @click="setView('reading-plan')"
        >
          阅读计划
        </button>
        <label class="duplicate-mode">显示：<select
          :value="filters.duplicate_mode"
          :disabled="!hasScannedDuplicates"
          @change="setDuplicateMode(($event.target as HTMLSelectElement).value as 'all' | 'consolidated')"
        ><option value="all">全部记录</option><option value="consolidated">合并去重</option></select><small v-if="!hasScannedDuplicates">尚未检查重复论文</small></label>
      </nav>
      <details
        v-show="activeView === 'results'"
        class="more-actions"
      >
        <summary>更多操作</summary>
        <button
          type="button"
          @click="openDuplicateReview"
        >
          检查重复论文
        </button>
      </details>
      <DuplicateReviewDrawer
        :open="isDuplicateReviewOpen"
        :summary="deduplication.summary.value"
        :groups="deduplication.groups.value"
        :status="deduplication.status.value"
        :page="deduplication.page.value"
        :total-pages="deduplication.totalPages.value"
        :loading="deduplication.loading.value"
        :error="deduplication.error.value"
        @close="isDuplicateReviewOpen = false"
        @scan="deduplication.scan"
        @load-groups="loadDuplicateGroups"
        @resolve="(id, action, recordKey) => deduplication.resolve(id, { action, canonical_record_key: recordKey })"
      />
      <ReadingPlan
        v-show="activeView === 'reading-plan'"
        :order="readingOrder"
        :loading="readingLoading"
        :saving="readingSaving"
        :error="readingError"
        :restore-notice="readingRestoreNotice"
        @generate="loadReadingOrder(true)"
        @save="saveReadingOrder"
      />
      <p
        v-if="error"
        class="request-error workspace-error"
        role="alert"
      >
        {{ error }}
      </p>
      <p
        v-if="libraryStatus"
        class="library-status workspace-status"
      >
        {{ libraryStatus }}
      </p>
      <PaperResults
        v-show="activeView === 'results'"
        :items="page?.items ?? []"
        :result-id="resultId"
        :loading="loading"
        :updating="updating"
        :current-page="currentPage"
        :page-size="DEFAULT_PAGE_SIZE"
        :total-pages="totalPages"
        :filtered-total="filteredTotal"
        :has-previous="hasPrevious"
        :has-next="hasNext"
        @previous-page="previousPage"
        @next-page="nextPage"
        @go-to-page="goToPage"
        @toggle-saved="(pmid, saved) => updateState(pmid, { saved })"
        @toggle-read="(pmid, read) => updateState(pmid, { read_status: read ? 'read' : 'unread' })"
        @saved-to-library="(item) => libraryStatus = libraryStatusMessage(item.fulltext_status)"
      />
    </section>
  </main>
</template>

<style scoped>
.results-view { max-width: 1440px; margin: auto; padding: 0; display: grid; gap: .8rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 800; letter-spacing: 0.12em; font-size: 0.72rem; }
.page-title { margin: 0.25rem 0; color: var(--text-primary); font-size: clamp(1.6rem, 3.5vw, 2.6rem); line-height: 1.15; }
.task-reference { margin: 0; color: var(--text-muted); font-size: .82rem; }
.page-copy { max-width: 760px; margin: 0; color: var(--text-muted); line-height: 1.6; overflow-wrap: anywhere; }
.request-error { margin: 0; padding: 0.8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: 10px; }
.library-status { margin: 0; padding: .8rem; color: var(--color-success); background: var(--color-success-soft, #edf8f1); border-radius: 10px; }
.results-workspace { overflow: hidden; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%)); }
.result-view-tabs { display:flex; align-items:center; gap:1.6rem; padding:.25rem .95rem 0; border-bottom:1px solid var(--border-subtle, #dbe4f0); }.result-view-tabs button { padding:.55rem 0; border:0; border-bottom:3px solid transparent; background:transparent; color:var(--text-muted); font:inherit; font-weight:700; cursor:pointer; }.result-view-tabs button.active { color:var(--text-primary); border-color:var(--color-primary); }.duplicate-mode { margin-left:auto; display:flex; align-items:center; gap:.3rem; color:var(--text-muted); font-size:.78rem; }.duplicate-mode select { border:1px solid var(--border-strong); background:var(--surface); padding:.28rem; color:var(--text-primary); font:inherit; }.duplicate-mode small { margin-left:.2rem; color:var(--text-faint); }.more-actions { position: relative; display: flex; justify-content: flex-end; padding: .35rem .95rem 0; }.more-actions summary { color: var(--text-muted); font-size: .78rem; cursor: pointer; }.more-actions button { position: absolute; z-index: 2; top: 2rem; right: .95rem; border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-primary); padding: .45rem .6rem; font: inherit; font-size: .78rem; box-shadow: var(--shadow-card); cursor: pointer; }
.research-brief { display: flex; align-items: center; justify-content: space-between; gap: .8rem; padding: .55rem .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); background: var(--surface-muted, #f5f8fc); }.brief-kicker { display: inline; margin: 0 .45rem 0 0; color: var(--color-primary); font-size: .64rem; font-weight: 800; letter-spacing: .1em; }.research-brief h2 { display: inline; max-width: 60rem; margin: 0; color: var(--text-primary); font-size: .98rem; line-height: 1.35; overflow-wrap: anywhere; }.brief-facts { display: flex; flex-wrap: wrap; justify-content: end; gap: .3rem; flex: 0 0 auto; }.brief-facts span { border-radius: 999px; padding: .2rem .45rem; background: var(--surface, #fff); border: 1px solid var(--border-subtle, #dbe4f0); color: var(--text-muted); font-size: .7rem; white-space: nowrap; }
.results-workspace :deep(.results) { border: 0; border-radius: 0; box-shadow: none; }
.workspace-error, .workspace-status { margin: .65rem .9rem 0; }
@media (max-width: 640px) { .research-brief { align-items: start; flex-direction: column; }.brief-facts { justify-content: start; } }
</style>
