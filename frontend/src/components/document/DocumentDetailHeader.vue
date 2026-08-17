<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  document: DocumentRecord;
  showResearchReturn: boolean;
}>();

const emit = defineEmits<{
  returnToResearch: [];
}>();

function parseStatusLabel(status: DocumentRecord["parse_status"]): string {
  return { pending: "等待解析", parsing: "正在解析", succeeded: "解析完成", failed: "解析失败" }[status];
}

function indexStatusLabel(status: DocumentRecord["index_status"]): string {
  return { pending: "等待索引", indexing: "正在索引", succeeded: "索引完成", failed: "索引失败", outdated: "索引已过期" }[status];
}
</script>

<template>
  <header class="detail-header">
    <nav class="breadcrumb" aria-label="文档导航">
      <RouterLink to="/documents">返回文档库</RouterLink>
      <span aria-hidden="true">/</span>
      <span aria-current="page">文档详情</span>
    </nav>
    <div class="header-main">
      <div class="title-group">
        <h1 class="document-title">{{ props.document.original_filename ?? props.document.file_path }}</h1>
        <button v-if="props.showResearchReturn" class="research-return" type="button" @click="emit('returnToResearch')">
          返回论文研究
        </button>
      </div>
      <p class="status-summary" role="status">
        <span>{{ parseStatusLabel(props.document.parse_status) }}</span>
        <span>{{ indexStatusLabel(props.document.index_status) }}</span>
      </p>
    </div>
  </header>
</template>

<style scoped>
.detail-header { display: grid; gap: .7rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-subtle); }
.breadcrumb { display: flex; gap: .45rem; color: var(--text-muted); font-size: .82rem; }
.breadcrumb a { color: var(--color-primary); font-weight: 700; text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.header-main { display: flex; align-items: start; justify-content: space-between; gap: 1rem; }
.title-group { min-width: 0; }
.document-title { margin: 0; color: var(--text-primary); font-size: clamp(1.35rem, 2vw, 1.8rem); line-height: 1.3; overflow-wrap: anywhere; }
.research-return { margin-top: .45rem; border: 0; padding: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: .84rem; font-weight: 700; cursor: pointer; }
.status-summary { display: flex; flex-wrap: wrap; justify-content: end; gap: .45rem; min-width: 220px; margin: .25rem 0 0; color: var(--text-muted); font-size: .78rem; }
.status-summary span { padding: .28rem .5rem; border: 1px solid var(--border-subtle); border-radius: 999px; background: var(--surface-muted); white-space: nowrap; }
@media (max-width: 720px) { .header-main { display: grid; }.status-summary { justify-content: start; min-width: 0; } }
</style>
