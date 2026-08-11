<script setup lang="ts">
import { computed } from "vue";

import type { LiteratureSearchTask, SearchResultChange, SearchTaskStatus } from "../../api/literatureSearch";

const props = defineProps<{
  task: LiteratureSearchTask;
  isRerunning: boolean;
}>();
const emit = defineEmits<{ rerun: [task: LiteratureSearchTask] }>();

const statusLabels: Record<SearchTaskStatus, string> = {
  pending: "待执行",
  running: "执行中",
  succeeded: "已完成",
  failed: "失败",
};

const latestChange = computed<SearchResultChange | null>(() => props.task.versions.at(-1)?.change ?? null);
const versionChangeLabel = computed(() => {
  if (!latestChange.value) return null;
  const { count_delta: countDelta } = latestChange.value;
  return `${countDelta >= 0 ? "+" : "-"}${Math.abs(countDelta)} 条`;
});
const versionChangeClass = computed(() => latestChange.value?.count_delta === undefined ? "" : latestChange.value.count_delta >= 0 ? "increased" : "decreased");
const displaySearchDate = computed(() => formatDate(props.task.searched_at));
const canViewResults = computed(() => props.task.latest_result_id !== null);
const isRerunDisabled = computed(() => props.isRerunning || props.task.status === "running");

function formatDate(value: string | null): string {
  if (!value) return "未检索";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未检索" : date.toLocaleString("zh-CN", { hour12: false });
}

function handleRerun(): void {
  emit("rerun", props.task);
}
</script>

<template>
  <li class="history-item">
    <div class="item-grid">
      <h2 class="item-title">{{ props.task.original_query }}</h2>
      <p class="search-string" :title="props.task.search_string">{{ props.task.search_string }}</p>
      <div class="version-cell">
        <span>v{{ props.task.versions.length }}</span>
        <span v-if="versionChangeLabel" class="version-change" :class="versionChangeClass">{{ versionChangeLabel }}</span>
      </div>
      <span class="result-count">{{ props.task.result_count }}</span>
      <span class="status-badge" :class="`status-${props.task.status}`">{{ statusLabels[props.task.status] }}</span>
      <time class="run-date">{{ displaySearchDate }}</time>
      <div class="row-actions">
        <RouterLink v-if="canViewResults" class="view-results" :to="`/literature-search/results/${props.task.latest_result_id}?task=${props.task.id}`">查看结果</RouterLink>
        <button class="rerun" type="button" :disabled="isRerunDisabled" @click="handleRerun">{{ props.isRerunning ? "重跑中…" : "重跑" }}</button>
      </div>
    </div>

    <p v-if="props.task.error_message" class="task-error" role="alert">失败原因：{{ props.task.error_message }}</p>
    <details v-if="latestChange" class="change-summary" :class="versionChangeClass">
      <summary>版本变化：命中数 {{ latestChange.previous_count }} → {{ latestChange.current_count }}，新增 {{ latestChange.added_count }} 条，减少 {{ latestChange.removed_count }} 条</summary>
      <div v-if="latestChange.added_pmids.length || latestChange.removed_pmids.length" class="pmid-list">
        <p v-if="latestChange.added_pmids.length">新增 PMID：{{ latestChange.added_pmids.join(", ") }}</p>
        <p v-if="latestChange.removed_pmids.length">减少 PMID：{{ latestChange.removed_pmids.join(", ") }}</p>
      </div>
    </details>
  </li>
</template>

<style scoped>
.history-item { display: grid; gap: .7rem; padding: .85rem 1rem; border-bottom: 1px solid var(--border-subtle); }
.history-item:last-child { border-bottom: 0; }
.item-grid { display: grid; grid-template-columns: 1.5fr 1.8fr .8fr .6fr .7fr 1.1fr 1.25fr; gap: .75rem; align-items: center; min-width: 980px; }
.item-title { min-width: 0; margin: 0; color: var(--text-primary); font-size: .92rem; overflow-wrap: anywhere; }
.search-string { min-width: 0; margin: 0; overflow: hidden; color: var(--text-muted); font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: .72rem; text-overflow: ellipsis; white-space: nowrap; }
.version-cell { display: grid; gap: .15rem; color: var(--text-secondary); font-size: .8rem; }
.version-change { font-size: .72rem; font-weight: 700; }.version-change.increased { color: var(--color-success); }.version-change.decreased { color: var(--color-warning); }
.result-count, .run-date { color: var(--text-secondary); font-size: .8rem; }
.status-badge { display: inline-block; width: fit-content; padding: .25rem .6rem; border-radius: 999px; background: var(--surface-muted); font-size: .75rem; font-weight: 800; white-space: nowrap; }
.status-succeeded { background: var(--color-success-soft); color: var(--color-success); }.status-failed { background: var(--color-danger-soft); color: var(--color-danger); }.status-running, .status-pending { background: var(--color-primary-soft); color: var(--color-primary); }
.row-actions { display: flex; flex-wrap: wrap; gap: .45rem; }.rerun, .view-results { padding: .4rem .65rem; border-radius: 6px; font: inherit; font-weight: 750; text-decoration: none; white-space: nowrap; }.rerun { border: 0; background: var(--color-primary); color: #fff; cursor: pointer; }.rerun:disabled { cursor: not-allowed; opacity: .6; }.view-results { border: 1px solid var(--color-primary); color: var(--color-primary); }.view-results:hover { background: var(--color-primary-soft); }
.task-error { margin: 0; color: var(--color-danger); font-size: .84rem; }.change-summary { padding: .7rem .8rem; border-radius: 8px; background: var(--color-primary-soft); color: var(--color-primary); font-size: .82rem; }.change-summary.decreased { background: var(--color-warning-soft); color: var(--color-warning); }.change-summary summary { cursor: pointer; }.pmid-list { margin-top: .5rem; color: var(--text-muted); overflow-wrap: anywhere; }.pmid-list p { margin: .25rem 0 0; }
@media (max-width: 900px) { .item-grid { grid-template-columns: 1fr 1fr; min-width: 0; }.item-title, .search-string, .row-actions { grid-column: 1 / -1; }.search-string { white-space: normal; }.version-cell { grid-column: 1; }.result-count { grid-column: 2; } }
</style>
