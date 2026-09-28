<script setup lang="ts">
import { shallowRef } from "vue";

import type { FacetValue } from "../../api/paperLibrary";
import BaseIcon from "../ui/BaseIcon.vue";

const props = withDefaults(defineProps<{
  title: string;
  options: readonly FacetValue[];
  selected: readonly string[];
  initialOpen?: boolean;
  searchable?: boolean;
}>(), { initialOpen: true, searchable: false });
const emit = defineEmits<{ toggle: [value: string] }>();
const expanded = shallowRef(props.initialOpen);
const query = shallowRef("");
</script>

<template>
  <section class="filter-group">
    <button class="group-toggle" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
      <span>{{ title }}</span><BaseIcon name="chevron-down" :class="{ rotated: expanded }" />
    </button>
    <div v-if="expanded" class="group-body">
      <label v-if="searchable" class="option-search">
        <BaseIcon name="search" /><input v-model="query" :aria-label="`搜索${title}`" :placeholder="`搜索${title}…`" />
      </label>
      <label
        v-for="option in options.filter((item) => !query || (item.label ?? item.value).toLowerCase().includes(query.toLowerCase()))"
        :key="option.value"
        class="filter-option"
      >
        <input type="checkbox" :checked="selected.includes(option.value)" @change="emit('toggle', option.value)" />
        <span class="option-label">{{ option.label ?? option.value }}</span>
        <span class="option-count">{{ option.count }}</span>
      </label>
      <p v-if="!options.length" class="no-options">当前范围暂无可选项</p>
    </div>
  </section>
</template>

<style scoped>
.filter-group{border-bottom:1px solid var(--line);padding:13px 0}.group-toggle{display:flex;width:100%;align-items:center;justify-content:space-between;border:0;padding:0;background:transparent;color:var(--ink-900);font:inherit;font-size:13px;font-weight:750;text-align:left}.group-toggle :deep(.icon){width:14px;height:14px;color:#475569;transition:transform .15s}.group-toggle .rotated{transform:rotate(180deg)}.group-body{display:grid;gap:1px;margin-top:9px}.filter-option{display:flex;min-height:30px;align-items:center;gap:8px;color:#475569;font-size:12.5px;cursor:pointer}.filter-option input{width:14px;height:14px;margin:0;accent-color:var(--blue-600)}.option-label{overflow:hidden;min-width:0;text-overflow:ellipsis;white-space:nowrap}.option-count{margin-left:auto;color:#64748b;font-variant-numeric:tabular-nums}.option-search{display:flex;min-height:32px;align-items:center;gap:6px;margin:0 0 5px;border:1px solid var(--line);border-radius:4px;padding:0 8px;color:#94a3b8}.option-search :deep(.icon){width:14px}.option-search input{min-width:0;width:100%;border:0;outline:0;background:transparent;font:inherit;font-size:12px}.no-options{margin:5px 0 2px;color:#94a3b8;font-size:11px}@media(prefers-reduced-motion:reduce){.group-toggle :deep(.icon){transition:none}}
</style>
