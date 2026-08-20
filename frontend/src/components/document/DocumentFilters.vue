<script setup lang="ts">
import { onBeforeUnmount, reactive, watch } from "vue";

import type { DocumentFilters as DocumentFiltersValue } from "../../api/documents";

const props = defineProps<{ filters: Readonly<DocumentFiltersValue>; disabled: boolean }>();
const emit = defineEmits<{ change: [filters: DocumentFiltersValue] }>();

const draft = reactive<DocumentFiltersValue>({ ...props.filters });
let searchTimer: ReturnType<typeof setTimeout> | null = null;

watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });

function submit(): void {
  // 工具带只负责文档检索；正文定位已从文档库移除，恒定使用 document 模式。
  emit("change", { ...draft, mode: "document", query: draft.query.trim() });
}

function scheduleSearch(): void {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(submit, 320);
}

function clearFilters(): void {
  Object.assign(draft, { query: "", fileType: "", healthStatus: "" });
  submit();
}

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<template>
  <form class="document-filters" aria-label="文档查询" @submit.prevent="submit">
    <div class="search-row">
      <label class="search-input" for="document-file-query">
        <span aria-hidden="true">⌕</span>
        <input id="document-file-query" v-model="draft.query" :disabled="props.disabled" placeholder="搜索文档名称或文件路径…" @input="scheduleSearch">
      </label>
      <button class="search-button" type="submit" :disabled="props.disabled">搜索</button>
    </div>

    <div class="filter-row">
      <label class="filter-control"><span>文件类型</span><select v-model="draft.fileType" :disabled="props.disabled" @change="submit"><option value="">全部类型</option><option value="pdf">PDF</option><option value="pptx">PPTX</option><option value="docx">DOCX</option><option value="markdown">Markdown</option><option value="txt">TXT</option><option value="other">其他</option></select></label>
      <label class="filter-control"><span>处理状态</span><select v-model="draft.healthStatus" :disabled="props.disabled" @change="submit"><option value="">全部状态</option><option value="available">可用于问答</option><option value="processing">处理中</option><option value="needs_attention">需处理</option></select></label>
      <label class="filter-control"><span>排序</span><select v-model="draft.sortBy" :disabled="props.disabled" @change="submit"><option value="updated_at">最近更新</option><option value="name">文档名称</option><option value="file_size">文件大小</option></select></label>
      <button class="sort-order" type="button" :disabled="props.disabled" :aria-label="draft.sortOrder === 'desc' ? '切换为升序' : '切换为降序'" @click="draft.sortOrder = draft.sortOrder === 'desc' ? 'asc' : 'desc'; submit()">{{ draft.sortOrder === "desc" ? "↓" : "↑" }}</button>
      <button class="clear" type="button" :disabled="props.disabled" @click="clearFilters">清除</button>
    </div>
  </form>
</template>

<style scoped>
.document-filters { padding: 12px 14px; border-bottom: 1px solid var(--border-subtle); background: #fcfdff; }
.search-row { display: flex; align-items: center; gap: 8px; }
.search-input { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; height: 36px; box-sizing: border-box; padding: 0 11px; border: 1px solid var(--border-strong); border-radius: 7px; background: var(--surface); color: var(--text-faint); }.search-input:focus-within { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgb(37 99 235 / 10%); }.search-input span { font-size: .95rem; }.search-input input { min-width: 0; width: 100%; border: 0; outline: 0; background: transparent; color: var(--text-primary); font: inherit; font-size: .8rem; }
.search-button { height: 36px; border: 1px solid var(--color-primary); border-radius: 7px; padding: 0 14px; background: var(--color-primary); color: #fff; font: inherit; font-size: .76rem; font-weight: 800; cursor: pointer; }
.filter-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.filter-control { display: flex; align-items: center; gap: 7px; min-height: 30px; padding: 0 8px; border: 1px solid var(--border-subtle); border-radius: 6px; background: var(--surface); color: var(--text-faint); font-size: .68rem; font-weight: 750; }.filter-row select { max-width: 120px; border: 0; padding: 0; outline: 0; background: transparent; color: var(--text-primary); font: inherit; font-size: .72rem; font-weight: 700; cursor: pointer; }
.sort-order, .clear { border: 0; background: transparent; color: var(--text-muted); font: inherit; font-size: .74rem; font-weight: 800; cursor: pointer; }.sort-order { width: 30px; height: 30px; border: 1px solid var(--border-subtle); border-radius: 6px; background: var(--surface); }.clear { margin-left: auto; color: var(--color-primary); }
button:disabled, select:disabled, input:disabled { cursor: not-allowed; opacity: .55; }
@media (max-width: 680px) { .search-row { flex-wrap: wrap; }.search-input { min-width: calc(100% - 66px); }.filter-row { align-items: flex-start; flex-wrap: wrap; }.clear { margin-left: 0; } }
</style>
