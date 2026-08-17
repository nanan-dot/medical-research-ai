<script setup lang="ts">
import type { DocumentRecord, IndexStatus, ParseStatus } from "../../api/documents";

const props = defineProps<{
  document: DocumentRecord | null;
  sourceName: string | null;
  scopeName: string;
  total: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  retryParse: [document: DocumentRecord];
  retryIndex: [document: DocumentRecord];
}>();

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

function documentName(document: DocumentRecord): string {
  return document.original_filename ?? document.file_path;
}

function fileType(document: DocumentRecord): string {
  const extension = documentName(document).split(".").pop()?.trim().toUpperCase();
  return extension && extension.length <= 5 ? extension : "文件";
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
</script>

<template>
  <section class="inspector" aria-label="文档详情">
    <template v-if="props.document">
      <p class="eyebrow">文档详情</p>
      <div class="document-heading">
        <span class="file-icon">{{ fileType(props.document) }}</span>
        <h2>{{ documentName(props.document) }}</h2>
      </div>
      <p class="path">{{ props.sourceName ?? `来源 #${props.document.knowledge_source_id}` }} / {{ props.document.file_path }}</p>

      <dl>
        <div><dt>文件类型</dt><dd>{{ props.document.media_type || "—" }}</dd></div>
        <div><dt>文件大小</dt><dd>{{ formatBytes(props.document.file_size) }}</dd></div>
        <div><dt>更新时间</dt><dd>{{ formatTime(props.document.modified_time) }}</dd></div>
        <div><dt>解析状态</dt><dd :class="`status-${props.document.parse_status}`">{{ parseLabels[props.document.parse_status] }}</dd></div>
        <div><dt>索引状态</dt><dd :class="`status-${props.document.index_status}`">{{ indexLabels[props.document.index_status] }}</dd></div>
      </dl>

      <div v-if="props.document.error_message" class="error-context" role="alert">
        <p>错误原因</p>
        <span>{{ props.document.error_message }}</span>
      </div>
      <p v-else-if="props.document.parse_status === 'succeeded' && props.document.index_status === 'succeeded'" class="normal-context">处理状态正常，未返回错误信息。</p>

      <div class="inspector-actions">
        <button
          v-if="props.document.parse_status === 'failed' || props.document.parse_status === 'pending'"
          :disabled="props.disabled"
          type="button"
          @click="emit('retryParse', props.document)"
        >
          {{ props.document.parse_status === "pending" ? "开始解析" : "重试解析" }}
        </button>
        <button
          v-if="props.document.index_status === 'failed' || props.document.index_status === 'outdated'"
          :disabled="props.disabled || props.document.parse_status !== 'succeeded'"
          type="button"
          @click="emit('retryIndex', props.document)"
        >
          重试索引
        </button>
        <RouterLink class="detail-link" :to="`/documents/${props.document.id}`">打开文档详情</RouterLink>
      </div>
    </template>

    <template v-else>
      <p class="eyebrow">文档详情</p>
      <h2>{{ props.scopeName }}</h2>
      <p class="empty-copy">选择一篇文档，查看其真实来源、处理状态和错误原因。</p>
      <dl>
        <div><dt>当前范围文件</dt><dd>{{ props.total }} 篇</dd></div>
      </dl>
    </template>
  </section>
</template>

<style scoped>
.inspector {
  min-width: 0;
  padding: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.document-heading {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.file-icon {
  display: grid;
  flex: 0 0 auto;
  width: 28px;
  height: 30px;
  place-items: center;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.57rem;
  font-weight: 800;
}

.inspector h2 {
  margin: 0;
  color: var(--ink-900, #10213d);
  font-size: 0.95rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.path,
.empty-copy {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 0.75rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.path {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}

.inspector dl {
  margin: 14px 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.inspector dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  font-size: 0.75rem;
}

.inspector dt {
  flex: 0 0 auto;
  color: var(--text-muted);
}

.inspector dd {
  margin: 0;
  color: var(--ink-900, #10213d);
  text-align: right;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.status-succeeded { color: var(--color-success) !important; }
.status-failed { color: var(--color-danger) !important; }
.status-parsing,
.status-indexing { color: var(--color-primary) !important; }
.status-outdated { color: var(--color-warning) !important; }

.error-context,
.normal-context {
  margin: 14px 0;
  padding: 10px;
  font-size: 0.75rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.error-context {
  display: grid;
  gap: 4px;
  border-left: 2px solid var(--color-danger);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.error-context p {
  margin: 0;
  font-weight: 700;
}

.normal-context {
  border-left: 2px solid var(--color-success);
  background: var(--color-success-soft, #effaf4);
  color: var(--color-success);
}

.inspector-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.inspector-actions button,
.detail-link {
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
}
</style>
