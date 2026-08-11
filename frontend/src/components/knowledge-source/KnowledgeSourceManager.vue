<script setup lang="ts">
import { onMounted } from "vue";
import type { KnowledgeSource } from "../../api/knowledgeSources";

import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";
import KnowledgeSourceList from "./KnowledgeSourceList.vue";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";

const { sources, loading, error, enabledCount, load, create, setEnabled, remove, sync } =
  useKnowledgeSources();

onMounted(load);

function confirmRemove(source: KnowledgeSource): void {
  if (window.confirm(`确认移除“${source.name}”吗？仅移除系统记录，不会删除原始目录中的文件。`)) remove(source);
}
</script>

<template>
  <section class="manager" aria-labelledby="manager-title">
    <header class="manager-header">
      <div><h2 id="manager-title">知识来源</h2><p class="summary">{{ loading ? "正在读取知识来源" : `${sources.length} 个来源 · ${enabledCount} 个已启用` }}</p></div>
    </header>
    <KnowledgeSourceForm :disabled="loading" @submit="create" />
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <KnowledgeSourceList
      :sources="sources"
      :disabled="loading"
      @toggle="setEnabled"
      @remove="confirmRemove"
      @sync="sync"
    />
  </section>
</template>

<style scoped>
.manager { display:grid; gap:1.1rem; padding:1.5rem; border:1px solid var(--border-subtle); border-radius:12px; background:var(--surface-raised); }
.manager-header h2 { margin:0; color:#10213d; font-size:1.35rem; }.summary { margin:.25rem 0 0; color:var(--text-muted); }.request-error { margin:0; padding:.8rem; border:1px solid #fecaca; border-radius:8px; background:var(--color-danger-soft); color:var(--color-danger); }
</style>
