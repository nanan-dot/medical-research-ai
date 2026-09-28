<script setup lang="ts">
import type { PaperSort } from "../../api/paperLibrary";
import BaseIcon from "../ui/BaseIcon.vue";

export interface PaperFilterChip { key: string; label: string; }
defineProps<{ chips: readonly PaperFilterChip[]; total: number; sort: PaperSort; density: "comfortable" | "compact"; refreshing: boolean }>();
const emit = defineEmits<{ remove: [key: string]; clear: []; sort: [sort: PaperSort]; density: [density: "comfortable" | "compact"]; openFilters: [] }>();
</script>

<template>
  <div class="toolbar">
    <div v-if="chips.length" class="filter-chips" aria-label="已选筛选条件">
      <button v-for="chip in chips" :key="chip.key" type="button" :aria-label="`移除筛选 ${chip.label}`" @click="emit('remove', chip.key)">{{ chip.label }} <BaseIcon name="close" /></button>
      <button class="clear-chips" type="button" @click="emit('clear')">清除全部</button>
    </div>
    <div class="result-line">
      <button class="mobile-filter" type="button" @click="emit('openFilters')"><BaseIcon name="filter" />筛选</button>
      <b>{{ total }} 篇结果</b><span v-if="refreshing" class="refreshing" aria-live="polite">正在更新…</span>
      <label class="sort-control">排序<select :value="sort" @change="emit('sort', ($event.target as HTMLSelectElement).value as PaperSort)"><option value="recent_activity">最近活动</option><option value="added_at">添加时间</option><option value="year">发表年份</option><option value="title">论文标题</option></select></label>
      <div class="density-switch" aria-label="列表密度">
        <button type="button" :class="{ active: density === 'comfortable' }" aria-label="标准列表" :aria-pressed="density === 'comfortable'" @click="emit('density', 'comfortable')">☷</button>
        <button type="button" :class="{ active: density === 'compact' }" aria-label="紧凑列表" :aria-pressed="density === 'compact'" @click="emit('density', 'compact')">▦</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar{border-bottom:1px solid var(--line);background:#fff}.filter-chips{display:flex;min-height:46px;align-items:center;gap:7px;padding:8px 16px 2px;overflow-x:auto}.filter-chips button{display:inline-flex;min-height:28px;flex:0 0 auto;align-items:center;gap:5px;border:1px solid #dbe5f2;border-radius:4px;padding:0 8px;background:#f7f9fc;color:#3b4d66;font:inherit;font-size:11.5px}.filter-chips :deep(.icon){width:12px;height:12px}.filter-chips .clear-chips{border-color:transparent;background:transparent;color:#0b5fcc}.result-line{display:flex;height:44px;align-items:center;gap:10px;padding:0 16px;color:#475569;font-size:12px}.result-line>b{color:#475569;font-size:12.5px;font-weight:600}.refreshing{color:#64748b}.sort-control{display:flex;align-items:center;gap:5px;margin-left:auto}.sort-control select{height:31px;border:0;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:650}.density-switch{display:flex;gap:4px}.density-switch button,.mobile-filter{display:grid;width:31px;height:31px;place-items:center;border:1px solid var(--line);border-radius:4px;background:#fff;color:#64748b;font:inherit}.density-switch button.active{border-color:#c9ddfb;background:#eaf2ff;color:#0b5fcc}.mobile-filter{display:none;width:auto;grid-auto-flow:column;gap:5px;padding:0 9px}.mobile-filter :deep(.icon){width:14px}
@media(max-width:1279px){.mobile-filter{display:inline-grid}}
@media(max-width:767px){.filter-chips{padding-inline:12px}.result-line{padding-inline:12px}.density-switch{display:none}.sort-control{font-size:0}.sort-control select{font-size:11.5px}}
</style>
