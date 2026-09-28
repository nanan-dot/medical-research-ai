<script setup lang="ts">
import type {
  SearchStrategyVersion,
  StrategySaveState,
} from "../../types/searchStrategy";
import BaseIcon from "../../components/ui/BaseIcon.vue";
import SearchCenterNavigation from "./SearchCenterNavigation.vue";

const props = defineProps<{
  saveState: StrategySaveState;
  versions: SearchStrategyVersion[];
  executing?: boolean;
  canExecute?: boolean;
}>();

const emit = defineEmits<{
  createVersion: [];
  execute: [];
}>();

const saveLabel: Record<StrategySaveState, string> = {
  unsaved: "存在未保存修改",
  saving: "正在保存…",
  saved: "已保存",
  failed: "保存失败",
  conflict: "存在并发冲突",
};
</script>

<template>
  <header class="search-center-header">
    <div class="header-title"><SearchCenterNavigation /><h1>检索中心</h1></div>
    <div class="header-actions">
      <span
        class="save-state"
        aria-live="polite"
      >
        <BaseIcon name="sync" />
        {{ saveLabel[props.saveState] }}
      </span>
      <button
        type="button"
        @click="emit('createVersion')"
      >
        策略版本
        {{ props.versions[0] ? `v${props.versions[0].version}` : "草稿" }}
        <BaseIcon name="chevron-down" />
      </button>
      <button
        class="execute-button"
        type="button"
        :disabled="!props.canExecute || props.executing"
        @click="emit('execute')"
      >
        {{ props.executing ? "检索中…" : "开始检索" }}
        <span aria-hidden="true">→</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.search-center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 74px;
  padding: 0 26px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface);
}
.search-center-header h1 {
  margin: 0;
  color: #071b43;
  font-size: 30px;
  line-height: 38px;
  letter-spacing: -0.02em;
}
.header-title { display: flex; align-items: center; gap: 12px; min-width: 0; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.save-state,
button {
  min-height: 44px;
  padding: 0 17px;
  border: 1px solid #d9e4f2;
  border-radius: 9px;
  background: var(--surface);
  color: var(--text-primary);
  font: inherit;
  font-weight: 600;
}
.save-state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #0b1d42;
}
.save-state .icon {
  width: 17px;
  height: 17px;
  color: var(--color-success);
}
button {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}
button .icon {
  width: 16px;
  height: 16px;
}
button:not(:disabled) {
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: wait;
}
button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.execute-button {
  min-width: 140px;
  justify-content: center;
  border-color: #0b66f6;
  background: #0b66f6;
  color: #fff;
}
.execute-button:disabled {
  border-color: var(--border-subtle);
  background: var(--surface-muted);
  color: var(--text-faint);
}
@media (max-width: 768px) {
  .search-center-header {
    padding-inline: 16px;
  }
  .header-actions {
    gap: 8px;
  }
  .save-state,
  .execute-button {
    display: none;
  }
  .header-actions button {
    max-width: 128px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
@media (max-width: 480px) {
  .search-center-header h1 {
    font-size: 24px;
  }
}
</style>
