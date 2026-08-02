<script setup lang="ts">
import { reactive } from "vue";

import type { DocumentFilters } from "../../api/documents";

const props = defineProps<{ filters: Readonly<DocumentFilters>; disabled: boolean }>();
const emit = defineEmits<{ change: [filters: DocumentFilters] }>();
const draft = reactive<DocumentFilters>({
  parseStatus: props.filters.parseStatus,
  indexStatus: props.filters.indexStatus,
});

function apply(): void {
  emit("change", { ...draft });
}
</script>

<template>
  <form class="filters" @submit.prevent="apply">
    <label class="filter-field">
      <span>解析状态</span>
      <select v-model="draft.parseStatus">
        <option value="">全部</option>
        <option value="pending">等待</option>
        <option value="parsing">解析中</option>
        <option value="succeeded">成功</option>
        <option value="failed">失败</option>
      </select>
    </label>
    <label class="filter-field">
      <span>索引状态</span>
      <select v-model="draft.indexStatus">
        <option value="">全部</option>
        <option value="pending">等待</option>
        <option value="indexing">索引中</option>
        <option value="succeeded">成功</option>
        <option value="failed">失败</option>
        <option value="outdated">已过期</option>
      </select>
    </label>
    <button type="submit" :disabled="disabled">应用筛选</button>
  </form>
</template>

<style scoped>
.filters { display: flex; align-items: end; gap: 0.8rem; flex-wrap: wrap; }
.filter-field { display: grid; gap: 0.35rem; color: #52626b; font-size: 0.78rem; font-weight: 700; }
.filter-field select { min-width: 140px; border: 1px solid #c8d4d8; border-radius: 8px; padding: 0.55rem; background: #fff; }
.filters button { border: 0; border-radius: 8px; padding: 0.62rem 0.9rem; background: #1f514e; color: #fff; font-weight: 700; }
</style>
