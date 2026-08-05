<script setup lang="ts">
import { reactive, watch } from "vue";

import type { ResultFilterValues, SearchSort } from "../../api/literatureSearch";

interface Props {
  filters: Readonly<ResultFilterValues>;
  disabled: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{ apply: [filters: ResultFilterValues] }>();

// 排序枚举的中文说明：说明排序信号，方便用户理解"排序理由"。
const SORT_OPTIONS: Array<{ value: SearchSort; label: string; hint: string }> = [
  { value: "relevance", label: "相关性", hint: "PubMed 本次检索内的默认排序" },
  { value: "newest", label: "最新", hint: "按发表年份降序" },
  { value: "classic", label: "经典代表性", hint: "权威期刊 + 已核实 + 近 5 年" },
  { value: "custom", label: "自定义", hint: "按你设定的手动顺序" },
];

function cloneFilters(source: ResultFilterValues): ResultFilterValues {
  return { ...source };
}

// 草稿状态由外部筛选值初始化；外部变化（URL 回退/前进）时同步草稿。
const draft = reactive<ResultFilterValues>(cloneFilters(props.filters));
watch(
  () => props.filters,
  (next) => Object.assign(draft, cloneFilters(next)),
  { deep: true },
);

function apply(): void {
  emit("apply", { ...draft });
}

function reset(): void {
  emit("apply", {
    year: null,
    publication_type: "",
    journal: "",
    author: "",
    has_abstract: null,
    saved: null,
    read_status: "",
    tags: "",
    sort: draft.sort,
  });
}
</script>

<template>
  <form class="filters" @submit.prevent="apply">
    <div class="filter-grid">
      <label class="filter-field">
        <span>年份</span>
        <input v-model.number="draft.year" min="1900" max="2100" type="number" placeholder="全部" />
      </label>
      <label class="filter-field">
        <span>期刊</span>
        <input v-model="draft.journal" type="text" placeholder="如 Nature Medicine" />
      </label>
      <label class="filter-field">
        <span>文献类型</span>
        <input v-model="draft.publication_type" type="text" placeholder="如 Meta-Analysis" />
      </label>
      <label class="filter-field">
        <span>作者</span>
        <input v-model="draft.author" type="text" placeholder="如 Kim" />
      </label>
      <label class="filter-field">
        <span>有摘要</span>
        <select v-model="draft.has_abstract">
          <option :value="null">全部</option>
          <option :value="true">有摘要</option>
          <option :value="false">无摘要</option>
        </select>
      </label>
      <label class="filter-field">
        <span>已保存</span>
        <select v-model="draft.saved">
          <option :value="null">全部</option>
          <option :value="true">已保存</option>
          <option :value="false">未保存</option>
        </select>
      </label>
      <label class="filter-field">
        <span>已读</span>
        <select v-model="draft.read_status">
          <option value="">全部</option>
          <option value="read">已读</option>
          <option value="unread">未读</option>
        </select>
      </label>
      <label class="filter-field">
        <span>标签</span>
        <input v-model="draft.tags" type="text" placeholder="如 key" />
      </label>
    </div>
    <div class="filter-footer">
      <label class="filter-field sort-field">
        <span>排序</span>
        <select v-model="draft.sort">
          <option v-for="option in SORT_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }} · {{ option.hint }}
          </option>
        </select>
      </label>
      <p class="sort-note">排序理由会在每条结果上显示，可解释、不虚构被引量。</p>
      <div class="actions">
        <button type="button" :disabled="disabled" @click="reset">清空筛选</button>
        <button type="submit" :disabled="disabled">应用筛选</button>
      </div>
    </div>
  </form>
</template>

<style scoped>
.filters { display: grid; gap: 0.8rem; padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); }
.filter-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.7rem; }
.filter-field { display: grid; gap: 0.35rem; color: var(--text-muted); font-size: 0.78rem; font-weight: 700; }
.filter-field input, .filter-field select { width: 100%; padding: 0.55rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); font: inherit; }
.filter-footer { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
.sort-field { min-width: 260px; }
.sort-note { margin: 0; color: var(--text-faint); font-size: 0.76rem; flex: 1; min-width: 200px; }
.actions { display: flex; gap: 0.5rem; margin-left: auto; }
.actions button { border: 0; border-radius: 8px; padding: 0.55rem 0.9rem; font-weight: 700; }
.actions button[type="submit"] { background: var(--color-primary); color: #fff; }
.actions button[type="button"] { border: 1px solid var(--border-strong); background: var(--paper); color: var(--text-primary); }
.actions button:disabled { opacity: 0.55; }
@media (max-width: 900px) { .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .filter-grid { grid-template-columns: 1fr; } }
</style>
