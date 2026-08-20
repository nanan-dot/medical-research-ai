<script setup lang="ts">
import type { DocumentStatistics } from "../../api/documents";

const props = defineProps<{ summary: DocumentStatistics | null; loading: boolean; error?: boolean; active: "all" | "available" | "processing" | "needs_attention" }>();
const emit = defineEmits<{ select: [value: "all" | "available" | "processing" | "needs_attention"] }>();
const cards = [
  { key: "all", label: "全部文档", icon: "▣", value: (summary: DocumentStatistics) => summary.total },
  { key: "available", label: "可用于问答", icon: "✓", value: (summary: DocumentStatistics) => summary.available },
  { key: "processing", label: "处理中", icon: "◌", value: (summary: DocumentStatistics) => summary.processing },
  { key: "needs_attention", label: "需处理", icon: "!", value: (summary: DocumentStatistics) => summary.needs_attention },
] as const;
</script>

<template>
  <section class="summary" aria-label="文档库全局统计">
    <button v-for="card in cards" :key="card.key" type="button" class="card" :class="[`card--${card.key}`, { 'is-active': props.active === card.key }]" :aria-pressed="props.active === card.key" @click="emit('select', card.key)">
      <span class="icon" aria-hidden="true">{{ card.icon }}</span>
      <span><strong v-if="!props.loading && props.summary">{{ card.value(props.summary) }}</strong><strong v-else-if="props.error" class="unavailable">—</strong><strong v-else class="skeleton">&nbsp;</strong><small>{{ card.label }}</small></span>
    </button>
  </section>
</template>

<style scoped>
.summary { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:0 0 16px; }
.card { display:flex; align-items:center; gap:11px; min-width:0; min-height:72px; padding:10px 14px; border:1px solid var(--border-subtle); border-radius:10px; background:var(--surface); box-shadow:0 1px 2px rgb(15 23 42 / 3%); color:var(--text-primary); text-align:left; cursor:pointer; }.card:hover,.card:focus-visible,.card.is-active { border-color:var(--color-primary); background:#f8fbff; outline:none; }.icon { display:grid; width:30px; height:30px; flex:0 0 auto; place-items:center; border-radius:8px; background:var(--color-primary-soft); color:var(--color-primary); font-size:.9rem; font-weight:800; }.card--available .icon{background:var(--color-success-soft);color:var(--color-success)}.card--needs_attention .icon{background:var(--color-warning-soft);color:var(--color-warning)}strong,small{display:block}strong{font-size:1.1rem;line-height:1.1}small{margin-top:4px;color:var(--text-muted);font-size:.7rem;font-weight:700}.skeleton{width:30px;border-radius:4px;background:var(--surface-muted)}.unavailable{color:var(--text-faint)}@media(max-width:760px){.summary{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:0 0 12px}.card{min-height:60px;padding:8px 10px}.icon{width:25px;height:25px}}
</style>
