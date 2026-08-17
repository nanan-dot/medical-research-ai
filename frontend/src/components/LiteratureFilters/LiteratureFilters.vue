<script setup lang="ts">
import { computed, reactive, watch } from "vue";

import type { ResultFilterValues, SearchSort } from "../../api/literatureSearch";

const props = defineProps<{ filters: Readonly<ResultFilterValues>; disabled: boolean }>();
const emit = defineEmits<{ apply: [filters: ResultFilterValues] }>();

const draft = reactive<ResultFilterValues>({ ...props.filters });
const sorts: Array<{ value: SearchSort; label: string; explanation: string }> = [
  { value: "relevance", label: "相关性", explanation: "按 PubMed 本次返回顺序展示。" },
  { value: "newest", label: "最新", explanation: "按发表年份从新到旧，年份未知排后。" },
  { value: "classic", label: "经典代表性", explanation: "依据期刊、PubMed 核实状态与发表年份等可用信号，不代表临床证据更强。" },
  { value: "custom", label: "自定义", explanation: "优先使用已保存的人工顺序，未手动排序条目保留检索顺序。" },
];
const sortExplanation = computed(() => sorts.find((option) => option.value === draft.sort)?.explanation ?? "");

watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });

function apply(): void {
  emit("apply", { ...draft });
}

function reset(): void {
  emit("apply", { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: draft.sort });
}
</script>

<template>
  <form class="filters" @submit.prevent="apply">
    <div class="toolbar-row">
      <details class="filter-disclosure">
        <summary>筛选条件</summary>
        <div class="filter-grid">
          <label><span>年份</span><input v-model.number="draft.year" min="1900" max="2100" type="number" placeholder="全部" /></label>
          <label><span>期刊</span><input v-model="draft.journal" type="text" placeholder="如 Nature Medicine" /></label>
          <label><span>文献类型</span><input v-model="draft.publication_type" type="text" placeholder="如 Meta-Analysis" /></label>
          <label><span>作者</span><input v-model="draft.author" type="text" placeholder="如 Kim" /></label>
          <label><span>摘要</span><select v-model="draft.has_abstract"><option :value="null">全部</option><option :value="true">有摘要</option><option :value="false">无摘要</option></select></label>
          <label><span>保存</span><select v-model="draft.saved"><option :value="null">全部</option><option :value="true">已保存</option><option :value="false">未保存</option></select></label>
          <label><span>已读</span><select v-model="draft.read_status"><option value="">全部</option><option value="read">已读</option><option value="unread">未读</option></select></label>
          <label><span>标签</span><input v-model="draft.tags" type="text" /></label>
        </div>
        <div class="filter-actions"><button type="button" :disabled="props.disabled" @click="reset">清空</button><button type="submit" :disabled="props.disabled">应用筛选</button></div>
      </details>
      <label class="sort-control"><span>排序：</span><select v-model="draft.sort" :disabled="props.disabled" @change="apply"><option v-for="option in sorts" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
      <details class="sort-help">
        <summary>排序依据</summary>
        <p>{{ sortExplanation }}</p>
      </details>
    </div>
  </form>
</template>

<style scoped>
.filters { display: grid; }
.toolbar-row { display: flex; align-items: center; gap: .55rem; flex-wrap: wrap; padding: .62rem .95rem; border-bottom: 1px solid var(--border-subtle); }
.filter-disclosure, .sort-help { position: relative; }
.filter-disclosure summary, .sort-control, .sort-help summary { box-sizing: border-box; display: inline-flex; align-items: center; min-height: 2rem; padding: .32rem .6rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--text-primary); font-size: .8rem; cursor: pointer; }
.filter-disclosure[open] { flex-basis: 100%; }
.filter-disclosure[open] summary { width: max-content; }
.sort-help { color: var(--text-muted); font-size: .78rem; }
.sort-help summary { border-color: transparent; padding: .32rem .2rem; color: var(--text-muted); text-decoration: underline; text-underline-offset: .16rem; }
.sort-help p { position: absolute; z-index: 1; width: min(22rem, calc(100vw - 2rem)); margin: .35rem 0 0; padding: .55rem .65rem; border: 1px solid var(--border-subtle); border-radius: 6px; background: var(--surface); color: var(--text-secondary); line-height: 1.5; box-shadow: var(--shadow-card); }
.filter-disclosure summary:focus-visible, .sort-help summary:focus-visible, .sort-control select:focus-visible, .filter-actions button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.filter-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .55rem; margin-top: .65rem; }
.filter-grid label { display: grid; gap: .25rem; color: var(--text-muted); font-size: .74rem; }
.filter-grid input, .filter-grid select, .sort-control select { box-sizing: border-box; min-width: 0; min-height: 2rem; border: 1px solid var(--border-strong); border-radius: 5px; background: var(--surface); color: var(--text-primary); font: inherit; }
.sort-control { padding: 0 .25rem 0 .55rem; cursor: default; }
.sort-control select { border: 0; padding: .2rem; }
.filter-actions { display: flex; justify-content: flex-end; gap: .45rem; margin-top: .6rem; }
.filter-actions button { min-height: 2rem; padding: .3rem .62rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--text-primary); font: inherit; font-size: .8rem; cursor: pointer; }
.filter-actions button[type="submit"] { border-color: var(--color-primary); background: var(--color-primary); color: var(--text-on-primary); }
@media (max-width: 900px) { .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .filter-grid { grid-template-columns: 1fr; }.sort-help { flex-basis: 100%; } }
@media (prefers-reduced-motion: no-preference) { .sort-help p { transition: opacity 150ms ease; } }
</style>
