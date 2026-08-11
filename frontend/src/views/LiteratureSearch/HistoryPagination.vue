<script setup lang="ts">
const props = defineProps<{
  currentPage: number;
  totalPages: number;
  isLoading: boolean;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
}>();
const emit = defineEmits<{ previous: []; next: [] }>();
</script>

<template>
  <nav class="pagination" aria-label="历史分页">
    <button type="button" :disabled="!props.hasPreviousPage || props.isLoading" @click="emit('previous')">上一页</button>
    <span class="page-note">第 {{ props.currentPage }} / {{ props.totalPages }} 页</span>
    <button type="button" :disabled="!props.hasNextPage || props.isLoading" @click="emit('next')">下一页</button>
  </nav>
</template>

<style scoped>
.pagination { display: flex; align-items: center; justify-content: center; gap: .8rem; }.pagination button { padding: .5rem .85rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); color: var(--text-primary); font: inherit; font-weight: 700; cursor: pointer; }.pagination button:disabled { cursor: not-allowed; opacity: .5; }.page-note { color: var(--text-muted); font-size: .86rem; }
</style>
