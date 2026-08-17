<script setup lang="ts">
import { computed } from "vue";

import type { DocumentRecord, IndexStatus, ParseStatus } from "../../api/documents";

const props = defineProps<{
  documents: readonly DocumentRecord[];
  disabled: boolean;
  selectedIds: readonly number[];
  selectedDocumentId: number | null;
  sourceNames: Readonly<Record<number, string>>;
}>();

const emit = defineEmits<{
  retryParse: [document: DocumentRecord];
  retryIndex: [document: DocumentRecord];
  deleteIndex: [document: DocumentRecord];
  toggleSelect: [documentId: number, selected: boolean];
  selectDocument: [document: DocumentRecord];
}>();

const selectedSet = computed(() => new Set(props.selectedIds));

const parseLabels: Record<ParseStatus, string> = {
  pending: "等待解析",
  parsing: "解析中",
  succeeded: "解析成功",
  failed: "解析失败",
};

const indexLabels: Record<IndexStatus, string> = {
  pending: "等待索引",
  indexing: "建立索引中",
  succeeded: "已索引",
  failed: "索引失败",
  outdated: "索引过期",
};

function isSelected(id: number): boolean {
  return selectedSet.value.has(id);
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date);
}

function documentName(document: DocumentRecord): string {
  return document.original_filename ?? document.file_path;
}

function fileType(document: DocumentRecord): string {
  const filename = documentName(document);
  const extension = filename.split(".").pop()?.trim().toUpperCase();
  return extension && extension.length <= 5 ? extension : "文件";
}
</script>

<template>
  <p v-if="!props.documents.length" class="empty">当前范围没有文档。</p>
  <div v-else class="table-wrap">
    <table>
      <thead>
        <tr>
          <th><span class="visually-hidden">选择</span></th>
          <th>文档</th>
          <th>解析</th>
          <th>索引</th>
          <th>更新时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="document in props.documents"
          :key="document.id"
          :class="{ selected: document.id === props.selectedDocumentId }"
          tabindex="0"
          @click="emit('selectDocument', document)"
          @keydown.enter.prevent="emit('selectDocument', document)"
          @keydown.space.prevent="emit('selectDocument', document)"
        >
          <td>
            <input
              :checked="isSelected(document.id)"
              :disabled="props.disabled"
              type="checkbox"
              :aria-label="`选择文档 ${document.id}`"
              @click.stop
              @change="emit('toggleSelect', document.id, ($event.target as HTMLInputElement).checked)"
            >
          </td>
          <td>
            <div class="file">
              <span class="file-icon" :class="`file-icon--${fileType(document).toLowerCase()}`">{{ fileType(document) }}</span>
              <span class="file-copy">
                <RouterLink :to="`/documents/${document.id}`" @click.stop>{{ documentName(document) }}</RouterLink>
                <small>{{ props.sourceNames[document.knowledge_source_id] ?? `来源 #${document.knowledge_source_id}` }} / {{ document.file_path }}</small>
              </span>
            </div>
          </td>
          <td><span class="status" :class="`status-${document.parse_status}`">{{ parseLabels[document.parse_status] }}</span></td>
          <td><span class="status" :class="`status-${document.index_status}`">{{ indexLabels[document.index_status] }}</span></td>
          <td class="timestamp">{{ formatTime(document.modified_time) }}</td>
          <td class="actions" @click.stop>
            <button
              v-if="document.parse_status === 'failed' || document.parse_status === 'pending'"
              :disabled="props.disabled"
              type="button"
              @click="emit('retryParse', document)"
            >
              {{ document.parse_status === "pending" ? "开始解析" : "重试解析" }}
            </button>
            <button
              v-if="document.index_status === 'failed' || document.index_status === 'outdated'"
              :disabled="props.disabled || document.parse_status !== 'succeeded'"
              type="button"
              @click="emit('retryIndex', document)"
            >
              重试索引
            </button>
            <button
              v-if="document.index_status === 'succeeded'"
              :disabled="props.disabled"
              type="button"
              @click="emit('deleteIndex', document)"
            >
              删除索引
            </button>
            <RouterLink :to="`/documents/${document.id}`">详情</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow: auto;
}

.table-wrap table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
}

.table-wrap th,
.table-wrap td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
  vertical-align: middle;
  font-size: 0.75rem;
}

.table-wrap th {
  color: var(--text-muted);
  font-weight: 600;
}

.table-wrap tbody tr {
  cursor: pointer;
}

.table-wrap tbody tr:hover,
.table-wrap tbody tr:focus-visible {
  outline: 0;
  background: var(--surface-muted);
}

.table-wrap tbody tr.selected {
  box-shadow: inset 3px 0 var(--color-primary);
  background: var(--color-primary-soft);
}

.file {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 230px;
}

.file-icon {
  display: grid;
  flex: 0 0 auto;
  width: 26px;
  height: 28px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.55rem;
  font-weight: 800;
}

.file-icon--pdf {
  border-color: color-mix(in srgb, var(--color-danger) 18%, transparent);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.file-copy {
  min-width: 0;
}

.file a {
  display: block;
  overflow: hidden;
  color: var(--ink-900, #10213d);
  font-weight: 700;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file small {
  display: block;
  max-width: 290px;
  overflow: hidden;
  margin-top: 3px;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.66rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
  font-size: 0.72rem;
  white-space: nowrap;
}

.status::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: "";
}

.status-succeeded { color: var(--color-success); }
.status-failed { color: var(--color-danger); }
.status-parsing,
.status-indexing { color: var(--color-primary); }
.status-outdated { color: var(--color-warning); }

.timestamp {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.actions {
  white-space: nowrap;
}

.actions button,
.actions a {
  margin-right: 6px;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: 0.7rem;
  font-weight: 700;
  text-decoration: none;
}

.empty {
  padding: 32px 12px;
  color: var(--text-muted);
  text-align: center;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
