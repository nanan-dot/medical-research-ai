<script setup lang="ts">
const props = defineProps<{ page: number; totalPages: number; total: number; pending?: boolean }>();
const emit = defineEmits<{ change: [page: number] }>();

function pages(): number[] {
  return Array.from({ length: props.totalPages }, (_, index) => index + 1);
}
</script>

<template>
  <nav v-if="props.totalPages > 1" class="pagination" aria-label="推荐文献分页">
    <span class="page-summary">共 {{ props.total }} 篇，第 {{ props.page }} / {{ props.totalPages }} 页</span>
    <div class="page-actions">
      <button type="button" :disabled="props.pending || props.page === 1" @click="emit('change', props.page - 1)">上一页</button>
      <button v-for="pageNumber in pages()" :key="pageNumber" type="button" :disabled="props.pending" :class="{ active: pageNumber === props.page }" :aria-current="pageNumber === props.page ? 'page' : undefined" @click="emit('change', pageNumber)">{{ pageNumber }}</button>
      <button type="button" :disabled="props.pending || props.page === props.totalPages" @click="emit('change', props.page + 1)">下一页</button>
    </div>
  </nav>
</template>

<style scoped>
.pagination{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 16px;border-top:1px solid #dce5f0;background:#fff}.page-summary{color:#46617f;font-size:12px}.page-actions{display:flex;align-items:center;gap:6px}.page-actions button{min-width:31px;height:31px;padding:0 9px;border:1px solid #d5e2f2;border-radius:5px;background:#fff;color:#244978;font-size:12px;cursor:pointer}.page-actions button.active{border-color:#075ce9;background:#075ce9;color:#fff}.page-actions button:disabled{cursor:not-allowed;opacity:.48}.page-actions button:focus-visible{outline:2px solid #0b5fcc;outline-offset:2px}@media(max-width:640px){.pagination{align-items:stretch;flex-direction:column}.page-actions{flex-wrap:wrap}}
</style>
