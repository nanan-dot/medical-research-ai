<script setup lang="ts">
import { computed } from "vue";
import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{
  sources: readonly KnowledgeSource[];
  selectedSourceId: number | null;
  recentSourceIds: readonly number[];
  total: number;
}>();

const emit = defineEmits<{ select: [sourceId: number | null] }>();
const recentSources = computed(() => [...new Set(props.recentSourceIds)]
  .map((id) => props.sources.find((source) => source.id === id))
  .filter((source): source is KnowledgeSource => source !== undefined));
const groups = computed(() => [
  { label: "本地文件夹", sourceType: "local_folder", sources: props.sources.filter((source) => source.source_type === "local_folder") },
  { label: "Obsidian Vault", sourceType: "obsidian_vault", sources: props.sources.filter((source) => source.source_type === "obsidian_vault") },
]);
</script>

<template>
  <nav class="scope-nav" aria-label="资料范围">
    <div class="scope-heading">
      <h2>知识来源</h2>
      <RouterLink to="/sources">管理来源</RouterLink>
    </div>

    <button class="scope-item" :class="{ active: props.selectedSourceId === null }" type="button" @click="emit('select', null)">
      <span class="source-primary">
        <svg class="type-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.2a1.5 1.5 0 0 1 1.1.47L11.3 7h8.2A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5v-11Z"/></svg>
        <span class="source-name">全部文档</span>
      </span>
      <b class="count-badge">{{ props.total }}</b>
    </button>

    <section v-if="recentSources.length" class="source-section" aria-label="最近使用">
      <p class="source-label">最近使用</p>
      <button v-for="source in recentSources" :key="source.id" class="scope-item scope-item--recent" :class="{ active: source.id === props.selectedSourceId }" type="button" @click="emit('select', source.id)">
        <span class="source-primary">
          <svg v-if="source.source_type === 'obsidian_vault'" class="type-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="#7C3AED" d="M7.2 2h9.6a2 2 0 0 1 1.7.94l3 4.66a2 2 0 0 1 .28 1.06V19a2 2 0 0 1-2 2H4.2a2 2 0 0 1-2-2V8.66a2 2 0 0 1 .28-1.06l3-4.66A2 2 0 0 1 7.2 2Z"/><circle cx="12" cy="13" r="4.6" fill="#fff"/><circle cx="12" cy="13" r="1.5" fill="#1E1B18"/></svg>
          <svg v-else class="type-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.2a1.5 1.5 0 0 1 1.1.47L11.3 7h8.2A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5v-11Z"/></svg>
          <span class="source-name">{{ source.name }}</span>
        </span>
        <b class="count-badge">{{ source.stats.total_files }}</b>
      </button>
    </section>

    <template v-for="group in groups" :key="group.label">
      <p class="source-label">{{ group.label }} <span class="source-label-count">({{ group.sources.length }})</span></p>
      <button v-for="source in group.sources" :key="source.id" class="scope-item" :class="{ active: source.id === props.selectedSourceId }" type="button" @click="emit('select', source.id)">
        <span class="source-primary">
          <svg v-if="group.sourceType === 'obsidian_vault'" class="type-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="#7C3AED" d="M7.2 2h9.6a2 2 0 0 1 1.7.94l3 4.66a2 2 0 0 1 .28 1.06V19a2 2 0 0 1-2 2H4.2a2 2 0 0 1-2-2V8.66a2 2 0 0 1 .28-1.06l3-4.66A2 2 0 0 1 7.2 2Z"/><circle cx="12" cy="13" r="4.6" fill="#fff"/><circle cx="12" cy="13" r="1.5" fill="#1E1B18"/></svg>
          <svg v-else class="type-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.2a1.5 1.5 0 0 1 1.1.47L11.3 7h8.2A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5v-11Z"/></svg>
          <span class="source-name">{{ source.name }}</span>
        </span>
        <b class="count-badge">{{ source.stats.total_files }}</b>
      </button>
      <RouterLink v-if="!group.sources.length && group.sourceType === 'obsidian_vault'" class="section-empty" to="/sources">尚未添加 Obsidian Vault</RouterLink>
    </template>

    <RouterLink v-if="!props.sources.length" class="empty-link" to="/sources">去知识库添加资料文件夹</RouterLink>
  </nav>
</template>

<style scoped>
.scope-nav {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100%;
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
.scope-heading h2 { color: var(--ink-900, #10213d); font-size: 13px; font-weight: 800; }
.scope-heading a,
.empty-link { color: var(--color-primary); font-weight: 700; text-decoration: none; }
.scope-heading a { font-size: 12px; }

.scope-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 38px;
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

.source-label { padding: 16px 2px 6px; color: var(--text-muted); font-size: 11px; font-weight: 800; }
.source-label-count { color: var(--text-faint); font-weight: 700; }
.source-primary { display: flex; min-width: 0; align-items: center; gap: 7px; }
.type-icon { flex: 0 0 auto; color: var(--color-primary); opacity: .9; }
.source-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.section-empty { margin: 0; padding: 5px 10px 2px 26px; color: var(--text-faint); font-size: 11px; line-height: 1.45; text-decoration: none; }
.section-empty:hover { color: var(--color-primary); text-decoration: underline; }
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
