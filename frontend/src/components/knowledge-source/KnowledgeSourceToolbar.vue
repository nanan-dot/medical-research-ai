<script setup lang="ts">
import type { KnowledgeSourceSort } from "../../api/knowledgeSources";
import BaseIcon from "../ui/BaseIcon.vue";

const props = defineProps<{ modelValue: string; sort: KnowledgeSourceSort; total: number; filterOpen: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: string]; "update:sort": [value: KnowledgeSourceSort]; "toggle-filter": [] }>();
function clear(): void { emit("update:modelValue", ""); }
</script>

<template>
  <section
    class="tools"
    aria-label="知识来源工具栏"
    data-testid="knowledge-source-toolbar"
  >
    <div class="search">
      <BaseIcon name="search" /><input
        :value="props.modelValue"
        aria-label="搜索来源名称、路径或研究项目"
        placeholder="搜索来源名称、路径、研究项目…"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      ><button
        v-if="props.modelValue"
        type="button"
        aria-label="清空搜索"
        @click="clear"
      >
        <BaseIcon name="close" />
      </button>
    </div>
    <button
      type="button"
      class="filter-button"
      :aria-expanded="filterOpen"
      @click="emit('toggle-filter')"
    >
      <BaseIcon name="filter" />筛选
    </button>
    <select
      :value="sort"
      aria-label="排序方式"
      @change="emit('update:sort', ($event.target as HTMLSelectElement).value as KnowledgeSourceSort)"
    >
      <option value="last_opened">最近使用</option><option value="pinned">置顶优先</option><option value="last_sync">最近同步</option><option value="name">名称</option><option value="document_count">文档数</option>
    </select>
    <small>找到 {{ total }} 个来源</small>
  </section>
</template>

<style scoped>
.tools { display:grid; grid-template-columns:minmax(0,1fr) auto 128px; gap:10px; align-items:center; }.search { display:flex; align-items:center; min-width:0; height:38px; padding:0 11px; border:1px solid #dfe7f3; border-radius:7px; background:#fff; color:#7283a1; }.search > .icon { flex:none; font-size:16px; }.search input { min-width:0; flex:1; border:0; outline:0; background:transparent; padding:0 8px; color:#17274a; font-size:13px; }.search button { display:grid; padding:3px; border:0; background:transparent; color:#7283a1; font-size:16px; }.filter-button,.tools select { height:38px; border:1px solid #dfe7f3; border-radius:7px; background:#fff; color:#314566; font-size:13px; font-weight:700; }.filter-button { display:flex; align-items:center; gap:6px; padding:0 11px; }.filter-button .icon { font-size:15px; }.tools select { width:128px; padding:0 9px; }.tools small { grid-column:1/-1; margin-top:-2px; color:#7887a2; font-size:11px; }
@media (max-width:767px) { .tools { grid-template-columns:minmax(0,1fr) auto; }.search { grid-column:1/-1; }.tools select { grid-column:1/-1; width:100%; } }
</style>
