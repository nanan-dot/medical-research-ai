<script setup lang="ts">
import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{
  sources: readonly KnowledgeSource[];
  selectedSourceId: number | null;
  total: number;
}>();

const emit = defineEmits<{ select: [sourceId: number | null] }>();
</script>

<template>
  <nav class="scope-nav" aria-label="资料范围">
    <div class="scope-heading">
      <h2>资料范围</h2>
      <RouterLink to="/sources">管理资料</RouterLink>
    </div>
    <button class="scope-item" :class="{ active: props.selectedSourceId === null }" type="button" @click="emit('select', null)">
      <span class="source-copy">
        <span class="source-primary"><span class="folder-mark" aria-hidden="true">□</span><span class="source-name">全部文档</span></span>
      </span>
      <b class="count-badge">{{ props.total }}</b>
    </button>
    <p v-if="props.sources.length" class="source-label">知识文件夹</p>
    <button
      v-for="source in props.sources"
      :key="source.id"
      class="scope-item"
      :class="{ active: source.id === props.selectedSourceId }"
      type="button"
      @click="emit('select', source.id)"
    >
      <span class="source-copy">
        <span class="source-primary"><span class="folder-mark" aria-hidden="true">□</span><span class="source-name">{{ source.name }}</span></span>
        <small v-if="source.stats.failed > 0" class="failure-hint">{{ source.stats.failed }} 个异常</small>
      </span>
      <b class="count-badge">{{ source.stats.total_files }}</b>
    </button>
    <RouterLink v-if="!props.sources.length" class="empty-link" to="/sources">去知识库添加资料文件夹</RouterLink>
  </nav>
</template>

<style scoped>
.scope-nav {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 14px 10px;
}

.scope-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 2px 12px;
}

.scope-heading h2,
.scope-heading a,
.source-label { margin: 0; }
.scope-heading h2 { color: var(--ink-900, #10213d); font-size: 14px; font-weight: 700; }
.scope-heading a,
.empty-link { color: var(--color-primary); font-weight: 700; text-decoration: none; }
.scope-heading a { font-size: 12px; }

.scope-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 42px;
  padding: 8px 10px;
  border: 0;
  border-left: 2px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-size: 14px;
  text-align: left;
}

.scope-item:hover { background: var(--surface-muted); }
.scope-item.active { border-left-color: var(--color-primary); background: var(--color-primary-soft); color: var(--color-primary); font-weight: 700; }
.count-badge { flex: 0 0 auto; min-width: 25px; color: currentColor; font-size: 12px; font-variant-numeric: tabular-nums; text-align: right; }

.source-label { padding: 16px 2px 6px; color: var(--text-muted); font-size: 12px; font-weight: 600; }
.source-copy { display: grid; min-width: 0; gap: 2px; }
.source-primary { display: flex; min-width: 0; align-items: center; gap: 7px; }
.folder-mark { color: var(--color-primary); font-family: ui-monospace, monospace; font-size: 15px; }
.source-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.failure-hint { padding-left: 22px; color: var(--color-danger); font-size: 11px; font-weight: 600; line-height: 1.35; white-space: nowrap; }
.empty-link { padding: 10px 2px; font-size: 13px; }

@media (max-width: 1023px) {
  .scope-nav { flex-direction: row; align-items: center; gap: 4px; overflow-x: auto; padding: 8px 0; }
  .scope-heading { flex: 0 0 auto; padding: 0 8px 0 0; }
  .scope-heading a,
  .source-label { display: none; }
  .scope-item { flex: 0 0 auto; width: auto; min-width: max-content; }
  .empty-link { white-space: nowrap; }
}
</style>
