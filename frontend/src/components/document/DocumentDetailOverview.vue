<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  document: DocumentRecord;
  actionLoading: boolean;
}>();

const emit = defineEmits<{
  retryParse: [];
  retryIndex: [];
}>();
</script>

<template>
  <section class="overview" aria-labelledby="document-title">
    <header class="overview-header">
      <div>
        <p class="eyebrow">DOCUMENT DETAIL · LIVE</p>
        <h1 id="document-title" class="document-title">
          {{ props.document.original_filename ?? props.document.file_path }}
        </h1>
        <p class="description">仅展示经服务端受控接口提供的原文和解析元数据。</p>
      </div>
    </header>

    <dl class="metadata">
      <div><dt>解析状态</dt><dd>{{ props.document.parse_status }}</dd></div>
      <div><dt>索引状态</dt><dd>{{ props.document.index_status }}</dd></div>
      <div><dt>修改时间</dt><dd>{{ props.document.modified_time }}</dd></div>
      <div><dt>重试次数</dt><dd>{{ props.document.retry_count }}</dd></div>
    </dl>

    <div class="actions">
      <button
        v-if="props.document.parse_status === 'failed'"
        :disabled="props.actionLoading"
        @click="emit('retryParse')"
      >
        重试解析
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
.overview-header { display: flex; justify-content: space-between; gap: 1rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 900; font-size: .72rem; letter-spacing: .12em; }
.document-title { max-width: 760px; margin: .25rem 0 .45rem; overflow-wrap: anywhere; color: var(--text-primary); }
.description { margin: 0; color: var(--text-muted); }
.metadata { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; margin: 0; background: var(--border-subtle); border: 1px solid var(--border-subtle); }
.metadata div { display: grid; gap: .45rem; padding: 1rem; background: var(--paper); }
.metadata dt { color: var(--text-muted); font-size: .8rem; }
.metadata dd { margin: 0; color: var(--text-primary); font-weight: 750; }
.actions { display: flex; gap: .6rem; }
.actions button { border: 0; border-radius: 8px; padding: .6rem .85rem; background: var(--color-primary); color: #fff; font: inherit; }
@media (max-width: 700px) { .metadata { grid-template-columns: repeat(2, 1fr); } }
</style>
