<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  documents: readonly DocumentRecord[];
  disabled: boolean;
  selectedIds: readonly number[];
}>();

const emit = defineEmits<{
  retryParse: [document: DocumentRecord];
  retryIndex: [document: DocumentRecord];
  deleteIndex: [document: DocumentRecord];
  toggleSelect: [documentId: number, selected: boolean];
}>();

const statusLabels: Record<string, string> = {
  pending: "待处理", parsing: "解析中", indexing: "索引中", succeeded: "已完成",
  failed: "失败", outdated: "需更新",
};

function isSelected(documentId: number) {
  return props.selectedIds.includes(documentId);
}
</script>

<template>
  <p v-if="documents.length === 0" class="empty-state">当前筛选条件下没有文档。</p>
  <div v-else class="table-wrap">
    <table class="document-table">
      <thead>
        <tr><th>选择</th><th>文档</th><th>来源 / 类型</th><th>解析</th><th>索引</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="document in documents" :key="document.id">
          <td><input :aria-label="`选择文档 ${document.id}`" type="checkbox" :checked="isSelected(document.id)" :disabled="disabled" @change="emit('toggleSelect', document.id, ($event.target as HTMLInputElement).checked)" /></td>
          <td>
            <RouterLink class="file-name" :to="`/documents/${document.id}`">{{ document.original_filename ?? document.file_path }}</RouterLink>
            <span class="file-meta">{{ document.file_size }} bytes · 已重试 {{ document.retry_count }} 次</span>
            <span v-if="document.error_message" class="error-text" role="alert">{{ document.error_code }} · {{ document.error_message }}</span>
          </td>
          <td><span class="source-label">来源 #{{ document.knowledge_source_id }}</span><span class="file-meta">系统记录</span></td>
          <td><span class="status" :class="`status-${document.parse_status}`">{{ statusLabels[document.parse_status] }}</span></td>
          <td><span class="status" :class="`status-${document.index_status}`">{{ statusLabels[document.index_status] }}</span></td>
          <td class="actions">
            <button v-if="document.parse_status === 'failed'" :disabled="disabled" @click="emit('retryParse', document)">重试解析</button>
            <button v-if="document.index_status === 'failed' || document.index_status === 'outdated'" :disabled="disabled || document.parse_status !== 'succeeded'" @click="emit('retryIndex', document)">重试索引</button>
            <RouterLink class="detail-link" :to="`/documents/${document.id}`">详情</RouterLink>
            <button class="danger" :disabled="disabled || document.index_status === 'indexing'" @click="emit('deleteIndex', document)">删除索引</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow-x: auto; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--paper); }
.document-table { width: 100%; min-width: 800px; border-collapse: collapse; }
.document-table th, .document-table td { padding: .75rem; border-bottom: 1px solid var(--border-subtle); text-align: left; vertical-align: top; }
.document-table th { color: var(--text-muted); font-size: .72rem; letter-spacing: .08em; }
.file-name, .file-meta, .error-text { display: block; }
.file-name { max-width: 330px; overflow-wrap: anywhere; color: var(--color-primary); font-weight: 750; text-decoration: none; }
.file-name:hover, .detail-link:hover { text-decoration: underline; }
.file-meta, .source-label { margin-top: .25rem; color: var(--text-muted); font-size: .76rem; }
.error-text { max-width: 360px; margin-top: .45rem; color: var(--color-danger); font-size: .8rem; }
.status { display: inline-block; border-radius: 99px; padding: .25rem .55rem; background: var(--surface-muted); font-size: .75rem; font-weight: 800; white-space: nowrap; }
.status-succeeded { background: var(--color-success-soft); color: var(--color-success); }
.status-failed { background: var(--color-danger-soft); color: var(--color-danger); }
.status-parsing, .status-indexing { background: var(--color-primary-soft); color: var(--color-primary); }
.status-outdated { background: var(--color-warning-soft); color: var(--color-warning); }
.actions { display: flex; gap: .4rem; flex-wrap: wrap; }
.actions button, .detail-link { border: 1px solid var(--border-strong); border-radius: 7px; padding: .4rem .55rem; background: var(--paper); color: var(--text-primary); font: inherit; font-size: .78rem; text-decoration: none; white-space: nowrap; }
.actions .danger { color: var(--color-danger); }
.empty-state { padding: 2rem; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); text-align: center; color: var(--text-muted); }
</style>
