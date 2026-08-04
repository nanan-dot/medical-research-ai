<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";
defineProps<{ items: DocumentRecord[]; loading: boolean; error: string; }>();
function formatTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const diff = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000 / 60));
  if (diff < 1) return "刚刚";
  if (diff < 60) return `${diff} 分钟前`;
  const hours = Math.floor(diff / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return date.toLocaleDateString();
}
function statusLabel(item: DocumentRecord): string {
  if (item.parse_status === "failed" || item.index_status === "failed") return "解析失败";
  if (item.parse_status === "parsing" || item.index_status === "indexing") return "处理中";
  if (item.parse_status === "pending" || item.index_status === "pending") return "排队中";
  return "已完成";
}
</script>
<template>
  <section class="recent-research" aria-label="最近研究">
    <div class="panel-head">
      <h2>最近研究</h2>
      <RouterLink to="/documents">全部 →</RouterLink>
    </div>
    <p v-if="loading" class="hint">正在读取真实状态…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <p v-else-if="!items.length" class="hint">暂无文档记录。登记知识源后，最近研究将出现在这里。</p>
    <ul v-else class="issue-list">
      <li v-for="item in items.slice(0, 6)" :key="item.id" class="issue">
        <span class="doc-icon" aria-hidden="true">▤</span>
        <span class="issue-copy"><b>{{ item.file_path }}</b><span class="issue-meta">{{ statusLabel(item) }} · {{ formatTime(item.modified_time) }}</span></span>
        <RouterLink :to="`/documents/${item.id}`" class="open" aria-label="打开文档">→</RouterLink>
      </li>
    </ul>
  </section>
</template>
<style scoped>
.recent-research{min-width:0}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.55rem}.panel-head h2{margin:0;font-size:1rem;color:var(--text-primary)}.panel-head a{color:var(--text-muted);font-size:.8rem;text-decoration:none}.panel-head a:hover{color:var(--color-primary)}.hint{padding:.85rem .95rem;color:var(--text-muted);font-size:.84rem;background:var(--surface);border:1px dashed var(--border-subtle);border-radius:10px}.hint.error{color:var(--color-danger)}.issue-list{display:grid;gap:2px;margin:0;padding:0;list-style:none}.issue{display:flex;align-items:center;gap:.65rem;min-width:0;padding:.55rem .6rem;border-radius:8px;transition:background-color .15s}.issue:hover{background:var(--surface)}.doc-icon{flex-shrink:0;display:grid;place-items:center;width:28px;height:28px;border-radius:7px;background:var(--surface-muted);color:var(--color-primary);font-size:.8rem}.issue-copy{display:grid;gap:.1rem;min-width:0}.issue-copy b{font-size:.85rem;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.issue-meta{color:var(--text-faint);font-size:.74rem}.open{flex-shrink:0;color:var(--text-faint);text-decoration:none;font-size:.85rem}.issue:hover .open{color:var(--color-primary)}
</style>
