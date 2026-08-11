<script setup lang="ts">
import { shallowRef } from "vue";
import { useRoute } from "vue-router";

import { literatureSearchApi, type DuplicateGroup, type DuplicateResolutionAction, type ReadingOrder } from "../../api/literatureSearch";
import DuplicateReview from "../../components/DuplicateReview/DuplicateReview.vue";
import ReadingPlan from "../../components/ReadingPlan/ReadingPlan.vue";
import { useLiteratureResults } from "../../composables/useLiteratureResults";
import LiteratureFilters from "../../components/LiteratureFilters/LiteratureFilters.vue";
import PaperResults from "../../components/PaperResults/PaperResults.vue";

const props = withDefaults(defineProps<{ resultId?: number; taskId?: number; embedded?: boolean }>(), { embedded: false });
const route = useRoute();
const resultId = props.resultId ?? Number(route.params.id);
// 去重接口期望的是任务 id（task），而结果页 id 来自 latest_result_id（result）。
// History 跳转时带 ?task= 参数，优先用它调去重；缺失时退回 resultId（兼容直接访问）。
const routeTaskId = route.query.task !== undefined && !Array.isArray(route.query.task)
  ? Number(route.query.task)
  : resultId;
const taskId = props.taskId ?? routeTaskId;
const duplicateGroups = shallowRef<DuplicateGroup[]>([]);
const deduplicating = shallowRef(false);
const deduplicationError = shallowRef("");
const libraryStatus = shallowRef("");

// 推荐阅读顺序（R2-WP08）：算法顺序由服务端规则分类器生成；人工顺序保存后
// 重新生成仍优先人工顺序（不覆盖）。
const readingOrder = shallowRef<ReadingOrder | null>(null);
const readingLoading = shallowRef(false);
const readingSaving = shallowRef(false);
const readingError = shallowRef("");

async function generateReadingOrder(): Promise<void> {
  readingLoading.value = true;
  readingError.value = "";
  try {
    readingOrder.value = await literatureSearchApi.generateReadingOrder(resultId);
  } catch (error) {
    readingError.value = error instanceof Error ? error.message : "阅读顺序生成失败";
  } finally {
    readingLoading.value = false;
  }
}

async function saveReadingOrder(manualOrder: string[]): Promise<void> {
  readingSaving.value = true;
  readingError.value = "";
  try {
    readingOrder.value = await literatureSearchApi.saveReadingOrder(resultId, manualOrder);
  } catch (error) {
    readingError.value = error instanceof Error ? error.message : "人工顺序保存失败";
  } finally {
    readingSaving.value = false;
  }
}

async function runDeduplication(): Promise<void> {
  deduplicating.value = true;
  deduplicationError.value = "";
  try { duplicateGroups.value = (await literatureSearchApi.deduplicateTask(taskId)).items; }
  catch (error) { deduplicationError.value = error instanceof Error ? error.message : "去重请求失败"; }
  finally { deduplicating.value = false; }
}

async function resolveDuplicate(groupId: number, action: DuplicateResolutionAction): Promise<void> {
  deduplicating.value = true;
  deduplicationError.value = "";
  try {
    const group = await literatureSearchApi.resolveDuplicateGroup(groupId, { action });
    duplicateGroups.value = duplicateGroups.value.map((item) => item.id === group.id ? group : item);
  } catch (error) { deduplicationError.value = error instanceof Error ? error.message : "去重决策保存失败"; }
  finally { deduplicating.value = false; }
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
  updateState,
} = useLiteratureResults(resultId);
</script>

<template>
  <main class="results-view">
    <header v-if="!props.embedded" class="page-header">
      <p class="eyebrow">LITERATURE RESULTS · LIVE</p>
      <h1 class="page-title">检索结果 · 任务 #{{ resultId }}</h1>
      <p v-if="page" class="page-copy">检索式：{{ page.query }}。结果来自真实 PubMed 检索快照；本页只展示服务端已返回的数据。</p>
      <p v-else class="page-copy">正在按服务端返回的检索快照展示筛选、排序与分页。</p>
    </header>

    <section class="results-workspace" aria-label="检索结果工作区">
      <LiteratureFilters :filters="filters" :disabled="loading" @apply="applyFilters" />
      <p v-if="error" class="request-error workspace-error" role="alert">{{ error }}</p>
      <p v-if="deduplicationError" class="request-error workspace-error" role="alert">{{ deduplicationError }}</p>
      <p v-if="libraryStatus" class="library-status workspace-status">{{ libraryStatus }}</p>
      <PaperResults
      :items="page?.items ?? []"
      :result-id="resultId"
      :loading="loading"
      :updating="updating"
      :current-page="currentPage"
      :total-pages="totalPages"
      :filtered-total="filteredTotal"
      :has-previous="hasPrevious"
      :has-next="hasNext"
      @previous-page="previousPage"
      @next-page="nextPage"
      @go-to-page="goToPage"
      @toggle-saved="(pmid, saved) => updateState(pmid, { saved })"
      @toggle-read="(pmid, read) => updateState(pmid, { read_status: read ? 'read' : 'unread' })"
        @saved-to-library="(item) => libraryStatus = item.fulltext_status_reason"
      />
    </section>
    <details class="utility-disclosure">
      <summary>阅读顺序</summary>
      <ReadingPlan
      :order="readingOrder"
      :loading="readingLoading"
      :saving="readingSaving"
      :error="readingError"
      @generate="generateReadingOrder"
        @save="saveReadingOrder"
      />
    </details>
    <details class="utility-disclosure">
      <summary>去重</summary>
      <DuplicateReview :groups="duplicateGroups" :loading="deduplicating" @run="runDeduplication" @resolve="resolveDuplicate" />
    </details>
  </main>
</template>

<style scoped>
.results-view { max-width: 1440px; margin: auto; padding: 0; display: grid; gap: .8rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 800; letter-spacing: 0.12em; font-size: 0.72rem; }
.page-title { margin: 0.25rem 0; color: var(--text-primary); font-size: clamp(1.6rem, 3.5vw, 2.6rem); line-height: 1.15; }
.page-copy { max-width: 760px; margin: 0; color: var(--text-muted); line-height: 1.6; overflow-wrap: anywhere; }
.request-error { margin: 0; padding: 0.8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: 10px; }
.library-status { margin: 0; padding: .8rem; color: var(--color-success); background: var(--color-success-soft, #edf8f1); border-radius: 10px; }
.results-workspace { overflow: hidden; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%)); }
.results-workspace :deep(.results) { border: 0; border-radius: 0; box-shadow: none; }
.workspace-error, .workspace-status { margin: .65rem .9rem 0; }
.utility-disclosure { border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); padding: .65rem .8rem; }.utility-disclosure summary { color: var(--text-primary, #0f2a43); font-size: .84rem; font-weight: 600; cursor: pointer; }.utility-disclosure[open] summary { margin-bottom: .7rem; }
</style>
