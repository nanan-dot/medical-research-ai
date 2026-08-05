<script setup lang="ts">
import { shallowRef } from "vue";
import { useRoute } from "vue-router";

import { literatureSearchApi, type DuplicateGroup, type DuplicateResolutionAction } from "../../api/literatureSearch";
import DuplicateReview from "../../components/DuplicateReview/DuplicateReview.vue";
import { useLiteratureResults } from "../../composables/useLiteratureResults";
import LiteratureFilters from "../../components/LiteratureFilters/LiteratureFilters.vue";
import PaperResults from "../../components/PaperResults/PaperResults.vue";

const route = useRoute();
const resultId = Number(route.params.id);
const duplicateGroups = shallowRef<DuplicateGroup[]>([]);
const deduplicating = shallowRef(false);
const deduplicationError = shallowRef("");

async function runDeduplication(): Promise<void> {
  deduplicating.value = true;
  deduplicationError.value = "";
  try { duplicateGroups.value = (await literatureSearchApi.deduplicateTask(resultId)).items; }
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
    <header class="page-header">
      <p class="eyebrow">LITERATURE RESULTS · LIVE</p>
      <h1 class="page-title">检索结果 · 任务 #{{ resultId }}</h1>
      <p v-if="page" class="page-copy">检索式：{{ page.query }}。结果来自真实 PubMed 检索快照；本页只展示服务端已返回的数据。</p>
      <p v-else class="page-copy">正在按服务端返回的检索快照展示筛选、排序与分页。</p>
    </header>

    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <p v-if="deduplicationError" class="request-error" role="alert">{{ deduplicationError }}</p>

    <LiteratureFilters :filters="filters" :disabled="loading" @apply="applyFilters" />
    <PaperResults
      :items="page?.items ?? []"
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
    />
    <DuplicateReview :groups="duplicateGroups" :loading="deduplicating" @run="runDeduplication" @resolve="resolveDuplicate" />
  </main>
</template>

<style scoped>
.results-view { max-width: 1100px; margin: auto; padding: 2rem 1.2rem 3rem; display: grid; gap: 1rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 800; letter-spacing: 0.12em; font-size: 0.72rem; }
.page-title { margin: 0.25rem 0; color: var(--text-primary); font-size: clamp(1.6rem, 3.5vw, 2.6rem); line-height: 1.15; }
.page-copy { max-width: 760px; margin: 0; color: var(--text-muted); line-height: 1.6; overflow-wrap: anywhere; }
.request-error { margin: 0; padding: 0.8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: 10px; }
</style>
