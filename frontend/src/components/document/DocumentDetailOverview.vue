<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  document: DocumentRecord;
  summary: { page_count: number; character_count: number; section_headings: readonly string[] } | null;
  actionLoading: boolean;
}>();

function parseStatusLabel(status: DocumentRecord["parse_status"]): string {
  return { pending: "等待解析", parsing: "正在解析", succeeded: "解析完成", failed: "解析失败" }[status];
}

function indexStatusLabel(status: DocumentRecord["index_status"]): string {
  return { pending: "等待索引", indexing: "正在索引", succeeded: "索引完成", failed: "索引失败", outdated: "索引已过期" }[status];
}

const emit = defineEmits<{
  retryParse: [];
  retryIndex: [];
}>();
</script>

<template>
  <section class="overview" aria-labelledby="information-title">
    <header class="overview-header"><h2 id="information-title" class="section-title">文档信息</h2></header>

    <dl class="metadata">
      <div><dt>解析状态</dt><dd>{{ parseStatusLabel(props.document.parse_status) }}</dd></div>
      <div><dt>索引状态</dt><dd>{{ indexStatusLabel(props.document.index_status) }}</dd></div>
      <div><dt>修改时间</dt><dd>{{ props.document.modified_time }}</dd></div>
      <div><dt>重试次数</dt><dd>{{ props.document.retry_count }}</dd></div>
    </dl>

    <dl v-if="props.summary" class="summary"><div><dt>内容摘要</dt><dd>共 {{ props.summary.page_count }} 页，{{ props.summary.character_count }} 个字符。</dd></div><div v-if="props.summary.section_headings.length"><dt>章节</dt><dd>{{ props.summary.section_headings.join('、') }}</dd></div></dl>

    <div class="actions">
      <button
        v-if="props.document.parse_status === 'failed' || props.document.parse_status === 'pending'"
        :disabled="props.actionLoading"
        @click="emit('retryParse')"
      >
        {{ props.document.parse_status === 'pending' ? '开始解析' : '重试解析' }}
      </button>
      <button
        v-if="props.document.index_status === 'failed' || props.document.index_status === 'outdated'"
        :disabled="props.actionLoading"
        @click="emit('retryIndex')"
      >
        重试索引
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview { display: grid; gap: 1rem; }
.section-title { margin: 0; font-size: 1rem; }
.metadata, .summary { display: grid; gap: .65rem; margin: 0; }
.metadata div, .summary div { display: grid; grid-template-columns: 5rem minmax(0, 1fr); gap: .6rem; align-items: baseline; padding-bottom: .6rem; border-bottom: 1px solid var(--border-subtle); }
.metadata dt { color: var(--text-muted); font-size: .8rem; }
.metadata dd, .summary dd { margin: 0; color: var(--text-primary); font-weight: 650; overflow-wrap: anywhere; }
.actions { display: flex; gap: .6rem; }
.actions button { border: 0; border-radius: 8px; padding: .6rem .85rem; background: var(--color-primary); color: #fff; font: inherit; }
</style>
