<script setup lang="ts">
import { computed } from "vue";

import type { DocumentHealthStatus, DocumentRecord } from "../../api/documents";

const props = defineProps<{
  documents: readonly DocumentRecord[];
  disabled: boolean;
  selectedIds: readonly number[];
  selectedDocumentId: number | null;
  sourceNames: Readonly<Record<number, string>>;
  emptyMessage?: string;
}>();

const emit = defineEmits<{
  repair: [document: DocumentRecord];
  retryParse: [document: DocumentRecord];
  retryIndex: [document: DocumentRecord];
  toggleSelect: [documentId: number, selected: boolean];
  selectDocument: [document: DocumentRecord];
}>();

const selectedSet = computed(() => new Set(props.selectedIds));
const allCurrentPageSelected = computed(() => props.documents.length > 0 && props.documents.every((item) => selectedSet.value.has(item.id)));

type DisplayHealth = DocumentHealthStatus | "unknown";

function health(document: DocumentRecord): DisplayHealth {
  return document.health_status ?? "unknown";
}

function healthLabel(document: DocumentRecord): string {
  const state = health(document);
  if (state === "available") return "可用于问答";
  if (state === "processing") return "处理中";
  if (state === "needs_attention") return "需处理";
  return "状态待确认";
}

function healthReason(document: DocumentRecord): string {
  if (document.health_reason) return document.health_reason;
  if (document.error_message) return document.error_message;
  return document.health_status ? "后端未返回状态原因" : "后端未返回健康状态";
}

function name(document: DocumentRecord): string {
  return document.original_filename ?? document.file_path;
}

function type(document: DocumentRecord): string {
  return document.file_type?.toUpperCase() ?? document.extension?.replace(".", "").toUpperCase() ?? "文件";
}

function bytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function time(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}

function canRepair(document: DocumentRecord): boolean {
  return document.available_actions?.includes("repair") ?? false;
}

function toggleCurrentPage(selected: boolean): void {
  props.documents.forEach((document) => {
    if (selected !== selectedSet.value.has(document.id)) emit("toggleSelect", document.id, selected);
  });
}
</script>

<template>
  <section class="document-list" aria-live="polite">
    <div v-if="props.disabled && !props.documents.length" class="loading-list" aria-label="正在加载文档"><div v-for="index in 5" :key="index" class="loading-row"><span></span><span></span><span></span></div></div>
    <p v-else-if="!props.documents.length" class="empty">{{ props.emptyMessage ?? "当前范围没有匹配文档。请调整关键词、来源或筛选条件。" }}</p>
    <table v-else class="document-table">
      <thead><tr><th scope="col"><input :checked="allCurrentPageSelected" :disabled="props.disabled" type="checkbox" aria-label="选择当前页全部文档" @change="toggleCurrentPage(($event.target as HTMLInputElement).checked)"></th><th scope="col">文档信息</th><th scope="col">处理状态</th><th scope="col">更新时间</th><th scope="col">操作</th></tr></thead>
      <tbody><tr v-for="document in props.documents" :key="document.id" :class="{ selected: document.id === props.selectedDocumentId }">
        <td><input :checked="selectedSet.has(document.id)" :disabled="props.disabled" type="checkbox" :aria-label="`选择文档 ${name(document)}`" @change="emit('toggleSelect', document.id, ($event.target as HTMLInputElement).checked)"></td>
        <td><button type="button" class="document-main" @click="emit('selectDocument', document)"><span class="file-icon" :class="`type-${type(document).toLowerCase()}`" aria-hidden="true">{{ type(document) }}</span><span class="copy"><strong :title="name(document)">{{ name(document) }}</strong><small :title="document.file_path">{{ props.sourceNames[document.knowledge_source_id] ?? `来源 #${document.knowledge_source_id}` }} · {{ type(document) }} · {{ bytes(document.file_size) }}</small></span></button></td>
        <td><div class="health" :class="`health-${health(document)}`"><b>{{ healthLabel(document) }}</b><small>{{ healthReason(document) }}</small><template v-if="health(document) === 'processing' && document.progress != null"><span class="progress" role="progressbar" :aria-valuenow="document.progress" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: `${document.progress}%` }"></i></span><small>{{ document.progress }}%</small></template></div></td>
        <td><time :datetime="document.modified_time" :title="document.modified_time">{{ time(document.modified_time) }}</time></td>
        <td class="actions"><button v-if="canRepair(document)" :disabled="props.disabled" type="button" @click="emit('repair', document)">修复</button><button v-else-if="health(document) === 'available'" type="button" @click="emit('selectDocument', document)">查看文档</button><span v-else>—</span></td>
      </tr></tbody>
    </table>
  </section>
</template>

<style scoped>
.document-list { min-height: 320px; overflow-x: auto; }.document-table { width: 100%; border-collapse: collapse; table-layout: fixed; }.document-table th { height: 42px; padding: 0 14px; border-bottom: 1px solid var(--border-subtle); background: var(--surface-muted); color: var(--text-muted); font-size: .72rem; font-weight: 700; text-align: left; }.document-table th:first-child,.document-table td:first-child { width: 40px; }.document-table th:nth-child(2) { width: 40%; }.document-table th:nth-child(3) { width: 22%; }.document-table th:nth-child(4) { width: 16%; }.document-table th:last-child { width: auto; }.document-table td { height: 76px; padding: 8px 14px; border-bottom: 1px solid var(--border-subtle); vertical-align: middle; }.document-table tbody tr:hover,.document-table tbody tr.selected { background: var(--accent-soft, #eaf2ff); }.document-table input { width: 16px; height: 16px; accent-color: var(--color-primary); }
.document-main { display: flex; align-items: center; gap: 10px; min-width: 0; border: 0; padding: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; }.file-icon { display: grid; flex: 0 0 auto; width: 28px; height: 34px; place-items: center; border-radius: 6px; background: var(--color-primary-soft); color: var(--color-primary); font-size: .55rem; font-weight: 900; }.type-pdf { background: var(--color-danger-soft); color: var(--color-danger); }.copy { display: grid; min-width: 0; gap: 4px; }.copy strong, .copy small, .health small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.copy strong { color: var(--text-primary); font-size: .8rem; font-weight: 750; }.copy small, .health small, time { color: var(--text-muted); font-size: .7rem; }.health { display: grid; min-width: 0; gap: 3px; }.health b { color: var(--text-primary); font-size: .72rem; }.health b::before { margin-right: 5px; content: "●"; font-size: .62rem; }.health-available b::before { color: var(--color-success); }.health-processing b::before { color: var(--color-primary); }.health-needs_attention b::before { color: var(--color-warning); }.health-unknown b::before { color: var(--text-faint); }time { font-variant-numeric: tabular-nums; }.actions { text-align: left; }.actions button { border: 0; padding: 4px 0; background: transparent; color: var(--color-primary); font: inherit; font-size: .72rem; font-weight: 800; cursor: pointer; }.actions span { color: var(--text-faint); font-size: .72rem; }
.progress { display: block; width: 80px; height: 4px; overflow: hidden; border-radius: 2px; background: var(--border-subtle); }.progress i { display: block; height: 100%; background: var(--color-primary); }.empty { padding: 68px 20px; color: var(--text-muted); font-size: .8rem; text-align: center; }.loading-list { padding: 0 14px; }.loading-row { display: grid; grid-template-columns: 1.9fr 1.2fr 90px; gap: 20px; min-height: 66px; align-items: center; border-bottom: 1px solid var(--border-subtle); }.loading-row span { height: 12px; border-radius: 4px; background: linear-gradient(90deg, #edf1f6 25%, #f7f9fc 45%, #edf1f6 65%); background-size: 200% 100%; animation: shimmer 1.2s infinite; }@keyframes shimmer { to { background-position: -200% 0; } }
@media (max-width: 760px) { .document-list { overflow: visible; }.document-table,.document-table tbody,.document-table tr,.document-table td { display: block; width: 100%; }.document-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }.document-table tr { position: relative; min-height: 146px; padding: 12px 12px 12px 44px; border-bottom: 1px solid var(--border-subtle); }.document-table td { height: auto; padding: 0; border: 0; }.document-table td:first-child { position: absolute; top: 16px; left: 14px; }.document-table td:nth-child(3) { margin-top: 9px; }.document-table td:nth-child(4) { display: none; }.actions { position: absolute; top: 16px; right: 14px; }.copy strong { white-space: normal; }.copy small,.health small { white-space: normal; } }
</style>
