<script setup lang="ts">
interface FeatureEntryItem { label: string; description: string; path: string; icon: string; }
defineProps<{ items: FeatureEntryItem[] }>();
</script>
<template>
  <nav class="feature-entry" aria-label="研究能力入口">
    <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="entry">
      <span class="entry-icon" aria-hidden="true">{{ item.icon }}</span>
      <span class="entry-copy"><b>{{ item.label }}</b><span>{{ item.description }}</span></span>
    </RouterLink>
  </nav>
</template>
<style scoped>
.feature-entry{display:grid;grid-template-columns:repeat(3,1fr);gap:.9rem}.entry{display:flex;align-items:center;gap:.8rem;min-height:90px;padding:.9rem 1rem;background:var(--surface);border:1px solid var(--border-subtle);border-radius:12px;box-shadow:var(--shadow-card);color:var(--text-primary);text-decoration:none;transition:border-color .15s,box-shadow .15s,transform .15s}.entry:hover{border-color:var(--color-primary);box-shadow:0 2px 12px rgba(37,99,235,.08)}.entry-icon{display:grid;place-items:center;width:40px;height:40px;flex-shrink:0;border-radius:10px;background:var(--color-primary-soft);color:var(--color-primary);font-size:1.15rem}.entry-copy{display:grid;gap:.15rem;min-width:0}.entry-copy b{font-size:.9rem}.entry-copy span{color:var(--text-muted);font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}@media(max-width:1100px){.feature-entry{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.feature-entry{grid-template-columns:1fr}}
</style>
