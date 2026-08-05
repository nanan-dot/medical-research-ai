<script setup lang="ts">
import type { DuplicateGroup, DuplicateResolutionAction } from "../../api/literatureSearch";

interface Props { groups: DuplicateGroup[]; loading: boolean; }
interface Emits { run: []; resolve: [groupId: number, action: DuplicateResolutionAction]; }
const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const methodLabels: Record<string, string> = {
  pmid: "PMID 精确匹配", doi: "DOI 标准化匹配", title_normalized: "标题标准化候选", author_year: "首位作者与年份候选", manual: "人工确认",
};
</script>

<template>
  <section class="duplicate-review" aria-label="文献去重复核">
    <header class="review-header">
      <div><p class="review-kicker">REFERENCE DEDUPLICATION</p><h2 class="review-title">去重复核</h2></div>
      <button class="action-button" :disabled="props.loading" @click="emit('run')">运行去重</button>
    </header>
    <p class="review-copy">仅保存合并决策；原始检索快照和来源任务始终保留。</p>
    <p v-if="!props.groups.length" class="review-empty">尚无去重组。运行去重后在此显示真实匹配依据。</p>
    <article v-for="group in props.groups" :key="group.id" class="group-card">
      <p class="group-meta">{{ methodLabels[group.match_method] }} · {{ group.confidence === 'clear' ? '明确匹配' : '需人工确认' }}</p>
      <ul class="member-list"><li v-for="member in group.members" :key="`${member.result_id}:${member.record_pmid}`">PMID {{ member.record_pmid }} · 来源任务 {{ member.source_search_ids.join('、') }}</li></ul>
      <div v-if="group.confidence === 'fuzzy' && group.status === 'pending_resolution'" class="group-actions">
        <button :disabled="props.loading" @click="emit('resolve', group.id, 'merge_all')">全部合并</button>
        <button :disabled="props.loading" @click="emit('resolve', group.id, 'keep_all')">全部保留</button>
      </div>
      <button v-else-if="group.resolution" class="undo-button" :disabled="props.loading" @click="emit('resolve', group.id, 'undo')">撤销决策</button>
    </article>
  </section>
</template>

<style scoped>
.duplicate-review { display: grid; gap: .75rem; padding: 1rem; border: 1px solid var(--border-color, #d9e1ed); border-radius: 12px; }
.review-header { display: flex; justify-content: space-between; gap: 1rem; align-items: center; }.review-kicker,.group-meta { margin: 0; color: var(--text-muted); font-size: .78rem; }.review-title { margin: .2rem 0 0; }.review-copy,.review-empty { margin: 0; color: var(--text-muted); }.action-button,.group-actions button,.undo-button { padding: .45rem .75rem; border: 0; border-radius: 7px; cursor: pointer; }.action-button { color: #fff; background: var(--color-primary); }.group-card { padding: .8rem; background: var(--surface-muted, #f5f8fc); border-radius: 8px; }.member-list { margin: .55rem 0; padding-left: 1.2rem; }.group-actions { display: flex; gap: .5rem; }.undo-button { background: transparent; border: 1px solid var(--border-color, #d9e1ed); }
</style>
