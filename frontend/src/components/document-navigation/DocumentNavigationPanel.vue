<script setup lang="ts">
import { computed, shallowRef, watch } from "vue";

import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{
  sources: readonly KnowledgeSource[];
  loading: boolean;
  defaultSourceId: number | null;
}>();

const emit = defineEmits<{
  search: [query: string, knowledgeSourceId: number | null, indexedOnly: boolean];
}>();

const query = shallowRef("");
const sourceId = shallowRef<number | null>(null);
const indexedOnly = shallowRef(true);
const canSubmit = computed(() => Boolean(query.value.trim()) && !props.loading);

function submit(): void {
  if (canSubmit.value) emit("search", query.value.trim(), sourceId.value, indexedOnly.value);
}

watch(
  () => props.defaultSourceId,
  (nextSourceId) => {
    sourceId.value = nextSourceId;
  },
  { immediate: true },
);
</script>

<template>
  <form class="navigation-panel" aria-label="AI 资料定位" @submit.prevent="submit">
    <div class="heading">
      <span class="ai-mark" aria-hidden="true">AI</span>
      <div>
        <strong>AI 资料定位</strong>
        <p>仅检索当前资料范围内已有的真实解析与索引结果。</p>
      </div>
    </div>
    <div class="query-row">
      <label class="visually-hidden" for="navigation-query">定位问题</label>
      <input id="navigation-query" v-model="query" maxlength="500" placeholder="在当前资料中定位内容…">
      <label class="scope-control">
        <span>范围</span>
        <select v-model="sourceId">
          <option :value="null">全部知识库</option>
          <option v-for="source in props.sources" :key="source.id" :value="source.id">{{ source.name }}</option>
        </select>
      </label>
      <label class="check"><input v-model="indexedOnly" type="checkbox">仅已索引</label>
      <button type="submit" :disabled="!canSubmit">{{ props.loading ? "定位中" : "定位" }}</button>
    </div>
  </form>
</template>

<style scoped>
.navigation-panel {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: #fbfdff;
}

.heading,
.query-row,
.scope-control,
.check {
  display: flex;
  align-items: center;
}

.heading { gap: 8px; }
.heading strong { color: var(--ink-900, #10213d); font-size: 0.78rem; }
.heading p { margin: 2px 0 0; color: var(--text-muted); font-size: 0.7rem; }

.ai-mark {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.61rem;
  font-weight: 800;
}

.query-row { gap: 8px; }
.query-row > input { min-width: 120px; flex: 1; }
.query-row > input,
.query-row select {
  box-sizing: border-box;
  height: 32px;
  border: 1px solid var(--border-subtle);
  border-radius: 5px;
  background: #fff;
  color: var(--text-primary);
  font: inherit;
  font-size: 0.73rem;
}

.query-row > input { padding: 0 8px; }
.scope-control,
.check { gap: 5px; color: var(--text-muted); font-size: 0.72rem; white-space: nowrap; }
.scope-control select { max-width: 170px; padding: 0 5px; }
.query-row button {
  height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 5px;
  background: var(--color-primary);
  color: #fff;
  font: inherit;
  font-size: 0.73rem;
  font-weight: 700;
}
.query-row button:disabled { opacity: 0.55; }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 700px) {
  .query-row { align-items: stretch; flex-direction: column; }
  .query-row > input { flex: none; }
  .scope-control select { max-width: none; flex: 1; }
  .query-row button { width: 100%; }
}
</style>
