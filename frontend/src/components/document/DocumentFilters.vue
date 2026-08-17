<script setup lang="ts">
import { reactive, watch } from "vue";
import type { DocumentFilters as DocumentFiltersValue } from "../../api/documents";
const props = defineProps<{ filters: Readonly<DocumentFiltersValue>; disabled: boolean }>();
const emit = defineEmits<{ change: [filters: DocumentFiltersValue] }>();
const draft = reactive<DocumentFiltersValue>({ parseStatus: props.filters.parseStatus, indexStatus: props.filters.indexStatus, query: props.filters.query ?? "", researchReady: props.filters.researchReady ?? false, knowledgeSourceId: props.filters.knowledgeSourceId ?? null });
watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });
function apply(): void { emit("change", { ...draft, query: draft.query?.trim() || undefined }); }
function clearFilters(): void { Object.assign(draft, { parseStatus: "", indexStatus: "", query: "", researchReady: false }); apply(); }
</script>
<template>
  <form class="filters" aria-label="文件筛选" @submit.prevent="apply">
    <div class="file-lookup">
      <label class="search" for="document-file-query">
        <span class="search-mark" aria-hidden="true">⌕</span>
        <span>按文件名查找</span>
      </label>
      <input
        id="document-file-query"
        v-model="draft.query"
        :disabled="props.disabled"
        placeholder="文件名或相对路径，如 2026 或 PD-1"
      />
      <button class="filter-submit" type="submit" :disabled="props.disabled">筛选</button>
      <span class="lookup-hint">用于查找未解析或未索引的文件</span>
    </div>
    <div class="filter-row"><select v-model="draft.parseStatus" :disabled="props.disabled" aria-label="解析状态" @change="apply"><option value="">全部解析状态</option><option value="pending">等待</option><option value="parsing">处理中</option><option value="succeeded">成功</option><option value="failed">失败</option></select><select v-model="draft.indexStatus" :disabled="props.disabled" aria-label="索引状态" @change="apply"><option value="">全部索引状态</option><option value="pending">等待</option><option value="indexing">处理中</option><option value="succeeded">已索引</option><option value="failed">失败</option><option value="outdated">索引过期</option></select><label class="indexed-only"><input v-model="draft.researchReady" type="checkbox" @change="apply" />仅显示可用于证据问答</label><button class="clear" type="button" :disabled="props.disabled" @click="clearFilters">清除筛选</button></div>
  </form>
</template>
<style scoped>
.filters { padding: 8px 12px 10px; border-top: 1px solid var(--border-subtle); border-bottom: 1px solid var(--border-subtle); }
.file-lookup { display: flex; align-items: center; gap: 7px; min-height: 29px; color: var(--text-muted); }
.search { display: inline-flex; align-items: center; gap: 4px; flex: none; font-size: .7rem; font-weight: 700; white-space: nowrap; }
.search-mark { color: var(--text-faint); font-size: .9rem; line-height: 1; }
.file-lookup input { min-width: 120px; flex: 1; height: 28px; box-sizing: border-box; border: 1px solid var(--border-subtle); border-radius: 5px; padding: 0 7px; background: var(--surface); color: var(--text-primary); font: inherit; font-size: .72rem; }
.filter-submit, .clear { border: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: .7rem; font-weight: 700; }
.lookup-hint { color: var(--text-faint); font-size: .68rem; white-space: nowrap; }
.filter-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.filter-row select { border: 1px solid var(--border-subtle); border-radius: 5px; padding: 5px 7px; background: var(--surface); color: var(--text-muted); font-size: .73rem; }
.indexed-only { margin-left: auto; color: var(--text-muted); font-size: .72rem; white-space: nowrap; }
.clear { color: var(--text-muted); }
@media(max-width:700px) { .file-lookup { align-items: flex-start; flex-wrap: wrap; } .file-lookup input { flex-basis: 180px; } .lookup-hint { width: 100%; } .filter-row { align-items: flex-start; flex-direction: column; } .indexed-only { margin-left: 0; } }
</style>
