<script setup lang="ts">
import { computed } from "vue";

import type { PaperFacets, PaperFilters, PaperView } from "../../api/paperLibrary";
import BaseIcon from "../ui/BaseIcon.vue";
import PaperFilterGroup from "./PaperFilterGroup.vue";
import { analysisLabel, readingLabel, roleLabel } from "./paperLibraryFormatters";

export type PaperFilterGroupKey = "readingStatus" | "analysisStatus" | "paperTypes" | "researchRoles" | "researchIds" | "tags";

const props = defineProps<{ open: boolean; filters: Readonly<PaperFilters>; facets: PaperFacets | null }>();
const emit = defineEmits<{ close: []; clear: []; view: [view: PaperView]; toggle: [group: PaperFilterGroupKey, value: string] }>();

const activeCount = computed(() => props.filters.readingStatus.length + props.filters.analysisStatus.length + props.filters.paperTypes.length + props.filters.researchRoles.length + props.filters.researchIds.length + props.filters.tags.length);
const empty = [] as const;
const readingOptions = computed(() => (props.facets?.reading_status ?? empty).map((item) => ({ ...item, label: item.label ?? readingLabel(item.value as "unread" | "reading" | "read") })));
const analysisOptions = computed(() => (props.facets?.analysis_status ?? empty).map((item) => ({ ...item, label: item.label ?? analysisLabel(item.value as "not_started" | "pending" | "analyzing" | "completed" | "failed" | "cancelled") })));
const roleOptions = computed(() => (props.facets?.research_roles ?? empty).map((item) => ({ ...item, label: item.label ?? roleLabel(item.value as "core_evidence" | "background_support" | "method_reference" | "supplementary_reading" | "to_evaluate") })));
</script>

<template>
  <div class="filter-layer" :class="{ open }" @click.self="emit('close')">
    <aside class="filter-rail" aria-label="论文筛选">
      <header class="rail-heading">
        <div><strong>筛选</strong><span v-if="activeCount">{{ activeCount }}</span></div>
        <button class="reset" type="button" :disabled="!activeCount" @click="emit('clear')">重置</button>
        <button class="rail-close" type="button" aria-label="关闭筛选" @click="emit('close')"><BaseIcon name="close" /></button>
      </header>
      <label class="scope-label" for="paper-library-scope">当前范围</label>
      <select id="paper-library-scope" class="scope-select" :value="filters.view" @change="emit('view', ($event.target as HTMLSelectElement).value as PaperView)">
        <option value="all">全部论文</option><option value="recent">最近使用</option><option value="reading">阅读中</option><option value="analyzing">分析中</option><option value="unclassified">待归类</option>
      </select>
      <PaperFilterGroup title="阅读状态" :options="readingOptions" :selected="filters.readingStatus" @toggle="emit('toggle', 'readingStatus', $event)" />
      <PaperFilterGroup title="论文分析" :options="analysisOptions" :selected="filters.analysisStatus" @toggle="emit('toggle', 'analysisStatus', $event)" />
      <PaperFilterGroup title="研究角色" :options="roleOptions" :selected="filters.researchRoles" @toggle="emit('toggle', 'researchRoles', $event)" />
      <PaperFilterGroup title="论文类型" :options="facets?.paper_types ?? empty" :selected="filters.paperTypes" :initial-open="false" @toggle="emit('toggle', 'paperTypes', $event)" />
      <PaperFilterGroup title="关联研究" :options="facets?.research_contexts ?? empty" :selected="filters.researchIds.map(String)" searchable @toggle="emit('toggle', 'researchIds', $event)" />
      <PaperFilterGroup title="标签" :options="facets?.tags ?? empty" :selected="filters.tags" :initial-open="false" searchable @toggle="emit('toggle', 'tags', $event)" />
    </aside>
  </div>
</template>

<style scoped>
.filter-layer{min-width:0;border-right:1px solid var(--line);background:#fff}.filter-rail{height:100%;padding:20px 17px 28px;overflow:auto;background:#fff}.rail-heading{display:grid;grid-template-columns:1fr auto;align-items:center;margin-bottom:20px}.rail-heading>div{display:flex;align-items:center;gap:7px}.rail-heading strong{font-size:14px}.rail-heading span{display:grid;min-width:19px;height:19px;place-items:center;border-radius:10px;background:#eaf2ff;color:#0b5fcc;font-size:10px}.reset,.rail-close{border:0;background:transparent;color:#0b5fcc;font:inherit;font-size:12px}.reset:disabled{color:#94a3b8;cursor:not-allowed}.rail-close{display:none;width:34px;height:34px;place-items:center}.scope-label{display:block;margin-bottom:6px;color:#64748b;font-size:11px}.scope-select{width:100%;height:36px;margin-bottom:8px;border:1px solid var(--line);border-radius:4px;padding:0 10px;background:#fff;color:#334155;font:inherit;font-size:12.5px}
@media(max-width:1279px){.filter-layer{position:fixed;z-index:45;inset:0;display:none;border:0;background:rgb(15 23 42 / 28%)}.filter-layer.open{display:block}.filter-rail{width:min(320px,calc(100vw - 48px));box-shadow:8px 0 24px rgb(15 23 42 / 10%)}.rail-heading{grid-template-columns:1fr auto auto}.rail-close{display:grid}}
@media(max-width:767px){.filter-rail{width:100%;padding-top:16px}.filter-layer.open{background:#fff}}
</style>
