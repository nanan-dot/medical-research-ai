<script setup lang="ts">
import { reactive, watch } from "vue";
import type { ResultFilterValues, SearchSort } from "../../api/literatureSearch";
const props = defineProps<{ filters: Readonly<ResultFilterValues>; disabled: boolean }>();
const emit = defineEmits<{ apply: [filters: ResultFilterValues] }>();
const draft = reactive<ResultFilterValues>({ ...props.filters });
const sorts: Array<{ value: SearchSort; label: string }> = [{ value: "relevance", label: "相关性" }, { value: "newest", label: "最新" }, { value: "classic", label: "经典代表性" }, { value: "custom", label: "自定义" }];
watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });
function apply(): void { emit("apply", { ...draft }); }
function reset(): void { emit("apply", { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: draft.sort }); }
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
    </div>
  </form>
</template>

<style scoped>
.filters { display: grid; }.toolbar-row { display: flex; gap: .55rem; align-items: center; flex-wrap: wrap; padding: .62rem .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); }
.filter-disclosure { position: relative; }.filter-disclosure summary, .sort-control { min-height: 2rem; box-sizing: border-box; display: inline-flex; align-items: center; padding: .32rem .6rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font-size: .8rem; cursor: pointer; }.filter-disclosure[open] { flex-basis: 100%; }.filter-disclosure[open] summary { width: max-content; }
.filter-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .55rem; margin-top: .65rem; }.filter-grid label { display: grid; gap: .25rem; color: var(--text-muted, #64748b); font-size: .74rem; }.filter-grid input, .filter-grid select, .sort-control select { min-width: 0; min-height: 2rem; box-sizing: border-box; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 5px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; }.sort-control { padding: 0 .25rem 0 .55rem; cursor: default; }.sort-control select { border: 0; padding: .2rem; }.filter-actions { display: flex; justify-content: flex-end; gap: .45rem; margin-top: .6rem; }.filter-actions button { min-height: 2rem; padding: .3rem .62rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; font-size: .8rem; cursor: pointer; }.filter-actions button[type="submit"] { border-color: var(--color-primary, #2563eb); background: var(--color-primary, #2563eb); color: #fff; }
@media (max-width: 900px) { .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } } @media (max-width: 560px) { .filter-grid { grid-template-columns: 1fr; } }
</style>
