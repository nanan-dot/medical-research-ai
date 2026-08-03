<script setup lang="ts">
import EvidenceItem, { type EvidenceItemModel } from "./EvidenceItem.vue";
defineProps<{ title?: string; items: readonly EvidenceItemModel[] }>();
const emit = defineEmits<{ open: [item: EvidenceItemModel] }>();
</script>
<template><aside class="panel"><p class="eyebrow">EVIDENCE · LIVE</p><h2>{{ title || "证据与上下文" }}</h2><p v-if="items.length === 0" class="empty">当前内容没有可定位的证据。</p><EvidenceItem v-for="item in items" :key="item.id" :item="item" @open="emit('open', $event)" /></aside></template>
<style scoped>.panel{display:grid;align-content:start;gap:.75rem;padding:1rem;border-left:1px solid var(--border-subtle);background:var(--surface-raised)}.eyebrow{margin:0;color:var(--color-primary);font-size:.7rem;font-weight:900;letter-spacing:.1em}.panel h2{margin:0;font-size:1rem}.empty{color:var(--text-muted);font-size:.85rem}</style>
