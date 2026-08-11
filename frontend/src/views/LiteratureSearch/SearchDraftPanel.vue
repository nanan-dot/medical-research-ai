<script setup lang="ts">
import { computed } from "vue";
import type { ExpandedTerms, SearchIntentCandidate } from "../../api/literatureSearch";
import TermEvidencePanel from "./TermEvidencePanel.vue";

const props = defineProps<{
  query: string;
  loading: boolean;
  expanded: ExpandedTerms | null;
  candidate: SearchIntentCandidate | null;
}>();

const emit = defineEmits<{
  queryChange: [query: string];
  copy: [];
}>();

const queryModel = computed({
  get: () => props.query,
  set: (value: string) => emit("queryChange", value),
});
</script>

<template>
  <section class="draft-panel" aria-labelledby="draft-panel-title">
    <header class="panel-heading">
      <span class="evidence-track" aria-hidden="true" />
      <h2 id="draft-panel-title">2. 检索式草案</h2>
    </header>
    <TermEvidencePanel :expanded="props.expanded" :candidate="props.candidate" />
    <div class="query-editor">
      <label class="sr-only" for="search-query-draft">可编辑检索式草案</label>
      <textarea
        id="search-query-draft"
        v-model="queryModel"
        maxlength="2000"
        rows="7"
        :placeholder="props.loading ? '正在解析研究问题并生成检索式…' : '解析研究问题后，将在此生成可编辑的检索式。'"
        aria-describedby="query-editor-note"
      />
      <div id="query-editor-note" class="editor-meta">
        <button v-if="props.query" type="button" class="copy-action" @click="emit('copy')">复制</button>
        <span v-else>生成后可编辑</span>
        <span>{{ props.query.length }}/2000</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.draft-panel {
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  height: 100%;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-subtle, #dbe4f0);
  border-radius: 8px;
  background: var(--surface, #fff);
  box-shadow: 0 8px 24px rgb(15 42 67 / 5%);
}
.panel-heading { display: flex; gap: .55rem; align-items: center; }
.panel-heading h2 { margin: 0; color: var(--text-primary, #0f2a43); font-size: 1rem; line-height: 1.3; }
.evidence-track { width: 3px; height: 1.25rem; border-radius: 2px; background: var(--color-primary, #2563eb); }
.generate-action:focus-visible, textarea:focus-visible, .copy-action:focus-visible { outline: 2px solid var(--color-primary, #2563eb); outline-offset: 2px; }
.query-editor { display: grid; grid-template-rows: minmax(0, 1fr) auto; min-height: 0; overflow: hidden; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; }
textarea { box-sizing: border-box; width: 100%; min-height: 9.7rem; resize: vertical; padding: .75rem .8rem; border: 0; background: transparent; color: var(--text-primary, #0f2a43); font: inherit; font-size: .86rem; line-height: 1.5; }
textarea::placeholder { color: var(--text-muted, #64748b); opacity: 1; }
.editor-meta { display: flex; justify-content: space-between; gap: .75rem; align-items: center; min-height: 2rem; padding: .35rem .7rem; border-top: 1px solid var(--border-subtle, #dbe4f0); color: var(--text-muted, #64748b); font-size: .75rem; }
.copy-action { padding: 0; border: 0; background: transparent; color: var(--color-primary, #2563eb); font: inherit; font-size: inherit; cursor: pointer; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
</style>
