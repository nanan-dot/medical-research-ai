<script setup lang="ts">
import type { PaperSummary, PaperView } from "../../api/paperLibrary";

const props = defineProps<{ active: PaperView; summary: PaperSummary | null }>();
const emit = defineEmits<{ select: [view: PaperView] }>();
const views: ReadonlyArray<{ key: PaperView; label: string; count: keyof PaperSummary }> = [
  { key: "all", label: "全部论文", count: "all" }, { key: "recent", label: "最近使用", count: "recent" },
  { key: "reading", label: "阅读中", count: "reading" }, { key: "analyzing", label: "分析中", count: "analyzing" },
  { key: "unclassified", label: "待归类", count: "unclassified" },
];
</script>

<template>
  <nav class="quick-views" aria-label="论文快捷视图">
    <button v-for="view in views" :key="view.key" type="button" :class="{ active: props.active === view.key }" :aria-current="props.active === view.key ? 'page' : undefined" @click="emit('select', view.key)">
      {{ view.label }} <b v-if="props.summary">{{ props.summary[view.count] }}</b>
    </button>
  </nav>
</template>

<style scoped>
.quick-views{display:flex;height:64px;align-items:stretch;gap:30px;padding:0 20px;border-bottom:1px solid var(--line);overflow-x:auto;background:#fff}.quick-views button{position:relative;flex:0 0 auto;border:0;padding:0 3px;background:transparent;color:#475569;font:inherit;font-size:13.5px;white-space:nowrap}.quick-views button::after{position:absolute;right:0;bottom:0;left:0;height:3px;background:transparent;content:""}.quick-views button.active{color:#0b5fcc;font-weight:750}.quick-views button.active::after{background:#0b5fcc}.quick-views b{margin-left:5px;font-weight:600;font-variant-numeric:tabular-nums}@media(max-width:767px){.quick-views{height:52px;gap:24px;padding-inline:14px}.quick-views button{font-size:12.5px}}
</style>
