<script setup lang="ts">
const props = defineProps<{ modelValue: "all" | "changes" | "failed" }>();
const emit = defineEmits<{ "update:modelValue": [value: "all" | "changes" | "failed"] }>();
</script>

<template>
  <div class="quick-filters" aria-label="快捷筛选">
    <button type="button" :class="{ active: props.modelValue === 'all' }" @click="emit('update:modelValue', 'all')">全部策略</button>
    <button type="button" :class="{ active: props.modelValue === 'changes' }" @click="emit('update:modelValue', 'changes')">有更新</button>
    <button type="button" :class="{ active: props.modelValue === 'failed' }" @click="emit('update:modelValue', 'failed')">执行失败</button>
  </div>
</template>

<style scoped>
.quick-filters { display:flex; gap:8px; margin-top:10px; }.quick-filters button { min-height:25px; padding:0 9px; border:1px solid var(--border-subtle); border-radius:6px; background:var(--surface); color:var(--text-secondary); font:600 11px/1 inherit; cursor:pointer; }.quick-filters button.active { border-color:#9cc4ff; background:var(--color-primary-soft); color:var(--color-primary); }
</style>

