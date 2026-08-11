<script setup lang="ts">
import type { ClaimKind } from "../../api/paperAnalysis";
import EvidenceCard from "./EvidenceCard.vue";
import type { EvidenceCardModel } from "./paperModel";

/**
 * 右侧证据栏（Evidence Context Rail）。
 * 证据数量取 sources.length（真实字段）；为空时展示引导文案而非伪造证据。
 * <1100px 时由页面容器将本栏渲染为底部抽屉（仅保留 body 区域与触发按钮）。
 */
const props = defineProps<{
  cards: readonly EvidenceCardModel[];
  sourceKinds: ReadonlyMap<number, readonly ClaimKind[]>;
}>();

const emit = defineEmits<{ jump: [localIndex: number] }>();

const TITLE_PREFIX = "来源证据";

function titleFor(count: number): string {
  return count > 0 ? `${TITLE_PREFIX} · ${count}` : TITLE_PREFIX;
}
</script>

<template>
  <aside class="rail" aria-label="Evidence Context Rail">
    <header class="rail-head">
      <div>
        <p class="eyebrow">EVIDENCE · LIVE</p>
        <h2>{{ titleFor(cards.length) }}</h2>
      </div>
    </header>
    <p v-if="cards.length === 0" class="empty">
      尚无来源证据。生成分析后，每条结论的原文片段与页码将显示在这里。
    </p>
    <ul v-else class="card-list">
      <li v-for="card in cards" :key="card.source.local_index">
        <EvidenceCard :card="card" :source-kinds="props.sourceKinds.get(card.source.local_index) ?? []" @jump="emit('jump', $event)" />
      </li>
    </ul>
    <footer v-if="cards.length > 0" class="rail-foot">
      <span class="count-label">Evidence 数量</span>
      <span class="count-value">{{ cards.length }}</span>
    </footer>
  </aside>
</template>

<style scoped>
.rail {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  align-content: start;
  gap: 0.85rem;
  padding: 1.15rem;
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-raised);
  overflow-y: auto;
}
.rail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.eyebrow {
  margin: 0;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}
.rail h2 {
  margin: 0.1rem 0 0;
  font-size: 0.95rem;
  color: var(--text-primary);
}
.empty {
  margin: 0;
  padding: 1rem;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}
.card-list {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.rail-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-subtle);
  font-size: 0.76rem;
}
.count-label {
  color: var(--text-muted);
}
.count-value {
  font-weight: 800;
  color: var(--text-primary);
}
</style>
