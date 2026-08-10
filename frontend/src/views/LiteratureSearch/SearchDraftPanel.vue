<script setup lang="ts">
// 检索式草案：按三段（核心概念/同义词扩展/研究类型）展示系统生成的布尔检索式。
// 仅展示真实 build-query 返回的检索式；无数据时显示诚实空状态。
// 三段划分基于后端 explanations/term_groups 语义；检索式为真实后端产物。
import { computed } from "vue";
import type { BuiltQuery, ExpandedTerms } from "../../api/literatureSearch";

const props = defineProps<{
  expanded: ExpandedTerms | null;
  result: BuiltQuery | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  build: [groups: unknown[]];
  copy: [];
}>();

// 从 term_groups 派生三段草稿；无真实数据时为 null（显示空状态）。
const coreConcept = computed<string | null>(() => {
  const group = props.expanded?.term_groups.find((g) => g.name === "disease" || g.name === "population");
  return group && group.terms.length ? group.terms.join(" OR ") : null;
});
const synonymExpansion = computed<string | null>(() => {
  const groups = props.expanded?.term_groups.filter((g) => g.name !== "disease" && g.name !== "population") ?? [];
  const parts = groups.filter((g) => g.terms.length).map((g) => g.terms.join(" OR "));
  return parts.length ? parts.join(" AND ") : null;
});
const studyType = computed<string | null>(() => {
  const group = props.expanded?.term_groups.find((g) => g.name === "study_type" || g.name === "study type");
  return group && group.terms.length ? group.terms.join(" OR ") : null;
});

const hasDraft = computed(() => Boolean(props.result?.boolean_query));
const fullQuery = computed(() => props.result?.boolean_query ?? "");
const sections = computed(() => [
  { label: "核心概念", value: coreConcept.value },
  { label: "同义词扩展", value: synonymExpansion.value },
  { label: "研究类型", value: studyType.value },
]);
</script>

<template>
  <section class="draft-panel" aria-labelledby="draft-panel-title">
    <header class="panel-head">
      <h3 id="draft-panel-title" class="panel-title">检索式草案</h3>
      <button
        v-if="hasDraft"
        type="button"
        class="text-action"
        aria-label="复制检索式"
        @click="emit('copy')"
      >
        复制
      </button>
    </header>

    <!-- 诚实空状态：未生成检索式时不展示任何虚构内容 -->
    <p v-if="!hasDraft && !loading" class="empty-hint">完善研究问题后生成检索式草案。</p>
    <p v-if="loading" class="empty-hint">正在生成检索式…</p>

    <template v-if="hasDraft">
      <div class="evidence-track" aria-hidden="true">
        <span class="track-line" />
        <span class="track-node" />
        <span class="track-node" />
        <span class="track-node" />
      </div>
      <div class="draft-sections">
        <div v-for="section in sections" :key="section.label" class="draft-section">
          <span class="draft-section-label">{{ section.label }}</span>
          <code v-if="section.value" class="draft-code">{{ section.value }}</code>
          <span v-else class="draft-muted">—</span>
        </div>
        <div class="draft-section draft-full">
          <span class="draft-section-label">完整检索式</span>
          <code class="draft-code full">{{ fullQuery }}</code>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.draft-panel {
  position: relative;
  display: grid;
  gap: 0.8rem;
  padding: 1.25rem;
  background: var(--surface, #fff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1rem;
}
.text-action {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--border-strong, #cbd5e1);
  border-radius: 6px;
  background: transparent;
  color: var(--color-primary, #2563eb);
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}
.empty-hint {
  margin: 0;
  color: var(--text-muted, #64748b);
  font-size: 0.875rem;
}
.evidence-track {
  position: absolute;
  left: 0.55rem;
  top: 3.4rem;
  bottom: 3.4rem;
  width: 2px;
  background: transparent;
}
.track-line {
  position: absolute;
  inset: 0;
  background: var(--color-primary, #2563eb);
  opacity: 0.35;
  border-radius: 1px;
}
.track-node {
  position: absolute;
  left: -3px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary, #2563eb);
}
.track-node:nth-of-type(2) {
  top: 33%;
}
.track-node:nth-of-type(3) {
  top: 66%;
}
.draft-sections {
  display: grid;
  gap: 0.6rem;
  margin-left: 1.1rem;
}
.draft-section {
  display: grid;
  gap: 0.3rem;
}
.draft-section-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary, #475569);
}
.draft-code {
  padding: 0.5rem 0.7rem;
  background: var(--surface-muted, #f1f5f9);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 6px;
  font-size: 0.8rem;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  color: var(--text-primary, #0f2a43);
}
.draft-code.full {
  background: var(--color-primary-soft, #eff6ff);
}
.draft-muted {
  color: var(--text-muted, #64748b);
  font-size: 0.85rem;
}
</style>
