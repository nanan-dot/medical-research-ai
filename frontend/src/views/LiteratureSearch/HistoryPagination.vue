<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ currentPage: number; totalPages: number; total: number; isLoading: boolean; hasPreviousPage: boolean; hasNextPage: boolean }>();
const emit = defineEmits<{ previous: []; next: []; page: [page: number] }>();
const pages = computed(() => {
  if (props.totalPages <= 6) return Array.from({ length: props.totalPages }, (_, index) => index + 1);
  return [1, 2, 3, 4, 5, props.totalPages];
});
</script>
<template><nav class="pagination" aria-label="历史分页"><button type="button" aria-label="上一页" :disabled="!props.hasPreviousPage || props.isLoading" @click="emit('previous')">‹</button><button v-for="(page, index) in pages" :key="page" type="button" :class="{ current: page === props.currentPage }" :disabled="props.isLoading" :aria-current="page === props.currentPage ? 'page' : undefined" @click="emit('page', page)"><span v-if="index === pages.length - 1 && page - pages[index - 1] > 1">…</span>{{ page }}</button><button type="button" aria-label="下一页" :disabled="!props.hasNextPage || props.isLoading" @click="emit('next')">›</button><span class="page-size">10 条/页　共 {{ props.total }} 条</span></nav></template>
<style scoped>.pagination { display:flex; align-items:center; justify-content:center; gap:5px; padding:16px 0 3px; }.pagination button { display:grid; min-width:26px; height:26px; place-items:center; padding:0 5px; border:1px solid transparent; border-radius:5px; background:transparent; color:var(--text-secondary); font:11px inherit; cursor:pointer; }.pagination button.current { border-color:#8ab9ff; background:#f2f7ff; color:var(--color-primary); }.pagination button:disabled { cursor:not-allowed; opacity:.45; }.page-size { margin-left:9px; color:var(--text-muted); font-size:10px; }</style>
