<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  query: string;
  researchReadyOnly: boolean;
  previewableOnly: boolean;
  documents: readonly DocumentRecord[];
  selectedDocumentId: number | null;
  total: number;
  offset: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  "update:query": [value: string];
  search: [];
  updateResearchReady: [value: boolean];
  updatePreviewable: [value: boolean];
  select: [document: DocumentRecord];
  page: [offset: number];
  close: [];
}>();

const parseStatusLabel: Readonly<Record<DocumentRecord["parse_status"], string>> = {
  pending: "待解析", parsing: "解析中", succeeded: "已解析", failed: "解析失败",
};
const indexStatusLabel: Readonly<Record<DocumentRecord["index_status"], string>> = {
  pending: "待索引", indexing: "索引中", succeeded: "已索引", failed: "索引失败", outdated: "索引需更新",
};
</script>

<template>
  <section class="selector-section" aria-labelledby="current-paper-title">
    <header class="section-header">
      <p class="eyebrow">CURRENT PAPER</p>
      <h2 id="current-paper-title" class="section-title">选择当前论文</h2>
      <p class="section-description">选择一篇已准备好的论文，作为后续分析、问答与批注的唯一上下文。</p>
    </header>
    <button v-if="props.selectedDocumentId !== null" class="close-button" type="button" @click="emit('close')">收起选择器</button>
    <form class="search-form" @submit.prevent="emit('search')">
      <label class="search-label" for="paper-query">搜索论文</label>
      <div class="search-row">
        <input id="paper-query" :value="props.query" placeholder="搜索文件名或文件路径" @input="emit('update:query', ($event.target as HTMLInputElement).value)" />
        <button type="submit" :disabled="props.loading">搜索</button>
      </div>
      <div class="filter-row">
        <label><input type="checkbox" :checked="props.researchReadyOnly" @change="emit('updateResearchReady', ($event.target as HTMLInputElement).checked)" /> 仅可研究</label>
        <label><input type="checkbox" :checked="props.previewableOnly" @change="emit('updatePreviewable', ($event.target as HTMLInputElement).checked)" /> 仅可批注 PDF</label>
      </div>
    </form>
    <p v-if="props.error" class="error" role="alert">{{ props.error }}</p>
    <p v-else-if="props.loading" class="state-copy">正在加载可选论文…</p>
    <p v-else-if="props.documents.length === 0" class="state-copy">当前筛选条件下没有文档。可先在文档与知识完成解析和索引，或调整筛选条件。</p>
    <ul v-else class="document-list" aria-label="可选论文">
      <li v-for="document in props.documents" :key="document.id">
        <button class="document-option" :class="{ selected: document.id === props.selectedDocumentId }" type="button" @click="emit('select', document)">
          <strong>{{ document.original_filename || document.file_path }}</strong>
          <span class="path">{{ document.file_path }}</span>
          <span class="status">{{ document.media_type || "媒体类型未提供" }} · {{ parseStatusLabel[document.parse_status] }} · {{ indexStatusLabel[document.index_status] }}</span>
          <code class="document-id">ID {{ document.id }}</code>
        </button>
      </li>
    </ul>
    <div v-if="props.total > props.pageSize" class="pagination" aria-label="论文分页">
      <button type="button" :disabled="props.offset === 0 || props.loading" @click="emit('page', props.offset - props.pageSize)">上一页</button>
      <span>第 {{ Math.floor(props.offset / props.pageSize) + 1 }} 页，共 {{ props.total }} 篇</span>
      <button type="button" :disabled="props.offset + props.pageSize >= props.total || props.loading" @click="emit('page', props.offset + props.pageSize)">下一页</button>
    </div>
  </section>
</template>

<style scoped>
.selector-section { position: relative; display: grid; gap: .85rem; padding: 1.15rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); background: var(--surface); box-shadow: var(--shadow); }
.section-header { display: grid; gap: .3rem; }.eyebrow { margin: 0; color: var(--color-primary); font-size: .7rem; font-weight: 900; letter-spacing: .1em; }.section-title { margin: 0; color: var(--text-primary); font-size: 1.18rem; }.section-description,.state-copy,.path,.status { margin: 0; color: var(--text-muted); font-size: .86rem; }.search-form { display: grid; gap: .55rem; }.search-label { color: var(--text-primary); font-size: .85rem; font-weight: 750; }.search-row { display: flex; gap: .55rem; }.search-row input { flex: 1; min-width: 0; padding: .62rem .7rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--paper); font: inherit; }.search-row button,.pagination button { padding: .62rem .85rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--paper); color: var(--text-primary); font: inherit; }.search-row button { border-color: var(--color-primary); background: var(--color-primary); color: #fff; font-weight: 750; }.filter-row { display: flex; flex-wrap: wrap; gap: .9rem; color: var(--text-primary); font-size: .84rem; }.filter-row label { display: inline-flex; align-items: center; gap: .35rem; }.error { margin: 0; color: var(--color-danger); }.document-list { display: grid; gap: .45rem; margin: 0; padding: 0; list-style: none; }.document-option { display: grid; gap: .25rem; width: 100%; padding: .75rem .8rem; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--paper); color: var(--text-primary); text-align: left; cursor: pointer; }.document-option:hover,.document-option:focus-visible,.document-option.selected { border-color: var(--color-primary); background: var(--color-primary-soft); outline: none; }.path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.status { font-size: .78rem; }.pagination { display: flex; align-items: center; justify-content: space-between; gap: .5rem; color: var(--text-muted); font-size: .8rem; }.pagination button:disabled,.search-row button:disabled { opacity: .55; cursor: not-allowed; } @media (max-width: 620px) { .search-row { flex-direction: column; }.pagination { align-items: stretch; flex-direction: column; } }
</style>
