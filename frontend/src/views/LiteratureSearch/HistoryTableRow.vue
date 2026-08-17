<script setup lang="ts">
import { computed } from "vue";

import type { LiteratureSearchHistoryEntry, SearchTaskStatus } from "../../api/literatureSearch";
import { formatSearchChangeNotice } from "./searchChangeNotice";

const props = defineProps<{ task: LiteratureSearchHistoryEntry; isRerunning: boolean }>();
const emit = defineEmits<{ rerun: [task: LiteratureSearchHistoryEntry] }>();

const statusLabels: Record<SearchTaskStatus, string> = {
  pending: "待执行", running: "执行中", succeeded: "已完成", failed: "失败",
};
const changeNotice = computed(() => formatSearchChangeNotice(props.task.latest_change));
const canViewResults = computed(() => props.task.latest_result_id !== null);
const isRerunDisabled = computed(() => props.isRerunning || props.task.status === "running");
const displaySearchDate = computed(() => {
  if (!props.task.searched_at) return "未检索";
  const date = new Date(props.task.searched_at);
  return Number.isNaN(date.getTime()) ? "未检索" : date.toLocaleString("zh-CN", { hour12: false });
});
</script>

<template>
  <li class="history-item">
    <div class="item-grid">
      <h2 class="item-title">{{ props.task.original_query }}</h2>
      <span class="result-count">最新结果 {{ props.task.result_count }} 篇</span>
      <span class="status-badge" :class="`status-${props.task.status}`">{{ statusLabels[props.task.status] }}</span>
      <time class="run-date">{{ displaySearchDate }}</time>
      <div class="row-actions">
        <RouterLink v-if="canViewResults" class="view-results" :to="`/literature-search/results/${props.task.latest_result_id}?task=${props.task.id}&from=history`">查看结果</RouterLink>
        <button class="rerun" type="button" :disabled="isRerunDisabled" @click="emit('rerun', props.task)">{{ props.isRerunning ? "重新检索中…" : "重新检索" }}</button>
      </div>
    </div>
    <p v-if="props.task.status === 'failed' && props.task.error_message" class="task-error" role="alert">失败原因：{{ props.task.error_message }}</p>
    <p v-if="changeNotice" class="change-notice" role="status">{{ changeNotice }}</p>
  </li>
</template>

<style scoped>
.history-item { display: grid; gap: .55rem; padding: .85rem 1rem; border-bottom: 1px solid var(--border-subtle); }
.history-item:last-child { border-bottom: 0; }
.item-grid { display: grid; grid-template-columns: minmax(16rem, 1.8fr) minmax(9rem, .8fr) minmax(5rem, .55fr) minmax(10rem, .9fr) minmax(11rem, .9fr); gap: .75rem; align-items: center; min-width: 780px; }
.item-title { min-width: 0; margin: 0; color: var(--text-primary); font-size: .92rem; overflow-wrap: anywhere; }.result-count,.run-date { color: var(--text-secondary); font-size: .82rem; }.status-badge { width: fit-content; padding: .25rem .6rem; border-radius: 999px; background: var(--surface-muted); font-size: .75rem; font-weight: 800; white-space: nowrap; }.status-succeeded { background: var(--color-success-soft); color: var(--color-success); }.status-failed { background: var(--color-danger-soft); color: var(--color-danger); }.status-running,.status-pending { background: var(--color-primary-soft); color: var(--color-primary); }.row-actions { display: flex; flex-wrap: wrap; gap: .45rem; }.rerun,.view-results { padding: .4rem .65rem; border-radius: 6px; font: inherit; font-weight: 750; text-decoration: none; white-space: nowrap; }.rerun { border: 0; background: var(--color-primary); color: var(--surface); cursor: pointer; }.rerun:disabled { cursor: not-allowed; opacity: .6; }.view-results { border: 1px solid var(--color-primary); color: var(--color-primary); }.task-error { margin: 0; color: var(--color-danger); font-size: .84rem; }.change-notice { margin: 0; padding: .55rem .7rem; border-radius: 6px; background: var(--color-primary-soft); color: var(--color-primary); font-size: .82rem; }
@media (max-width: 900px) { .item-grid { grid-template-columns: 1fr 1fr; min-width: 0; }.item-title,.row-actions { grid-column: 1 / -1; } }
</style>
