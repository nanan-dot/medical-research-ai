<script setup lang="ts">
import { computed } from "vue";

import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{
  sources: readonly KnowledgeSource[];
  disabled: boolean;
  pendingRemovalId: number | null;
}>();

const emit = defineEmits<{
  toggle: [source: KnowledgeSource, enabled: boolean];
  remove: [source: KnowledgeSource];
  sync: [source: KnowledgeSource];
  viewDocuments: [source: KnowledgeSource];
}>();

const typeLabels = {
  local_folder: "本地文件夹",
  obsidian_vault: "Obsidian Vault",
  temporary_import: "临时导入",
} as const;
const statusLabels = {
  idle: "等待同步",
  scanning: "同步中",
  completed: "已同步",
  completed_with_errors: "同步含错误",
  unavailable: "不可用",
} as const;
const hasNoSources = computed(() => props.sources.length === 0);

function formatTime(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : "尚未同步";
}

function isProblemSource(source: KnowledgeSource): boolean {
  return source.sync_status === "completed_with_errors" || source.sync_status === "unavailable";
}

function getErrorSummary(source: KnowledgeSource): string {
  return source.error_message ?? "同步存在问题，请查看详情";
}
</script>

<template>
  <section
    v-if="hasNoSources"
    class="empty-state"
    aria-labelledby="empty-sources-title"
  >
    <h3 id="empty-sources-title">当前没有知识来源</h3>
    <p>添加第一个资料文件夹开始管理文档和索引状态。</p>
  </section>
  <ul
    v-else
    class="source-list"
  >
    <li
      v-for="source in sources"
      :key="source.id"
      class="source-row"
    >
      <div class="source-main">
        <span
          class="source-icon"
          aria-hidden="true"
        >▣</span>
        <div>
          <h3>{{ source.name }}</h3>
          <p class="source-path">{{ source.root_path }}</p>
          <span class="type-pill">{{ typeLabels[source.source_type] }}</span>
        </div>
      </div>
      <div class="statistics">
        <span><b>{{ source.stats.total_files }}</b> 个文件</span>
        <span><b>{{ source.stats.indexed }}</b> 已索引</span>
        <span><b>{{ source.stats.pending }}</b> 待处理</span>
        <span :class="{ failed: source.stats.failed > 0 }"><b>{{ source.stats.failed }}</b> 异常</span>
      </div>
      <div class="source-status">
        <span>上次同步：{{ formatTime(source.last_sync_time) }}</span>
        <strong :class="`status-${source.sync_status}`">● {{ statusLabels[source.sync_status] }}</strong>
        <em
          v-if="isProblemSource(source)"
          role="alert"
        >{{ getErrorSummary(source) }}</em>
      </div>
      <div class="source-actions">
        <button
          type="button"
          :disabled="disabled || source.sync_status === 'scanning' || !source.enabled"
          @click="emit('sync', source)"
        >
          {{ source.sync_status === "scanning" ? "同步中" : "同步" }}
        </button>
        <label class="switch">
          <input
            type="checkbox"
            :checked="source.enabled"
            :disabled="disabled"
            :aria-label="`${source.enabled ? '停用' : '启用'} ${source.name}`"
            @change="emit('toggle', source, ($event.target as HTMLInputElement).checked)"
          >
          <span aria-hidden="true" />
        </label>
        <button
          class="document-link"
          type="button"
          @click="emit('viewDocuments', source)"
        >
          查看文档 →
        </button>
        <button
          class="remove-action"
          type="button"
          :disabled="disabled"
          :aria-label="pendingRemovalId === source.id ? `确认移除 ${source.name}` : `移除 ${source.name}`"
          @click="emit('remove', source)"
        >
          {{ pendingRemovalId === source.id ? "确认移除？" : "移除" }}
        </button>
      </div>
    </li>
  </ul>
</template>

<style scoped>
.source-list { margin: 0 -26px; padding: 0; list-style: none; border-top: 1px solid var(--border-subtle); }
.source-row { display: grid; grid-template-columns: minmax(250px, 1.25fr) minmax(255px, 1fr) minmax(155px, 0.7fr) auto; gap: 18px; align-items: center; padding: 18px 26px; }
.source-row + .source-row { border-top: 1px solid var(--border-subtle); }
.source-row:hover { background: var(--surface-muted); }
.source-main { display: flex; gap: 12px; }
.source-icon { display: grid; flex: 0 0 36px; width: 36px; height: 36px; place-items: center; border-radius: 9px; background: var(--color-primary-soft); color: var(--color-primary); }
.source-main h3 { margin: 0; color: var(--ink-900); font-size: 0.94rem; }
.source-path { margin: 2px 0; color: var(--text-muted); font-family: ui-monospace, Consolas, monospace; font-size: 0.75rem; overflow-wrap: anywhere; }
.type-pill { display: inline-block; padding: 2px 7px; border-radius: 5px; background: var(--surface-muted); color: var(--text-muted); font-size: 0.68rem; }
.statistics { display: flex; flex-wrap: wrap; gap: 12px; color: var(--text-muted); font-size: 0.76rem; }
.statistics b { color: var(--ink-900); }
.statistics .failed, .statistics .failed b { color: var(--color-danger); }
.source-status { display: grid; gap: 3px; color: var(--text-muted); font-size: 0.72rem; }
.source-status strong { font-size: 0.72rem; }
.status-idle, .status-completed { color: var(--color-success); }
.status-scanning { color: var(--color-primary); }
.status-completed_with_errors, .status-unavailable, .source-status em { color: var(--color-danger); }
.source-status em { font-style: normal; }
.source-actions { display: flex; align-items: center; gap: 10px; }
.source-actions button { border: 1px solid var(--border-subtle); border-radius: 7px; padding: 6px 9px; background: var(--surface); color: var(--color-primary); font: inherit; font-size: 0.76rem; font-weight: 700; }
.source-actions button:disabled { opacity: 0.55; }
.document-link { border: 0 !important; padding: 6px 0 !important; }
.remove-action { color: var(--text-muted) !important; }
.switch input { position: absolute; opacity: 0; }
.switch span { display: block; position: relative; width: 36px; height: 20px; border-radius: 999px; background: var(--border-strong); }
.switch span::after { position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--surface); box-shadow: var(--shadow-card); content: ""; }
.switch input:checked + span { background: var(--color-primary); }
.switch input:checked + span::after { transform: translateX(16px); }
.empty-state { margin: 0; padding: 32px 16px; border: 1px dashed var(--border-strong); border-radius: 8px; color: var(--text-muted); text-align: center; }
.empty-state h3 { margin: 0 0 8px; color: var(--text-primary); font-size: 1rem; }
.empty-state p { margin: 0; }
@media (max-width: 1050px) { .source-row { grid-template-columns: 1fr 1fr; } .source-actions { justify-content: flex-end; } }
@media (max-width: 650px) { .source-row { grid-template-columns: 1fr; } .source-actions { justify-content: flex-start; } }
</style>
