<script setup lang="ts">
import type { ResearchContext } from "../../api/researchContexts";
const props = defineProps<{
  query: string;
  researchContextId: string;
  framework: string;
  timeRange: string;
  archived: boolean;
  projects: ResearchContext[];
}>();

const emit = defineEmits<{
  "update:query": [value: string];
  "update:researchContextId": [value: string];
  "update:framework": [value: string];
  "update:timeRange": [value: string];
  "update:archived": [value: boolean];
}>();
</script>

<template>
  <div class="toolbar">
    <label class="search-field">
      <span class="sr-only">搜索检索策略</span>
      <span aria-hidden="true">⌕</span>
      <input :value="props.query" type="search" placeholder="搜索研究问题、策略名称、术语、MeSH…" @input="emit('update:query', ($event.target as HTMLInputElement).value)">
    </label>
    <label class="select-field">
      <span class="sr-only">项目</span>
      <select :value="props.researchContextId" @change="emit('update:researchContextId', ($event.target as HTMLSelectElement).value)">
        <option value="">全部项目</option>
        <option v-for="project in props.projects" :key="project.id" :value="String(project.id)">{{ project.name }}</option>
      </select>
    </label>
    <label class="select-field">
      <span class="sr-only">时间范围</span>
      <select :value="props.timeRange" @change="emit('update:timeRange', ($event.target as HTMLSelectElement).value)">
        <option value="">全部时间</option><option value="7">近 7 天</option><option value="30">近 30 天</option><option value="365">近一年</option>
      </select>
    </label>
    <label class="select-field framework-select">
      <span class="sr-only">研究框架</span>
      <select :value="props.framework" @change="emit('update:framework', ($event.target as HTMLSelectElement).value)">
        <option value="">筛选</option><option value="PICO">PICO</option><option value="PECO">PECO</option><option value="topic">主题检索</option>
      </select>
    </label>
    <label class="select-field archived-select">
      <span class="sr-only">归档状态</span>
      <select :value="String(props.archived)" @change="emit('update:archived', ($event.target as HTMLSelectElement).value === 'true')">
        <option value="false">未归档</option><option value="true">已归档</option>
      </select>
    </label>
  </div>
</template>

<style scoped>
.toolbar { display:flex; gap:10px; align-items:center; min-width:0; }.search-field,.select-field { display:flex; align-items:center; min-height:36px; border:1px solid var(--border-subtle); border-radius:7px; background:var(--surface); color:var(--text-muted); }.search-field { flex:1 1 270px; max-width:330px; gap:8px; padding:0 12px; }.search-field input,.select-field select { width:100%; min-width:0; border:0; outline:0; background:transparent; color:var(--text-primary); font:inherit; font-size:12px; }.select-field { min-width:112px; padding:0 8px; }.framework-select { min-width:76px; }.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }
@media (max-width: 760px) { .toolbar { flex-wrap:wrap; }.search-field { flex-basis:100%; max-width:none; }.select-field { flex:1; } }
</style>

