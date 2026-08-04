<script setup lang="ts">
import ConfidenceBadge from "./ConfidenceBadge.vue";
import SourceLocator from "./SourceLocator.vue";
import type { InsightBlockModel } from "./paperModel";
import { confidenceOf } from "./paperModel";

/**
 * 中央分析章节块（Research Block）：章节标题 + 分析结论 + 证据页码引用。
 * 每个结论通过 ConfidenceBadge 标记 kind 推导的置信度，并可定位到对应来源页码。
 */
defineProps<{ block: InsightBlockModel }>();

const emit = defineEmits<{ jump: [localIndex: number] }>();

function kindLabel(kind: InsightBlockModel["fieldValue"]["kind"]): string {
  if (kind === "not_found") return "原文未找到";
  if (kind === "fact") return "事实";
  if (kind === "summary") return "总结";
  return "推断";
}
</script>

<template>
  <article class="block" :aria-label="block.label">
    <header class="block-head">
      <h3 class="block-title">{{ block.label }}</h3>
      <span class="kind" :class="`kind--${block.fieldValue.kind}`">{{ kindLabel(block.fieldValue.kind) }}</span>
    </header>
    <p class="value">{{ block.fieldValue.value }}</p>
    <div v-if="block.evidenceCards.length > 0" class="refs">
      <span class="refs-label">来源</span>
      <SourceLocator
        v-for="card in block.evidenceCards"
        :key="card.source.local_index"
        :source="card.source"
        @jump="emit('jump', $event)"
      />
    </div>
    <footer v-else class="block-foot">
      <ConfidenceBadge :level="confidenceOf(block.fieldValue)" />
      <span class="no-source">此结论暂无对应来源页码</span>
    </footer>
  </article>
</template>

<style scoped>
.block {
  display: grid;
  gap: 0.55rem;
  padding: 1.15rem 1.35rem;
  border-left: 3px solid var(--color-primary);
  border-radius: 4px var(--radius-md) var(--radius-md) 4px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.block-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.block-title {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary);
}
.kind {
  padding: 0.16rem 0.5rem;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 800;
}
.kind--fact {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.kind--summary {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.kind--inference {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.kind--not_found {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.value {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.refs {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.refs-label {
  color: var(--text-faint);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.block-foot {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.no-source {
  color: var(--text-faint);
  font-size: 0.76rem;
}
</style>
