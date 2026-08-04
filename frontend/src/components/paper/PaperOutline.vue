<script setup lang="ts">
import type { PaperSource } from "../../api/paperAnalysis";
import { OUTLINE_SECTIONS, sectionStatus } from "./paperModel";

/**
 * 左侧章节导航（Paper Structure Navigator）。
 * 章节列表为展示层常量；每章状态从 sources[].page_start 推导（有引用=已分析）。
 */
defineProps<{ sources: readonly PaperSource[] }>();

const emit = defineEmits<{ navigate: [sectionKey: string] }>();
</script>

<template>
  <nav class="outline" aria-label="论文大纲">
    <p class="eyebrow">PAPER OUTLINE</p>
    <ul class="sections">
      <li v-for="section in OUTLINE_SECTIONS" :key="section.key">
        <button class="section" type="button" @click="emit('navigate', section.key)">
          <span class="dot" :class="sectionStatus(section.key, sources) === 'analyzed' ? 'dot--analyzed' : 'dot--uncovered'" />
          <span class="label">{{ section.label }}</span>
          <span class="status">{{ sectionStatus(section.key, sources) === 'analyzed' ? '已分析' : '未覆盖' }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.outline {
  display: grid;
  gap: 0.7rem;
  align-content: start;
  padding: 1.15rem 0.9rem;
}
.eyebrow {
  margin: 0;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}
.sections {
  display: grid;
  gap: 0.15rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.45rem 0.5rem;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  font-size: 0.84rem;
  transition: background-color 0.15s;
}
.section:hover {
  background: var(--surface-muted);
}
.dot {
  flex-shrink: 0;
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 99px;
  background: var(--text-faint);
}
.dot--analyzed {
  background: var(--color-success);
}
.dot--uncovered {
  background: var(--border-strong);
}
.label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.status {
  flex-shrink: 0;
  font-size: 0.68rem;
  color: var(--text-faint);
}
</style>
