<script setup lang="ts">
import type { KnowledgeSource } from "../../api/knowledgeSources";

defineProps<{ sources: readonly KnowledgeSource[]; disabled: boolean }>();
const emit = defineEmits<{
  toggle: [source: KnowledgeSource, enabled: boolean];
  remove: [source: KnowledgeSource];
}>();

const typeLabels = {
  local_folder: "本地文件夹",
  obsidian_vault: "Obsidian Vault",
  temporary_import: "临时导入",
};
</script>

<template>
  <p v-if="sources.length === 0" class="empty-state">还没有知识源。添加目录后，系统只会访问你明确授权的路径。</p>
  <ul v-else class="source-list">
    <li v-for="source in sources" :key="source.id" class="source-card">
      <div class="source-heading">
        <div>
          <span class="type-label">{{ typeLabels[source.source_type] }}</span>
          <h3 class="source-name">{{ source.name }}</h3>
        </div>
        <span class="status" :class="`status-${source.sync_status}`">{{ source.sync_status === "idle" ? "可用" : "不可用" }}</span>
      </div>
      <p class="source-path">{{ source.root_path }}</p>
      <p v-if="source.error_message" class="error-message" role="alert">{{ source.error_message }}</p>
      <div class="source-actions">
        <button type="button" :disabled="disabled" @click="emit('toggle', source, !source.enabled)">
          {{ source.enabled ? "停用" : "启用" }}
        </button>
        <button class="remove-action" type="button" :disabled="disabled" @click="emit('remove', source)">移除记录</button>
      </div>
    </li>
  </ul>
</template>

<style scoped>
.source-list { display: grid; gap: 0.9rem; margin: 0; padding: 0; list-style: none; }
.source-card { border: 1px solid #dbe3e3; border-radius: 14px; padding: 1rem; background: #fff; }
.source-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.type-label { color: #5e7477; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.source-name { margin: 0.2rem 0 0; }
.source-path { overflow-wrap: anywhere; color: #4e6168; font-family: ui-monospace, monospace; font-size: 0.82rem; }
.status { border-radius: 99px; padding: 0.28rem 0.6rem; font-size: 0.75rem; font-weight: 800; }
.status-idle { background: #d9f0e9; color: #096052; }
.status-unavailable { background: #fee5de; color: #9a321e; }
.error-message { color: #9a321e; }
.source-actions { display: flex; gap: 0.6rem; }
.source-actions button { border: 1px solid #b8c8cb; border-radius: 8px; padding: 0.5rem 0.75rem; background: #f7faf9; cursor: pointer; }
.remove-action { color: #9a321e; }
.empty-state { margin: 0; padding: 2rem; border: 1px dashed #b8c8cb; border-radius: 14px; color: #607276; text-align: center; }
</style>
