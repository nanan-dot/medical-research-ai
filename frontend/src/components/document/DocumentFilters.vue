<script setup lang="ts">
import { reactive, watch } from "vue";

import type { DocumentFilters } from "../../api/documents";

const props = defineProps<{ filters: Readonly<DocumentFilters>; disabled: boolean }>();
const emit = defineEmits<{ change: [filters: DocumentFilters] }>();
const draft = reactive<DocumentFilters>({ parseStatus: props.filters.parseStatus, indexStatus: props.filters.indexStatus, query: props.filters.query ?? "", researchReady: props.filters.researchReady ?? false, knowledgeSourceId: props.filters.knowledgeSourceId ?? null });
watch(() => props.filters, (filters) => Object.assign(draft, filters), { deep: true });
function apply(): void { emit("change", { ...draft, query: draft.query?.trim() || undefined }); }
</script>

<template>
  <form class="filters" @submit.prevent="apply"><label class="search"><span>AI</span><input v-model="draft.query" :disabled="disabled" placeholder="在资料中查找什么……"><button type="submit" :disabled="disabled">⌕</button></label><div class="filter-row"><select v-model="draft.parseStatus" :disabled="disabled" @change="apply"><option value="">全部解析状态</option><option value="pending">等待</option><option value="parsing">解析中</option><option value="succeeded">成功</option><option value="failed">失败</option></select><select v-model="draft.indexStatus" :disabled="disabled" @change="apply"><option value="">全部索引状态</option><option value="pending">等待</option><option value="indexing">索引中</option><option value="succeeded">已索引</option><option value="failed">失败</option><option value="outdated">索引过期</option></select><label class="indexed-only"><input v-model="draft.researchReady" type="checkbox" @change="apply">仅显示可用于证据问答</label></div></form>
</template>

<style scoped>
.filters{padding:14px;border-bottom:1px solid var(--border-subtle)}.search{display:flex;align-items:center;gap:8px;height:39px;padding:0 10px;border:1px solid var(--border-subtle);border-radius:8px;background:#fff}.search span{padding:2px 5px;border-radius:4px;background:var(--color-primary-soft);color:var(--color-primary);font-size:.68rem;font-weight:800}.search input{min-width:0;flex:1;border:0;outline:0;font:inherit}.search button{border:0;background:transparent;color:var(--color-primary);font-size:1rem}.filter-row{display:flex;align-items:center;gap:8px;margin-top:10px}.filter-row select{border:1px solid var(--border-subtle);border-radius:6px;padding:5px 7px;background:#fff;color:var(--text-muted);font-size:.75rem}.indexed-only{margin-left:auto;color:var(--text-muted);font-size:.75rem;white-space:nowrap}@media(max-width:560px){.filter-row{flex-wrap:wrap}.indexed-only{margin-left:0}}
</style>
