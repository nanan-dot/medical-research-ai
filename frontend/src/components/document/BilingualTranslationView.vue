<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  sourceQuote: string;
  revision: { source_anchor_id: number; translated_text: string; alignment: readonly Readonly<Record<string, unknown>>[] };
  mode: "source" | "bilingual";
}>();
const emit = defineEmits<{ locate: [] }>();

const alignedRows = computed(() => {
  const spans = props.revision.alignment;
  if (!spans.length) return [{ source: props.sourceQuote, target: props.revision.translated_text, precise: false }];
  return spans.map(span => {
    const sourceStart = Number(span.source_start); const sourceEnd = Number(span.source_end);
    const targetStart = Number(span.target_start); const targetEnd = Number(span.target_end);
    const precise = Number.isInteger(sourceStart) && Number.isInteger(sourceEnd) && Number.isInteger(targetStart) && Number.isInteger(targetEnd);
    return { source: precise ? props.sourceQuote.slice(sourceStart, sourceEnd) : props.sourceQuote,
      target: precise ? props.revision.translated_text.slice(targetStart, targetEnd) : props.revision.translated_text, precise };
  });
});
</script>

<template>
  <div v-if="props.mode === 'bilingual'" class="bilingual-result" aria-label="原文与译文对照">
    <article v-for="(row, index) in alignedRows" :key="`${index}-${row.source}`" class="aligned-row">
      <button type="button" class="source-cell" :disabled="!row.precise" :title="row.precise ? '在 PDF 中定位同一原文锚点' : '此译文没有精确句级对齐'" @click="emit('locate')">
        {{ row.source }}
      </button>
      <p class="target-cell">{{ row.target }}</p>
    </article>
    <p v-if="alignedRows.some(row => !row.precise)" class="alignment-degraded" role="status">该段缺少精确句级对齐；点击定位已降级，仍可通过原文锚点回溯。</p>
  </div>
  <p v-else class="translated-text">{{ props.revision.translated_text }}</p>
</template>

<style scoped>
.bilingual-result { display: grid; gap: .55rem; }.aligned-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); border: 1px solid var(--border-subtle); }.source-cell, .target-cell { min-width: 0; margin: 0; padding: .65rem; font-size: .82rem; line-height: 1.65; text-align: left; }.source-cell { border: 0; border-right: 1px solid var(--border-subtle); background: color-mix(in srgb, var(--color-primary) 4%, var(--paper)); color: var(--text-primary); cursor: pointer; font: inherit; }.source-cell:disabled { cursor: not-allowed; opacity: .72; }.target-cell { white-space: pre-wrap; }.source-cell:focus-visible { outline: 3px solid color-mix(in srgb, var(--color-primary) 45%, transparent); outline-offset: -3px; }.alignment-degraded { margin: 0; color: var(--text-muted); font-size: .76rem; line-height: 1.5; }
@media (max-width: 520px) { .aligned-row { grid-template-columns: 1fr; }.source-cell { border-right: 0; border-bottom: 1px solid var(--border-subtle); } }
</style>
