<script setup lang="ts">
import { computed, ref } from "vue";

import type { ResourceLibraryItem, ResourceSortBy, ResourceSortOrder } from "../../api/resourceLibrary";

const props = defineProps<{
  documents: readonly Readonly<ResourceLibraryItem>[];
  disabled: boolean;
  selectedIds: readonly number[];
  selectedDocumentId: number | null;
  emptyMessage?: string;
  sortBy?: ResourceSortBy;
  sortOrder?: ResourceSortOrder;
}>();

const emit = defineEmits<{
  repair: [document: Readonly<ResourceLibraryItem>];
  reprocess: [document: Readonly<ResourceLibraryItem>];
  toggleSelect: [documentId: number, selected: boolean];
  selectDocument: [document: Readonly<ResourceLibraryItem>];
  highlightDocument: [document: Readonly<ResourceLibraryItem>];
  sort: [sortBy: ResourceSortBy];
}>();

const selectedSet = computed(() => new Set(props.selectedIds));
const allCurrentPageSelected = computed(() => props.documents.length > 0 && props.documents.every((item) => selectedSet.value.has(item.id)));
const openMenuId = ref<number | null>(null);

interface StatusDisplay {
  label: string;
  reason: string;
  tone: "success" | "info" | "warning" | "muted";
  action: "view" | "progress" | "repair" | "reprocess" | "source";
}

function statusDisplay(document: Readonly<ResourceLibraryItem>): StatusDisplay {
  switch (document.status) {
    case "ai_available": return { label: "AI 可使用", reason: "解析和索引完成", tone: "success", action: "view" };
    case "needs_processing": return { label: "已解析", reason: "等待建立索引", tone: "info", action: "reprocess" };
    case "processing": return { label: document.progress == null ? "处理中" : `处理中 ${document.progress}%`, reason: document.phase || "正在处理", tone: "info", action: "progress" };
    case "outdated": return { label: "内容已更新", reason: "需要重新处理", tone: "warning", action: "reprocess" };
    case "metadata_only": return { label: "仅元数据", reason: "尚无可处理附件", tone: "muted", action: "source" };
    case "needs_attention": return { label: document.error_code === "unavailable_file" ? "异常" : "需处理", reason: issueReason(document.error_code), tone: "warning", action: "repair" };
    default: return { label: "状态待确认", reason: "后端未返回可用状态", tone: "muted", action: "view" };
  }
}

function issueReason(code: string | null): string {
  const reasons: Readonly<Record<string, string>> = {
    parse_failed: "解析失败",
    index_failed: "索引建立失败",
    unavailable_file: "文件不可访问",
    unsupported_format: "格式暂不支持",
  };
  return code ? reasons[code] ?? "需要处理" : "需要处理";
}

function fileType(document: Readonly<ResourceLibraryItem>): string {
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
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function toggleCurrentPage(selected: boolean): void {
  props.documents.forEach((document) => {
    if (selected !== selectedSet.value.has(document.id)) emit("toggleSelect", document.id, selected);
  });
}

function primaryAction(document: Readonly<ResourceLibraryItem>): void {
  const action = statusDisplay(document).action;
  if (action === "repair") emit("repair", document);
  else if (action === "reprocess") emit("reprocess", document);
  else emit("selectDocument", document);
}

function primaryLabel(document: Readonly<ResourceLibraryItem>): string {
  const action = statusDisplay(document).action;
  if (action === "repair") return "修复";
  if (action === "reprocess") return "重新处理";
  if (action === "progress") return "查看进度";
  if (action === "source") return "查看来源";
  return "查看";
}

function sort(sortBy: ResourceSortBy): void {
  emit("sort", sortBy);
}

function ariaSort(sortBy: ResourceSortBy): "ascending" | "descending" | "none" {
  if (props.sortBy !== sortBy) return "none";
  return props.sortOrder === "asc" ? "ascending" : "descending";
}

function closeMenu(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  openMenuId.value = null;
  const trigger = (event.currentTarget as HTMLElement).querySelector<HTMLButtonElement>(".more");
  trigger?.focus();
}
</script>

<template>
  <section class="document-list" aria-live="polite">
    <div v-if="props.disabled && !props.documents.length" class="loading-list" aria-label="正在加载资料"><div v-for="index in 5" :key="index" class="loading-row"><span></span><span></span><span></span></div></div>
    <p v-else-if="!props.documents.length" class="empty">{{ props.emptyMessage ?? "当前范围没有匹配资料。请调整关键词、来源或筛选条件。" }}</p>
    <table v-else class="document-table">
      <thead><tr><th scope="col"><input :checked="allCurrentPageSelected" :disabled="props.disabled" type="checkbox" aria-label="选择当前页全部资料" @change="toggleCurrentPage(($event.target as HTMLInputElement).checked)"></th><th scope="col" :aria-sort="ariaSort('name')"><button type="button" @click="sort('name')">资料信息</button></th><th scope="col" :aria-sort="ariaSort('status')"><button type="button" @click="sort('status')">状态</button></th><th scope="col" :aria-sort="ariaSort('updated_at')"><button type="button" @click="sort('updated_at')">更新时间</button></th><th scope="col">操作</th></tr></thead>
      <tbody><tr v-for="document in props.documents" :key="document.id" :class="{ selected: document.id === props.selectedDocumentId }" @click="emit('highlightDocument', document)">
        <td @click.stop><input :checked="selectedSet.has(document.id)" :disabled="props.disabled" type="checkbox" :aria-label="`选择资料 ${document.display_name}`" @change="emit('toggleSelect', document.id, ($event.target as HTMLInputElement).checked)"></td>
        <td><button type="button" class="document-main" @click.stop="emit('selectDocument', document)"><span class="file-icon" :class="`type-${fileType(document).toLowerCase()}`" aria-hidden="true">{{ fileType(document) }}</span><span class="copy"><strong :title="document.display_name">{{ document.display_name }}</strong><small :title="document.relative_path">{{ document.source_name }} · {{ fileType(document) }} · {{ bytes(document.file_size) }}</small><small v-if="document.snippet" class="snippet">{{ document.snippet }}</small></span></button></td>
        <td><div class="health" :class="`health-${statusDisplay(document).tone}`"><b>{{ statusDisplay(document).label }}</b><small>{{ statusDisplay(document).reason }}</small><template v-if="document.status === 'processing' && document.progress != null"><progress :value="document.progress" max="100">{{ document.progress }}%</progress><small>{{ document.progress }}%</small></template></div></td>
        <td><time :datetime="document.modified_time" :title="document.modified_time">{{ time(document.modified_time) }}</time></td>
        <td class="actions" @click.stop @keydown="closeMenu"><button :disabled="props.disabled" type="button" :aria-label="`${primaryLabel(document)} ${document.display_name}`" @click="primaryAction(document)">{{ primaryLabel(document) }}</button><button type="button" class="more" :aria-label="`更多操作 ${document.display_name}`" :aria-expanded="openMenuId === document.id" @click="openMenuId = openMenuId === document.id ? null : document.id">⋯</button><div v-if="openMenuId === document.id" class="more-menu" role="menu" @keydown="closeMenu"><button role="menuitem" type="button" @click="emit('selectDocument', document); openMenuId = null">查看详情</button><button v-if="document.status !== 'ai_available'" role="menuitem" type="button" @click="emit('reprocess', document); openMenuId = null">重新处理</button><button role="menuitem" type="button" disabled title="删除资料需要后端提供安全语义">删除暂不可用</button></div></td>
      </tr></tbody>
    </table>
  </section>
</template>

<style scoped>
.document-list { min-height:320px; overflow-x:auto; }.document-table { width:100%; border-collapse:collapse; table-layout:fixed; }.document-table th { height:42px; padding:0 14px; border-bottom:1px solid var(--border-subtle); background:var(--elevated, #fbfcfe); color:var(--text-muted); font-size:12px; font-weight:700; text-align:left; }.document-table th button { padding:0; border:0; background:transparent; color:inherit; font:inherit; cursor:pointer; }.document-table th:first-child,.document-table td:first-child { width:44px; }.document-table th:nth-child(2) { width:44%; }.document-table th:nth-child(3) { width:24%; }.document-table th:nth-child(4) { width:150px; }.document-table th:last-child { width:150px; }.document-table td { height:72px; padding:8px 14px; border-bottom:1px solid var(--border-subtle); vertical-align:middle; }.document-table tbody tr:hover,.document-table tbody tr.selected { background:var(--color-primary-soft); }.document-table input { width:16px; height:16px; accent-color:var(--color-primary); }.document-main { display:flex; align-items:center; gap:10px; min-width:0; border:0; padding:0; background:transparent; color:inherit; text-align:left; cursor:pointer; }.file-icon { display:grid; flex:0 0 auto; width:28px; height:34px; place-items:center; border-radius:4px; background:var(--color-primary-soft); color:var(--color-primary); font-size:8px; font-weight:850; }.type-pdf { background:var(--color-danger-soft); color:var(--color-danger); }.type-pptx { background:var(--color-warning-soft); color:var(--color-warning); }.copy { display:grid; min-width:0; gap:3px; }.copy strong,.copy small,.health small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.copy strong { color:var(--text-primary); font-size:13px; font-weight:700; }.copy small,.health small,time { color:var(--text-muted); font-size:12px; }.snippet { white-space:normal !important; }.health { display:grid; min-width:0; gap:3px; }.health b { color:var(--text-primary); font-size:12px; }.health b::before { margin-right:5px; content:"●"; font-size:9px; }.health-success b::before { color:var(--color-success); }.health-info b::before { color:var(--color-primary); }.health-warning b::before { color:var(--color-warning); }.health-muted b::before { color:var(--text-faint); }progress { width:96px; height:5px; accent-color:var(--color-primary); }time { font-variant-numeric:tabular-nums; }.actions { position:relative; white-space:nowrap; }.actions > button { border:0; padding:4px 0; background:transparent; color:var(--color-primary); font:inherit; font-size:12px; font-weight:700; cursor:pointer; }.actions .more { width:28px; margin-left:8px; border:1px solid var(--border-subtle); border-radius:4px; }.more-menu { position:absolute; z-index:20; right:12px; top:32px; display:grid; min-width:132px; padding:4px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); box-shadow:var(--shadow-md, 0 8px 24px rgb(15 23 42 / 8%)); }.more-menu button { min-height:30px; border:0; border-radius:3px; background:transparent; color:var(--text-primary); font:inherit; font-size:12px; text-align:left; cursor:pointer; }.more-menu button:hover,.more-menu button:focus-visible { background:var(--color-primary-soft); outline:2px solid var(--color-primary); }.more-menu button:disabled { color:var(--text-faint); cursor:not-allowed; }.empty { padding:68px 20px; color:var(--text-muted); font-size:13px; text-align:center; }.loading-list { padding:0 14px; }.loading-row { display:grid; grid-template-columns:1.9fr 1.2fr 90px; gap:20px; min-height:66px; align-items:center; border-bottom:1px solid var(--border-subtle); }.loading-row span { height:12px; border-radius:4px; background:linear-gradient(90deg,#edf1f6 25%,#f7f9fc 45%,#edf1f6 65%); background-size:200% 100%; animation:shimmer 1.2s infinite; }@keyframes shimmer { to { background-position:-200% 0; }}@media(max-width:767px){.document-list{overflow:visible}.document-table,.document-table tbody,.document-table tr,.document-table td{display:block;width:100%}.document-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}.document-table tr{position:relative;min-height:150px;padding:12px 12px 12px 44px;border-bottom:1px solid var(--border-subtle)}.document-table td{height:auto;padding:0;border:0}.document-table td:first-child{position:absolute;top:16px;left:14px}.document-table td:nth-child(3){margin-top:9px}.document-table td:nth-child(4){display:none}.actions{position:absolute;top:16px;right:14px;width:auto!important;display:flex;align-items:center}.copy strong,.copy small,.health small{white-space:normal}.more-menu{right:0;top:30px}}@media(prefers-reduced-motion:reduce){.loading-row span{animation:none}}
.document-list { min-width:0; min-height:0; }
</style>
