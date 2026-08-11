<script setup lang="ts">
import { computed } from "vue";
import type { ExpandedTerms, SearchIntentCandidate } from "../../api/literatureSearch";

const props = defineProps<{
  expanded: ExpandedTerms | null;
  candidate: SearchIntentCandidate | null;
}>();

const sourceLabels: Record<string, string> = {
  curated_local_mapping: "本地医学词表",
  user_supplied: "待确认术语",
};

const groups = computed(() => props.expanded?.term_groups ?? []);
const warnings = computed(() => props.expanded?.warnings ?? []);
const meshCount = computed(() => props.expanded?.mesh_candidates.length ?? 0);

function sourceLabel(source: string): string {
  return sourceLabels[source] ?? source;
}

function originalTerm(groupName: string, fallback: string): string {
  const candidate = props.candidate;
  if (!candidate) return fallback;
  const values: Record<string, string | null> = {
    disease: candidate.disease,
    intervention: candidate.intervention,
    target: candidate.target,
    mechanism: candidate.mechanism,
    topic: candidate.topic,
  };
  return values[groupName] || fallback;
}
</script>

<template>
  <section class="term-evidence" aria-labelledby="term-evidence-title">
    <div class="term-evidence-heading">
      <div>
        <h3 id="term-evidence-title">术语依据</h3>
        <p>系统生成的 PubMed 术语；英文词不需要手动输入。</p>
      </div>
      <span v-if="meshCount" class="mesh-count">{{ meshCount }} 个 MeSH 候选</span>
    </div>

    <p v-if="groups.length === 0 && warnings.length === 0" class="term-empty">
      解析研究问题后，这里会显示中文概念与实际检索词的对应关系。
    </p>

    <ul v-else-if="groups.length" class="term-list">
      <li v-for="group in groups" :key="group.name" class="term-row">
        <span class="term-core">{{ originalTerm(group.name, group.core_term) }}</span>
        <span class="term-arrow" aria-hidden="true">→</span>
        <span class="term-values">{{ group.terms.join(" · ") }}</span>
        <span class="term-source">{{ sourceLabel(group.source) }}</span>
      </li>
    </ul>

    <ul v-if="warnings.length" class="term-warnings" aria-live="polite">
      <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
    </ul>
  </section>
</template>

<style scoped>
.term-evidence { display: grid; gap: 8px; padding: 12px; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 6px; background: var(--surface-muted, #f8fafc); }
.term-evidence-heading { display: flex; gap: 12px; align-items: start; justify-content: space-between; }
.term-evidence h3, .term-evidence p { margin: 0; }
.term-evidence h3 { color: var(--text-primary, #0f2a43); font-size: .82rem; font-weight: 700; }
.term-evidence p { margin-top: 2px; color: var(--text-muted, #64748b); font-size: .72rem; line-height: 1.45; }
.mesh-count, .term-source { color: var(--text-muted, #64748b); font-size: .7rem; white-space: nowrap; }
.term-list, .term-warnings { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
.term-row { display: grid; grid-template-columns: minmax(74px, .7fr) auto minmax(0, 1.6fr) auto; gap: 8px; align-items: baseline; min-width: 0; padding: 6px 0; border-top: 1px solid var(--border-subtle, #dbe4f0); font-size: .75rem; }
.term-core { color: var(--text-primary, #0f2a43); font-weight: 600; }
.term-arrow { color: var(--text-faint, #94a3b8); }
.term-values { min-width: 0; overflow: hidden; color: var(--text-secondary, #475569); font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; font-size: .72rem; text-overflow: ellipsis; white-space: nowrap; }
.term-warnings { padding: 8px; border-left: 2px solid var(--color-warning, #d97706); background: var(--color-warning-soft, #fef3c7); color: #854d0e; font-size: .72rem; line-height: 1.45; }
.term-empty { padding-top: 4px; }
@media (max-width: 640px) { .term-row { grid-template-columns: 1fr auto; }.term-values { grid-column: 1 / -1; white-space: normal; overflow: visible; }.term-source { text-align: right; } }
</style>
