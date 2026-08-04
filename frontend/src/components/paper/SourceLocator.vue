<script setup lang="ts">
import type { ResolvedPaperSource } from "./paperModel";

/**
 * 来源定位行：展示页码/章节引用行。
 * 后端无字段时一律"未提供"；不假装能打开原文（openOriginal 由外部决定是否可用）。
 */
defineProps<{ source: ResolvedPaperSource }>();

const emit = defineEmits<{ jump: [localIndex: number] }>();

/** 页码区间文本；任一页码缺失则整体显示"未提供" */
function pageText(pageStart: number | null, pageEnd: number | null): string {
  if (pageStart === null) return "未提供";
  if (pageEnd !== null && pageEnd > pageStart) return `第 ${pageStart}–${pageEnd} 页`;
  return `第 ${pageStart} 页`;
}
</script>

<template>
  <div class="locator">
    <button class="jump" type="button" :aria-label="`定位到第 ${source.page_start ?? '?'} 页来源`" @click="emit('jump', source.local_index)">
      定位
    </button>
    <span class="page">{{ pageText(source.page_start, source.page_end) }}</span>
    <span class="citation">{{ source.citation || source.title || "引用信息未提供" }}</span>
  </div>
</template>

<style scoped>
.locator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  color: var(--text-muted);
  font-size: 0.76rem;
}
.jump {
  flex-shrink: 0;
  padding: 0.22rem 0.5rem;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  background: var(--surface);
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: 750;
  transition: border-color 0.15s, background-color 0.15s;
}
.jump:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.page {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--text-primary);
}
.citation {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
