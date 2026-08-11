<script setup lang="ts">
import { computed } from "vue";
import type { ClaimKind } from "../../api/paperAnalysis";
import ConfidenceBadge from "./ConfidenceBadge.vue";
import SourceLocator from "./SourceLocator.vue";
import type { ConfidenceLevel, EvidenceCardModel } from "./paperModel";

/**
 * 单条证据卡：页码/引用行 + 原文摘录 + 来源匹配分。
 * confidence 仅当该卡作为某分析字段的证据时传入（由字段 kind 推导）；
 * 单独出现在证据栏时后端未定义该来源的置信度，因此不渲染徽章，避免伪造。
 */
const props = defineProps<{
  card: EvidenceCardModel;
  confidence?: ConfidenceLevel | null;
  sourceKinds: readonly ClaimKind[];
}>();

const emit = defineEmits<{ jump: [localIndex: number] }>();

function scoreText(score: number | null): string {
  return score === null ? "未提供" : String(score);
}

const KIND_LABELS: Readonly<Record<ClaimKind, string>> = {
  fact: "直接证据",
  summary: "模型总结",
  inference: "模型推断",
  not_found: "待核对",
};

const evidenceKinds = computed(() => {
  const labels = props.sourceKinds.map((kind) => KIND_LABELS[kind]);
  return labels.length > 0 ? labels : ["待核对"];
});
</script>

<template>
  <article class="card" :aria-label="`证据卡 ${card.source.local_index + 1}`">
    <header class="card-head">
      <span class="index">#{{ card.source.local_index + 1 }}</span>
      <ConfidenceBadge v-if="confidence" :level="confidence" />
    </header>
    <div class="kind-list" aria-label="证据状态">
      <span v-for="kind in evidenceKinds" :key="kind" class="kind">{{ kind }}</span>
    </div>
    <p class="excerpt">{{ card.excerpt || "原文摘录未提供" }}</p>
    <footer class="card-foot">
      <SourceLocator :source="card.source" @jump="emit('jump', $event)" />
      <span class="score">Score {{ scoreText(card.score) }}</span>
    </footer>
  </article>
</template>

<style scoped>
.card {
  display: grid;
  gap: 0.5rem;
  padding: 0.85rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow);
  transition: border-color 0.15s;
}
.card:hover {
  border-color: var(--color-primary);
}
.card-head,
.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.index {
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--text-faint);
  letter-spacing: 0.04em;
}
.excerpt {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.score {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--text-faint);
}
.kind-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.kind {
  padding: 0.12rem 0.42rem;
  border-radius: 99px;
  background: var(--surface-muted);
  color: var(--text-muted);
  font-size: 0.67rem;
  font-weight: 800;
}
</style>
