<script setup lang="ts">
interface QuickAction { label: string; description: string; path: string; icon: string; status: "LIVE" | "MOCK" | "UNAVAILABLE"; }
defineProps<{ actions: QuickAction[] }>();
</script>
<template>
  <nav class="quick-actions" aria-label="快捷操作">
    <RouterLink v-for="action in actions" :key="action.path" :to="action.path" class="quick">
      <span class="quick-icon" aria-hidden="true">{{ action.icon }}</span>
      <span class="quick-copy"><b>{{ action.label }}</b><span>{{ action.description }}</span></span>
      <span class="quick-status" :class="action.status.toLowerCase()">{{ action.status }}</span>
    </RouterLink>
  </nav>
</template>
<style scoped>
.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem}.quick{display:flex;align-items:center;gap:.7rem;min-width:0;padding:.8rem .9rem;background:var(--surface);border:1px solid var(--border-subtle);border-radius:12px;color:var(--text-primary);text-decoration:none;transition:border-color .15s,box-shadow .15s}.quick:hover{border-color:var(--color-primary)}.quick-icon{flex-shrink:0;display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:var(--surface-muted);color:var(--color-primary)}.quick-copy{display:grid;gap:.1rem;min-width:0}.quick-copy b{font-size:.86rem}.quick-copy span{color:var(--text-muted);font-size:.75rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.quick-status{flex-shrink:0;font-size:.68rem;font-weight:800}.quick-status.live{color:var(--color-success)}.quick-status.mock{color:var(--color-warning)}.quick-status.unavailable{color:var(--text-faint)}@media(max-width:1100px){.quick-actions{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.quick-actions{grid-template-columns:1fr}}
</style>
