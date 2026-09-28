<script setup lang="ts">
import { computed } from "vue";
import type {
  SearchStrategyDraft,
  SearchStrategyVersion,
  StrategySaveState,
} from "../../types/searchStrategy";

const props = defineProps<{
  strategy: SearchStrategyDraft;
  versions: SearchStrategyVersion[];
  saveState: StrategySaveState;
  executing: boolean;
  disabled: boolean;
}>();
const emit = defineEmits<{ execute: [] }>();
const versionLabel = computed(() =>
  props.versions[0] ? `策略版本 v${props.versions[0].version}` : "当前草稿",
);
const saveLabel = computed(
  () =>
    ({
      saved: "已保存",
      saving: "保存中…",
      unsaved: "待保存",
      failed: "保存失败",
      conflict: "版本冲突",
    })[props.saveState],
);
</script>

<template>
  <footer class="strategy-sticky" aria-label="检索策略操作">
    <div class="summary">
      <details class="sticky-version-menu">
        <summary class="version-selector" :aria-label="`当前${versionLabel}`">
          {{ versionLabel }}⌄
        </summary>
        <div class="sticky-version-options">
          <span v-if="!props.versions.length">尚未保存版本</span>
          <span v-for="version in props.versions" :key="version.id"
            >版本 v{{ version.version }}</span
          >
        </div>
      </details>
      <span :class="`save-${props.saveState}`">{{ saveLabel }}</span
      ><span>{{ props.strategy.terms.length }} 个术语</span
      ><span>{{ props.strategy.mesh_terms.length }} 个 MeSH</span>
    </div>
    <button
      type="button"
      class="execute"
      :disabled="props.disabled || props.executing"
      @click="emit('execute')"
    >
      {{ props.executing ? "检索中…" : "开始检索 →" }}
    </button>
  </footer>
</template>

<style scoped>
.strategy-sticky {
  position: sticky;
  bottom: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 79px;
  padding: 12px 20px;
  border: 1px solid #dbe5f2;
  border-radius: 12px;
  background: var(--surface);
  box-shadow: 0 -4px 18px rgb(32 73 125 / 9%);
}
.summary {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 14px;
}
.summary > span {
  padding-left: 16px;
  border-left: 1px solid var(--border-subtle);
}
.sticky-version-menu {
  position: relative;
}
.version-selector {
  display: flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  background: var(--surface);
  color: var(--text-primary);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  list-style: none;
}
.version-selector::-webkit-details-marker {
  display: none;
}
.sticky-version-options {
  position: absolute;
  bottom: 42px;
  left: 0;
  display: grid;
  min-width: 150px;
  padding: 8px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow-md);
}
.sticky-version-options span {
  padding: 5px 7px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.save-saved {
  color: var(--color-success);
}
.save-failed,
.save-conflict {
  color: var(--color-danger);
}
.execute {
  min-width: 266px;
  min-height: 53px;
  border: 1px solid #0b66f6;
  border-radius: 8px;
  background: #0b66f6;
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.execute:disabled {
  opacity: 0.6;
  cursor: wait;
}
.version-selector:focus-visible,
.execute:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
@media (max-width: 640px) {
  .strategy-sticky {
    position: static;
    align-items: stretch;
    flex-direction: column;
  }
  .summary {
    gap: 8px;
  }
  .summary > span {
    padding-left: 8px;
  }
  .execute {
    width: 100%;
    min-width: 0;
  }
}
</style>
