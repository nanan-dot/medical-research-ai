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
  <form class="filters" @submit.prevent="apply"><strong>筛选文档</strong>
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
.filters{display:flex;align-items:end;gap:.8rem;flex-wrap:wrap;padding:1.1rem 1.25rem;border:1px solid var(--border-subtle);border-radius:12px;background:#fff}.filters strong{margin-right:1rem;color:#10213d;font-size:1rem}.filter-field{display:grid;gap:.35rem;color:var(--text-muted);font-size:.8rem;font-weight:700}.filter-field select{min-width:150px;border:1px solid var(--border-strong);border-radius:8px;padding:.58rem .7rem;background:#fff}.filters button{border:1px solid var(--border-strong);border-radius:8px;padding:.6rem .9rem;background:#fff;color:var(--color-primary);font-weight:700}
</style>
