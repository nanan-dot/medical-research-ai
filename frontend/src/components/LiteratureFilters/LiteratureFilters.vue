<script setup lang="ts">
import { computed, reactive, watch } from "vue";

import type { ResultFilterValues, SearchSort } from "../../api/literatureSearch";

const props = withDefaults(defineProps<{
  filters: Readonly<ResultFilterValues>;
  disabled: boolean;
  /** 服务端在同一结果快照上计算的可用筛选值，绝不由前端臆造。 */
  facets?: Record<string, Record<string, number>>;
  sortCapabilities?: Record<string, { available: boolean; reason: string | null }>;
}>(), { facets: () => ({}), sortCapabilities: () => ({}) });
const emit = defineEmits<{ apply: [filters: ResultFilterValues] }>();

const draft = reactive<ResultFilterValues>({ ...props.filters });
const sorts: Array<{ value: SearchSort; label: string; explanation: string }> = [
  { value: "recommended", label: "综合推荐", explanation: "使用已激活评分的阅读优先级；尚未生成评分时保持 PubMed 检索顺序。" },
  { value: "relevance", label: "相关性", explanation: "按 PubMed 本次返回顺序展示。" },
  { value: "popular", label: "近期热度", explanation: "按 OpenAlex 开放年度被引记录排序；缺少该开放数据时不可用。" },
  { value: "newest", label: "最新", explanation: "按发表年份从新到旧，年份未知排后。" },
  { value: "article_impact", label: "文章影响力", explanation: "按 OpenAlex 开放文章级被引计数排序；缺少该开放数据时不可用。" },
  { value: "classic", label: "经典度", explanation: "按文章级开放被引与发表年限计算，不能代表期刊指标。" },
  { value: "custom", label: "自定义", explanation: "优先使用已保存的人工顺序，未手动排序条目保留检索顺序。" },
];
const sortExplanation = computed(() => sorts.find((option) => option.value === draft.sort)?.explanation ?? "");
function sortIsAvailable(sort: SearchSort): boolean {
  return props.sortCapabilities[sort]?.available ?? true;
}

function sortUnavailableReason(sort: SearchSort): string | null {
  return props.sortCapabilities[sort]?.reason ?? null;
}
const yearFacets = computed(() => Object.entries(props.facets.year ?? {}).sort(([left], [right]) => Number(right) - Number(left)));
const journalFacets = computed(() => Object.entries(props.facets.journal ?? {}).sort(([left], [right]) => left.localeCompare(right)));
const publicationTypeFacets = computed(() => Object.entries(props.facets.publication_type ?? {}).sort(([left], [right]) => left.localeCompare(right)));
const appliedFilters = computed(() => {
  const values: Array<{ key: string; label: string }> = [];
  if (draft.year !== null) values.push({ key: "year", label: `年份：${draft.year}` });
  if (draft.journal) values.push({ key: "journal", label: `期刊：${draft.journal}` });
  if (draft.publication_type) values.push({ key: "publication_type", label: `类型：${draft.publication_type}` });
  if (draft.author) values.push({ key: "author", label: `作者：${draft.author}` });
  if (draft.has_abstract !== null) values.push({ key: "has_abstract", label: draft.has_abstract ? "有摘要" : "无摘要" });
  if (draft.saved !== null) values.push({ key: "saved", label: draft.saved ? "已保存" : "未保存" });
  if (draft.read_status) values.push({ key: "read_status", label: `阅读：${draft.read_status}` });
  if (draft.tags) values.push({ key: "tags", label: `标签：${draft.tags}` });
  return values;
});

watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });

function apply(): void {
  emit("apply", { ...draft });
}

function reset(): void {
  emit("apply", { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: draft.sort });
}

function removeFilter(key: string): void {
  const next = { ...draft };
  if (key === "year") next.year = null;
  if (key === "journal") next.journal = "";
  if (key === "publication_type") next.publication_type = "";
  if (key === "author") next.author = "";
  if (key === "has_abstract") next.has_abstract = null;
  if (key === "saved") next.saved = null;
  if (key === "read_status") next.read_status = "";
  if (key === "tags") next.tags = "";
  emit("apply", next);
}
</script>

<template>
  <form
    class="filters"
    @submit.prevent="apply"
  >
    <div class="toolbar-row">
      <details class="filter-disclosure">
        <summary>筛选条件</summary>
        <div class="filter-grid">
          <label><span>年份</span><input
            v-model.number="draft.year"
            list="result-year-facets"
            min="1900"
            max="2100"
            type="number"
            placeholder="全部"
          ><datalist id="result-year-facets"><option
            v-for="[year, count] in yearFacets"
            :key="year"
            :value="year"
          >{{ year }}（{{ count }}）</option></datalist></label>
          <label><span>期刊</span><input
            v-model="draft.journal"
            list="result-journal-facets"
            type="text"
            placeholder="如 Nature Medicine"
          ><datalist id="result-journal-facets"><option
            v-for="[journal, count] in journalFacets"
            :key="journal"
            :value="journal"
          >{{ journal }}（{{ count }}）</option></datalist></label>
          <label><span>文献类型</span><input
            v-model="draft.publication_type"
            list="result-publication-type-facets"
            type="text"
            placeholder="如 Meta-Analysis"
          ><datalist id="result-publication-type-facets"><option
            v-for="[type, count] in publicationTypeFacets"
            :key="type"
            :value="type"
          >{{ type }}（{{ count }}）</option></datalist></label>
          <label><span>作者</span><input
            v-model="draft.author"
            type="text"
            placeholder="如 Kim"
          ></label>
          <label><span>摘要</span><select v-model="draft.has_abstract"><option :value="null">全部</option><option :value="true">有摘要</option><option :value="false">无摘要</option></select></label>
          <label><span>保存</span><select v-model="draft.saved"><option :value="null">全部</option><option :value="true">已保存</option><option :value="false">未保存</option></select></label>
          <label><span>阅读状态</span><select v-model="draft.read_status"><option value="">全部</option><option value="read">已读</option><option value="reading">在读</option><option value="unread">未读</option></select></label>
          <label><span>标签</span><input
            v-model="draft.tags"
            type="text"
          ></label>
        </div>
        <div class="filter-actions">
          <button
            type="button"
            :disabled="props.disabled"
            @click="reset"
          >
            清空
          </button><button
            type="submit"
            :disabled="props.disabled"
          >
            应用筛选
          </button>
        </div>
      </details>
      <label class="sort-control"><span>排序：</span><select
        v-model="draft.sort"
        :disabled="props.disabled"
        @change="apply"
      ><option
        v-for="option in sorts"
        :key="option.value"
        :value="option.value"
        :disabled="!sortIsAvailable(option.value)"
      >{{ option.label }}{{ sortIsAvailable(option.value) ? "" : "（不可用）" }}</option></select></label>
      <details class="sort-help">
        <summary>排序依据</summary>
        <p>{{ sortUnavailableReason(draft.sort) ?? sortExplanation }}</p>
      </details>
    </div>
    <div
      v-if="appliedFilters.length"
      class="applied-filters"
      aria-label="已应用筛选"
    >
      <span>已应用：</span><button
        v-for="filter in appliedFilters"
        :key="filter.key"
        type="button"
        :disabled="props.disabled"
        @click="removeFilter(filter.key)"
      >
        {{ filter.label }} <span aria-hidden="true">×</span><span class="sr-only">移除</span>
      </button>
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
.applied-filters { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; padding:.42rem .95rem; border-bottom:1px solid var(--border-subtle); color:var(--text-muted); font-size:.75rem; }.applied-filters button { min-height:1.75rem; border:1px solid var(--border-strong); border-radius:999px; background:var(--surface); color:var(--text-primary); font:inherit; cursor:pointer; }.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
@media (max-width: 900px) { .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .filter-grid { grid-template-columns: 1fr; }.sort-help { flex-basis: 100%; } }
@media (prefers-reduced-motion: no-preference) { .sort-help p { transition: opacity 150ms ease; } }
</style>
