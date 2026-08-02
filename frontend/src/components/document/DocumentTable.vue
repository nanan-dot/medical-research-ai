<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

defineProps<{ documents: readonly DocumentRecord[]; disabled: boolean }>();
const emit = defineEmits<{
  retryParse: [document: DocumentRecord];
  retryIndex: [document: DocumentRecord];
  deleteIndex: [document: DocumentRecord];
}>();

const statusLabels: Record<string, string> = {
  pending: "等待",
  parsing: "解析中",
  indexing: "索引中",
  succeeded: "成功",
  failed: "失败",
  outdated: "已过期",
};
</script>

<template>
  <p v-if="documents.length === 0" class="empty-state">没有符合条件的文档。</p>
  <div v-else class="table-wrap">
    <table class="document-table">
      <thead>
        <tr><th>文档</th><th>解析</th><th>索引</th><th>重试</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="document in documents" :key="document.id">
          <td>
            <strong class="file-name">{{ document.file_path }}</strong>
            <span class="file-meta">{{ document.file_size }} bytes</span>
            <span v-if="document.error_message" class="error-text" role="alert">
              {{ document.error_code }} · {{ document.error_message }}
            </span>
          </td>
          <td><span class="status" :class="`status-${document.parse_status}`">{{ statusLabels[document.parse_status] }}</span></td>
          <td><span class="status" :class="`status-${document.index_status}`">{{ statusLabels[document.index_status] }}</span></td>
          <td>{{ document.retry_count }}</td>
          <td class="actions">
            <button v-if="document.parse_status === 'failed'" :disabled="disabled" @click="emit('retryParse', document)">重试解析</button>
            <button v-if="document.index_status === 'failed' || document.index_status === 'outdated'" :disabled="disabled || document.parse_status !== 'succeeded'" @click="emit('retryIndex', document)">重试索引</button>
            <button class="danger" :disabled="disabled || document.index_status === 'indexing'" @click="emit('deleteIndex', document)">删除索引</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow-x: auto; }
.document-table { width: 100%; border-collapse: collapse; background: #fff; }
.document-table th, .document-table td { padding: 0.85rem; border-bottom: 1px solid #e0e7e5; text-align: left; vertical-align: top; }
.document-table th { color: #617174; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; }
.file-name, .file-meta, .error-text { display: block; }
.file-name { max-width: 360px; overflow-wrap: anywhere; }
.file-meta { margin-top: 0.25rem; color: #718083; font-size: 0.76rem; }
.error-text { max-width: 420px; margin-top: 0.45rem; color: #9a321e; font-size: 0.8rem; }
.status { display: inline-block; border-radius: 99px; padding: 0.25rem 0.55rem; background: #edf1ef; font-size: 0.75rem; font-weight: 800; white-space: nowrap; }
.status-succeeded { background: #d9f0e9; color: #096052; }
.status-failed { background: #fee5de; color: #9a321e; }
.status-parsing, .status-indexing { background: #dceafb; color: #285d91; }
.status-outdated { background: #fff0ce; color: #805811; }
.actions { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.actions button { border: 1px solid #bdcbcc; border-radius: 7px; padding: 0.4rem 0.55rem; background: #f8faf9; white-space: nowrap; }
.actions .danger { color: #9a321e; }
.empty-state { padding: 2rem; border: 1px dashed #bdcbcc; border-radius: 12px; text-align: center; color: #68797c; }
</style>
