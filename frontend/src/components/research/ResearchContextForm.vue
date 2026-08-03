<script setup lang="ts">
import type { ResearchCondition } from "../../types/research-prototype";
defineProps<{ conditions: ResearchCondition[] }>();
</script>

<template>
  <section class="form-card"><div class="section-heading"><div><p class="eyebrow">RESEARCH CONTEXT · MOCK</p><h2>研究条件</h2></div><span class="mock-badge">不会自动补全未知信息</span></div>
    <div class="condition-grid"><label v-for="condition in conditions" :key="condition.id" class="condition"><span>{{ condition.label }}</span><input :value="condition.value" readonly><small>未知 / 待导师确认</small></label></div>
  </section>
</template>

<style scoped>.form-card{padding:1.2rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}.section-heading{display:flex;justify-content:space-between;gap:1rem;align-items:start}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.section-heading h2{margin:.25rem 0}.mock-badge{padding:.35rem .55rem;border-radius:99px;background:var(--color-warning-soft);color:var(--color-warning);font-size:.78rem;font-weight:800}.condition-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin-top:1rem}.condition{display:grid;gap:.28rem;font-size:.85rem;font-weight:700}.condition input{min-width:0;padding:.58rem .65rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface-muted);color:var(--text-muted)}.condition small{color:var(--color-warning);font-weight:600}@media(max-width:720px){.condition-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.section-heading{display:block}.mock-badge{display:inline-block;margin-top:.5rem}}</style>
