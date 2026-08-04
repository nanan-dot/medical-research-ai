<script setup lang="ts">
const emit = defineEmits<{ open: []; submit: [query: string] }>();
</script>
<template>
  <form class="research-search" role="search" @submit.prevent="emit('submit', '')" @click="emit('open')">
    <span class="search-icon" aria-hidden="true">⌕</span>
    <input aria-label="全局搜索" placeholder="搜索论文、笔记、研究方向、任务..." @click.stop="emit('open')" />
    <kbd>Ctrl K</kbd>
  </form>
</template>
<style scoped>
.research-search{display:flex;align-items:center;gap:.7rem;height:60px;width:80%;max-width:760px;margin:0 auto;padding:0 1.1rem;background:var(--surface);border:1px solid var(--border-subtle);border-radius:12px;box-shadow:var(--shadow-card);transition:border-color .15s,box-shadow .15s}.research-search:hover,.research-search:focus-within{border-color:var(--color-primary);box-shadow:0 2px 10px rgba(37,99,235,.08)}.search-icon{color:var(--text-faint);font-size:1.15rem}.research-search input{flex:1;min-width:0;border:0;outline:0;color:var(--text-primary);font-size:.95rem;background:transparent}.research-search input::placeholder{color:var(--text-faint)}.research-search kbd{flex-shrink:0;padding:.28rem .5rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface-muted);color:var(--text-faint);font-size:.72rem}@media(max-width:540px){.research-search{width:100%;height:52px}}
</style>
