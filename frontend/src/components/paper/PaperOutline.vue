<script setup lang="ts">
import { OUTLINE_SECTIONS } from "./paperModel";

/**
 * 章节导航只反映当前报告中可滚动到的分析块。
 * 后端没有论文原始章节边界，故不从页码推断“已覆盖”的章节状态。
 */
const props = defineProps<{ availableSections: readonly string[] }>();

const emit = defineEmits<{ navigate: [sectionKey: string] }>();

function isAvailable(sectionKey: string): boolean {
  return props.availableSections.includes(sectionKey);
}
</script>

<template>
  <nav class="outline" aria-label="论文结构">
    <p class="eyebrow">PAPER OUTLINE</p>
    <h2 class="title">论文结构</h2>
    <ul class="sections">
      <li v-for="section in OUTLINE_SECTIONS" :key="section.key">
        <button
          class="section"
          :class="{ 'section--available': isAvailable(section.key) }"
          type="button"
          :disabled="!isAvailable(section.key)"
          @click="emit('navigate', section.key)"
        >
          <span class="label">{{ section.label }}</span>
          <span class="status">{{ isAvailable(section.key) ? "定位" : "未提供" }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.outline {
  display: grid;
  align-content: start;
  gap: 0.45rem;
  padding: 1.15rem 0.9rem;
}
.eyebrow {
  margin: 0;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}
.title {
  margin: 0 0 0.3rem;
  color: var(--text-primary);
  font-size: 0.95rem;
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
  color: var(--text-faint);
  text-align: left;
  font-size: 0.84rem;
}
.section--available {
  color: var(--text-primary);
  cursor: pointer;
}
.section--available:hover,
.section--available:focus-visible {
  background: var(--surface-muted);
  outline: none;
}
.label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status {
  flex-shrink: 0;
  color: var(--text-faint);
  font-size: 0.68rem;
}
.section--available .status {
  color: var(--color-primary);
}
</style>
