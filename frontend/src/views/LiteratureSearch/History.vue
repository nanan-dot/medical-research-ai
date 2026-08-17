<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";

import { MAX_SEARCH_RESULTS, literatureSearchApi, type LiteratureSearchHistoryEntry } from "../../api/literatureSearch";
import HistoryPagination from "./HistoryPagination.vue";
import HistoryTableRow from "./HistoryTableRow.vue";

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });
const emit = defineEmits<{ rerunSucceeded: [selection: { resultId: number; taskId: number }] }>();
const pageSize = 10;
const tasks = shallowRef<LiteratureSearchHistoryEntry[]>([]);
const total = shallowRef(0);
const offset = shallowRef(0);
const isLoading = shallowRef(false);
const rerunningTaskId = shallowRef<number | null>(null);
const requestError = shallowRef("");
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const currentPage = computed(() => Math.floor(offset.value / pageSize) + 1);
const hasPreviousPage = computed(() => offset.value > 0);
const hasNextPage = computed(() => offset.value + pageSize < total.value);

async function loadTasks(): Promise<void> {
  isLoading.value = true; requestError.value = "";
  try { const page = await literatureSearchApi.listHistory(offset.value, pageSize); tasks.value = page.items; total.value = page.total; }
  catch (cause) { requestError.value = cause instanceof Error ? cause.message : "无法读取检索历史"; }
  finally { isLoading.value = false; }
}
async function handleRerun(task: LiteratureSearchHistoryEntry): Promise<void> {
  if (rerunningTaskId.value !== null) return;
  rerunningTaskId.value = task.id; requestError.value = "";
  try { const updated = await literatureSearchApi.rerunTask(task.id, MAX_SEARCH_RESULTS); await loadTasks(); emit("rerunSucceeded", { resultId: updated.new_result_id, taskId: updated.task.id }); }
  catch (cause) { requestError.value = cause instanceof Error ? cause.message : "重新检索失败"; }
  finally { rerunningTaskId.value = null; }
}
function previous(): void { if (hasPreviousPage.value) { offset.value -= pageSize; void loadTasks(); } }
function next(): void { if (hasNextPage.value) { offset.value += pageSize; void loadTasks(); } }
onMounted(() => { void loadTasks(); });
</script>

<template>
  <main class="history-page">
    <header v-if="!props.embedded" class="page-header"><h1 class="page-title">历史记录</h1><p class="page-copy">每条记录对应一个研究问题，展示该策略的最新检索状态与结果。</p></header>
    <div class="toolbar"><button class="refresh-button" type="button" :disabled="isLoading" @click="loadTasks">{{ isLoading ? "读取中…" : "刷新" }}</button><span class="total-note">共 {{ total }} 个研究记录 · 当前页 {{ tasks.length }} 条</span></div>
    <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p><p v-if="isLoading" class="state-text">正在读取检索历史…</p><p v-else-if="tasks.length === 0 && !requestError" class="empty-state">暂无保存的研究记录。</p>
    <section v-else class="history-table-wrap" aria-label="研究工作记录"><div class="history-columns" aria-hidden="true"><span>研究主题</span><span>最新结果</span><span>状态</span><span>最后运行</span><span>操作</span></div><ul class="history-list"><HistoryTableRow v-for="task in tasks" :key="task.id" :task="task" :is-rerunning="rerunningTaskId === task.id" @rerun="handleRerun" /></ul></section>
    <HistoryPagination v-if="total > pageSize" :current-page="currentPage" :total-pages="totalPages" :is-loading="isLoading" :has-previous-page="hasPreviousPage" :has-next-page="hasNextPage" @previous="previous" @next="next" />
  </main>
</template>

<style scoped>
.history-page { display:grid; gap:1rem; max-width:1440px; margin:0 auto; padding:1.4rem 1.5rem 2.6rem; }.page-header { display:grid; gap:.35rem; }.page-title { margin:0; color:var(--text-primary); font-size:clamp(2rem,4vw,3.2rem); line-height:1.1; }.page-copy,.total-note,.state-text { margin:0; color:var(--text-muted); }.toolbar { display:flex; align-items:center; gap:.8rem; }.refresh-button { padding:.55rem 1rem; border:1px solid var(--border-strong); border-radius:8px; background:var(--surface); color:var(--text-primary); font:inherit; font-weight:700; cursor:pointer; }.refresh-button:disabled { cursor:wait; opacity:.6; }.request-error { margin:0; padding:.8rem; border-radius:8px; background:var(--color-danger-soft); color:var(--color-danger); }.empty-state { margin:0; padding:2rem; border:1px dashed var(--border-strong); border-radius:var(--radius-md); color:var(--text-muted); text-align:center; }.history-table-wrap { overflow-x:auto; border:1px solid var(--border-subtle); border-radius:var(--radius-md); background:var(--surface); box-shadow:var(--shadow-card); }.history-columns { display:grid; grid-template-columns:minmax(16rem,1.8fr) minmax(9rem,.8fr) minmax(5rem,.55fr) minmax(10rem,.9fr) minmax(11rem,.9fr); gap:.75rem; min-width:780px; padding:.65rem 1rem; border-bottom:1px solid var(--border-subtle); background:var(--surface-muted); color:var(--text-muted); font-size:.74rem; font-weight:700; }.history-list { margin:0; padding:0; list-style:none; }@media (max-width:900px) { .history-page { padding:1.2rem; }.history-columns { display:none; }.history-table-wrap { overflow:visible; } }
</style>
